"""Real two-database failures at record commit and control publication."""

from unittest.mock import patch

from django.db import connections, transaction
from psycopg import sql

from app_platform import operation_journal, records
from app_platform.models import WebhookDelivery
from app_platform.tasks import recover_operation_publication
from app_platform.tests.test_webhooks import WebhookTestBase
from audit.models import AuditEvent


class OperationJournalTests(WebhookTestBase):
    def test_control_outage_after_tenant_commit_recovers_one_audit_and_delivery(self):
        self._create_webhook("http://127.0.0.1:1/hook")
        with patch("app_platform.operation_journal.publish", side_effect=OSError("control unavailable")):
            row = records.create_record(self.actor, self.item, {str(self.name_field.id): "Committed"})
        self.assertEqual(
            records.get_record(self.actor, self.item, row["id"])[str(self.name_field.id)], "Committed"
        )
        events = AuditEvent.objects.filter(action="app_instance.record.create", resource_id=self.item.id)
        self.assertEqual(events.count(), 0)
        with patch("app_platform.webhooks._enqueue"):
            recover_operation_publication.run()
            recover_operation_publication.run()
        self.assertEqual(events.count(), 1)
        self.assertEqual(WebhookDelivery.objects.count(), 1)

    def test_replay_after_control_commit_before_tenant_marker_deduplicates(self):
        self._create_webhook("http://127.0.0.1:1/hook")
        with patch("app_platform.webhooks._enqueue"):
            records.create_record(self.actor, self.item, {str(self.name_field.id): "Once"})
            # Recreate exactly the durable state left by a crash between the
            # independent control commit and tenant acknowledgement commit.
            with connections["tenant"].cursor() as cursor:
                cursor.execute(
                    sql.SQL("UPDATE {} SET published_at = NULL").format(
                        sql.Identifier(self.receipt.database.schema_name, operation_journal.TABLE)
                    )
                )
            operation_journal.publish(self.receipt.pk)
        self.assertEqual(
            AuditEvent.objects.filter(action="app_instance.record.create", resource_id=self.item.id).count(),
            1,
        )
        self.assertEqual(WebhookDelivery.objects.count(), 1)

    def test_rollback_cannot_publish_an_event_for_a_record_that_never_committed(self):
        self._create_webhook("http://127.0.0.1:1/hook")
        with self.assertRaisesRegex(RuntimeError, "rollback"), transaction.atomic(using="tenant"):
            row = records.create_record(self.actor, self.item, {str(self.name_field.id): "Never committed"})
            raise RuntimeError("rollback")
        self.assertFalse(records.record_exists(records._table(self.receipt, self.item), row["id"]))
        self.assertEqual(WebhookDelivery.objects.count(), 0)
        self.assertFalse(
            AuditEvent.objects.filter(action="app_instance.record.create", resource_id=self.item.id).exists()
        )

    def test_broker_recovery_republishes_existing_delivery_identity(self):
        self._create_webhook("http://127.0.0.1:1/hook")
        with patch("app_platform.webhooks._enqueue", side_effect=OSError("broker unavailable")):
            records.create_record(self.actor, self.item, {str(self.name_field.id): "Queued later"})
        identity = WebhookDelivery.objects.get().id
        with patch("app_platform.webhooks._enqueue") as enqueue:
            recover_operation_publication.run()
        enqueue.assert_called_once_with(identity)
