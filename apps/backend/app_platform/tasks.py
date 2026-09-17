"""Phase 5 -- workflow notification delivery: a single, at-most-once
outbound HTTP POST per WorkflowNotificationDelivery row, mirroring
imports/tasks.py's own acks_late/idempotent-retry fix exactly (a worker
OOM-kill mid-delivery must not silently lose or duplicate a
notification). No HMAC/webhook-signing secret exists for a `notify_url`
in this pass (a signing secret would need its own new encrypted-secret
field, deliberately not added to keep this pass minimal, per
docs/implementation/APP_PLATFORM_PHASE5.md's "Known limits") -- treat
this delivery as authenticated only by knowledge of the URL itself, and
the receiver's own optional dedup on the `event_id` field.

Phase 10 (docs/implementation/APP_PLATFORM_PHASE10.md) added
`deliver_app_platform_webhook` below, a second, HMAC-signed delivery
mechanism built on `environments.EnvironmentWebhook`'s existing
encrypted signing secret (Phase 22) -- the Known Limit above still
applies only to the original, unsigned `notify_url` field, which is
untouched by this addition."""

import hashlib
import hmac
import json
import urllib.error
import urllib.request
from urllib.parse import urlparse

from celery import shared_task
from celery.exceptions import MaxRetriesExceededError
from django.utils import timezone

from accounts.models import User
from databases.connectors import UnsafeHost, assert_host_is_safe

from .models import WebhookDelivery, WorkflowNotificationDelivery
from .provisioning import execute

REQUEST_TIMEOUT_SECONDS = 5


@shared_task(bind=True, max_retries=1, default_retry_delay=30, acks_late=True, reject_on_worker_lost=True)
def provision_runtime_task(self, instance_id: str, actor_id: str):
    try:
        execute(instance_id, User.objects.get(pk=actor_id))
    except Exception as exc:  # noqa: BLE001 - persisted failure and bounded retry, preserving cause
        raise self.retry(exc=exc) from exc


def _payload(delivery: WorkflowNotificationDelivery) -> bytes:
    attempt = delivery.attempt
    transition = attempt.transition
    body = {
        "event_id": str(delivery.id),
        "record_id": str(attempt.record_id),
        "transition": {"key": transition.key, "label": transition.label},
        "from_state": transition.from_state.key if transition.from_state_id else None,
        "to_state": transition.to_state.key,
        "occurred_at": attempt.completed_at.isoformat() if attempt.completed_at else None,
    }
    return json.dumps(body).encode()


@shared_task(
    bind=True,
    max_retries=5,
    default_retry_delay=30,
    # Same acks_late fix as imports/tasks.py::run_import_task and
    # exports/tasks.py::run_export_task -- a worker OOM-kill mid-delivery
    # must not silently lose the notification. Safe to redeliver: the
    # `delivered_at` check below is the actual at-most-once gate, not this
    # flag alone.
    acks_late=True,
    reject_on_worker_lost=True,
)
def deliver_workflow_notification(self, delivery_id: str) -> None:
    try:
        delivery = WorkflowNotificationDelivery.objects.select_related(
            "attempt__transition__from_state", "attempt__transition__to_state"
        ).get(pk=delivery_id)
    except WorkflowNotificationDelivery.DoesNotExist:
        return  # Nothing to do -- e.g. a stale retry after cleanup.

    if delivery.delivered_at:
        return  # Already sent -- the actual replay-safety gate.

    # Re-checked immediately before every delivery attempt, not just at
    # definition time -- DNS can rebind between the two (the same
    # doctrine assert_host_is_safe's own docstring states).
    parsed = urlparse(delivery.url)
    try:
        assert_host_is_safe(parsed.hostname)
    except UnsafeHost as exc:
        # Not retryable -- the target will never become safe. Recorded,
        # never silently dropped.
        delivery.last_error = str(exc)[:200]
        delivery.save(update_fields=["last_error"])
        return

    delivery.attempt_count += 1
    delivery.save(update_fields=["attempt_count"])

    request = urllib.request.Request(
        delivery.url,
        data=_payload(delivery),
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
            if response.status >= 400:
                raise urllib.error.HTTPError(
                    delivery.url, response.status, "delivery rejected", response.headers, None
                )
    except Exception as exc:  # noqa: BLE001 - any failure here should trigger a retry, not just a known subset
        try:
            raise self.retry(exc=exc)
        except MaxRetriesExceededError:
            delivery.last_error = f"{type(exc).__name__}: {exc}"[:200]
            delivery.save(update_fields=["last_error"])
            return

    delivery.delivered_at = timezone.now()
    delivery.save(update_fields=["delivered_at"])


def _signature_header(secret: str, body: bytes) -> str:
    digest = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


@shared_task(
    bind=True,
    max_retries=5,
    default_retry_delay=30,
    # Same acks_late/at-most-once discipline as deliver_workflow_notification
    # above (and imports/exports' own tasks) -- a worker OOM-kill mid-delivery
    # must not silently lose or duplicate a webhook.
    acks_late=True,
    reject_on_worker_lost=True,
)
def deliver_app_platform_webhook(self, delivery_id: str) -> None:
    from environments.crypto import SecretDecryptionError, decrypt_secret

    try:
        delivery = WebhookDelivery.objects.select_related("webhook").get(pk=delivery_id)
    except WebhookDelivery.DoesNotExist:
        return  # Nothing to do -- e.g. a stale retry after cleanup.

    if delivery.delivered_at:
        return  # Already sent -- the actual replay-safety gate.

    webhook = delivery.webhook
    if not webhook.enabled:
        # Disabled between dispatch and delivery -- never send to a
        # subscription the owner has since turned off. Not an error.
        delivery.last_error = "webhook disabled before delivery"
        delivery.save(update_fields=["last_error"])
        return

    # Re-checked immediately before every delivery attempt, not just at
    # dispatch time -- DNS can rebind between the two (the same doctrine
    # deliver_workflow_notification and assert_host_is_safe's own
    # docstring both already apply).
    parsed = urlparse(webhook.url)
    try:
        assert_host_is_safe(parsed.hostname)
    except UnsafeHost as exc:
        delivery.last_error = str(exc)[:200]
        delivery.save(update_fields=["last_error"])
        return

    try:
        secret = decrypt_secret(webhook.signing_secret_ciphertext)
    except SecretDecryptionError as exc:
        # Not retryable -- a corrupt/undecryptable secret will never
        # become valid on its own.
        delivery.last_error = str(exc)[:200]
        delivery.save(update_fields=["last_error"])
        return

    body = json.dumps({
        "event_id": str(delivery.id),
        "event_type": delivery.event_type,
        "instance_id": str(delivery.instance_id),
        **delivery.payload,
    }).encode()

    delivery.attempt_count += 1
    delivery.save(update_fields=["attempt_count"])

    request = urllib.request.Request(
        webhook.url,
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "X-IntraForge-Signature": _signature_header(secret, body),
            "X-IntraForge-Event": delivery.event_type,
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
            if response.status >= 400:
                raise urllib.error.HTTPError(
                    webhook.url, response.status, "delivery rejected", response.headers, None
                )
    except Exception as exc:  # noqa: BLE001 - any failure here should trigger a retry, not just a known subset
        try:
            raise self.retry(exc=exc)
        except MaxRetriesExceededError:
            delivery.last_error = f"{type(exc).__name__}: {exc}"[:200]
            delivery.save(update_fields=["last_error"])
            return

    delivery.delivered_at = timezone.now()
    delivery.save(update_fields=["delivered_at"])
