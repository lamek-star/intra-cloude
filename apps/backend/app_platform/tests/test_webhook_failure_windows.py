"""Deterministic failures at HTTP/result and tenant/event boundaries."""

import json
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Event
from unittest.mock import patch

from django.db import close_old_connections
from django.utils import timezone

from app_platform import records
from app_platform.models import WebhookDelivery
from app_platform.tasks import deliver_app_platform_webhook
from app_platform.tests.test_webhooks import WebhookTestBase


class WebhookFailureWindowTests(WebhookTestBase):
    def test_due_time_and_exhaustion_survive_new_task_invocations(self):
        self._create_webhook("http://127.0.0.1:1/hook")
        with patch("app_platform.webhooks._enqueue"):
            self._create_item()
        delivery = WebhookDelivery.objects.get()
        with patch("app_platform.outbound_http.post", side_effect=OSError("unavailable")) as post:
            for attempt in range(1, 7):
                WebhookDelivery.objects.filter(pk=delivery.pk).update(next_attempt_at=timezone.now())
                deliver_app_platform_webhook.run(str(delivery.pk))
                delivery.refresh_from_db()
                self.assertEqual(delivery.attempt_count, attempt)
                self.assertTrue(delivery.last_error)
                # Duplicate queue messages cannot burn through the retry budget.
                deliver_app_platform_webhook.run(str(delivery.pk))
                self.assertEqual(post.call_count, attempt)
            self.assertIsNotNone(delivery.exhausted_at)
            WebhookDelivery.objects.filter(pk=delivery.pk).update(
                next_attempt_at=timezone.now() - timedelta(days=1)
            )
            deliver_app_platform_webhook.run(str(delivery.pk))
            self.assertEqual(post.call_count, 6)

    def test_concurrent_queue_duplicates_cannot_send_simultaneously(self):
        self._create_webhook("http://127.0.0.1:1/hook")
        with patch("app_platform.webhooks._enqueue"):
            self._create_item()
        delivery = WebhookDelivery.objects.get()
        entered, release = Event(), Event()

        def blocked_post(*args, **kwargs):
            entered.set()
            self.assertTrue(release.wait(10))

        def run():
            close_old_connections()
            try:
                deliver_app_platform_webhook.run(str(delivery.pk))
            finally:
                close_old_connections()

        with patch("app_platform.outbound_http.post", side_effect=blocked_post) as post:
            with ThreadPoolExecutor(max_workers=2) as pool:
                first = pool.submit(run)
                try:
                    self.assertTrue(entered.wait(10))
                    pool.submit(run).result(timeout=10)
                finally:
                    release.set()
                first.result(timeout=10)
            self.assertEqual(post.call_count, 1)
        delivery.refresh_from_db()
        self.assertIsNotNone(delivery.delivered_at)

    def test_receiver_can_see_duplicate_event_after_success_marker_failure(self):
        url, received = self._start_receiver()
        self._create_webhook(url)
        with patch("app_platform.webhooks._enqueue"):
            self._create_item()
        delivery = WebhookDelivery.objects.get()
        original = WebhookDelivery.save

        def fail_success_marker(row, *args, **kwargs):
            if row.delivered_at:
                raise OSError("injected crash after remote acceptance")
            return original(row, *args, **kwargs)

        with patch.object(WebhookDelivery, "save", fail_success_marker), self.assertRaises(OSError):
            deliver_app_platform_webhook.run(str(delivery.id))
        deliver_app_platform_webhook.run(str(delivery.id))
        self.assertEqual(len(received), 2)
        self.assertEqual(json.loads(received[0]["body"])["event_id"], str(delivery.id))
        self.assertEqual(received[0]["body"], received[1]["body"])
        # This is deliberately a proof of at-least-once ambiguity, not a
        # demand for impossible exactly-once HTTP effects at a remote server.

    def test_broker_failure_does_not_turn_a_committed_record_into_a_failed_request(self):
        self._create_webhook("http://127.0.0.1:1/hook")
        with patch("app_platform.webhooks._enqueue", side_effect=OSError("broker unavailable")):
            row = records.create_record(self.actor, self.item, {str(self.name_field.id): "Durable"})
        self.assertEqual(
            records.get_record(self.actor, self.item, row["id"])[str(self.name_field.id)], "Durable"
        )
        self.assertEqual(WebhookDelivery.objects.count(), 1)
