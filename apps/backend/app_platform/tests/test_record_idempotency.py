from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest.mock import patch

from django.db import close_old_connections
from rest_framework.test import APIClient

from app_platform.tests.test_webhooks import WebhookTestBase
from audit.models import AuditEvent
from permissions.models import RoleAssignment


class RecordIdempotencyTests(WebhookTestBase):
    def create(self, key, value="Once"):
        return self.client.post(
            f"/api/v1/app-models/{self.item.pk}/records/",
            {str(self.name_field.pk): value},
            format="json",
            HTTP_IDEMPOTENCY_KEY=key,
        )

    def test_replay_after_publication_failure_returns_same_record_and_one_audit(self):
        with patch("app_platform.operation_journal.publish", side_effect=OSError("control unavailable")):
            first = self.create("create-1")
        second = self.create("create-1")
        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 201)
        self.assertEqual(first.json(), second.json())
        from app_platform.operation_journal import publish

        publish(self.receipt.pk)
        self.assertEqual(
            AuditEvent.objects.filter(resource_id=self.item.pk, action="app_instance.record.create").count(),
            1,
        )

    def test_conflicting_payload_is_rejected_and_revocation_still_applies(self):
        first = self.create("create-2")
        self.assertEqual(first.status_code, 201)
        self.assertEqual(self.create("create-2", "Different").status_code, 409)
        RoleAssignment.objects.filter(user=self.actor).delete()
        self.assertEqual(self.create("create-2").status_code, 403)

    def test_same_key_is_scoped_to_model_and_invalid_keys_are_rejected(self):
        self.assertEqual(self.create(" ").status_code, 400)
        self.assertEqual(self.create("x" * 129).status_code, 400)
        first = self.create("shared")
        other_model = self.instance.models.exclude(pk=self.item.pk).first()
        self.assertIsNotNone(other_model)
        second = self.client.post(
            f"/api/v1/app-models/{other_model.pk}/records/",
            {},
            format="json",
            HTTP_IDEMPOTENCY_KEY="shared",
        )
        self.assertEqual(second.status_code, 201, second.data)
        self.assertNotEqual(first.data["id"], second.data["id"])

    def test_concurrent_creates_share_one_tenant_effect(self):
        barrier = Barrier(2)

        def run():
            close_old_connections()
            try:
                client = APIClient()
                client.force_authenticate(self.actor)
                barrier.wait(timeout=10)
                response = client.post(
                    f"/api/v1/app-models/{self.item.pk}/records/",
                    {str(self.name_field.pk): "Concurrent"},
                    format="json",
                    HTTP_IDEMPOTENCY_KEY="same-concurrent-operation",
                )
                return response.status_code, response.json()
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as pool:
            responses = [future.result(timeout=30) for future in [pool.submit(run), pool.submit(run)]]
        self.assertEqual([status for status, _ in responses], [201, 201])
        self.assertEqual(responses[0][1], responses[1][1])
        listing = self.client.get(f"/api/v1/app-models/{self.item.pk}/records/")
        self.assertEqual(listing.data["count"], 1)
