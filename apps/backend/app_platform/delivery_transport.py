"""Serialized, bounded, durably scheduled HTTP delivery attempts."""

import hashlib
import hmac
import json
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from databases.connectors import UnsafeHost
from environments.crypto import SecretDecryptionError, decrypt_secret

from . import outbound_http
from .models import WebhookDelivery, WorkflowNotificationDelivery

MAX_ATTEMPTS = 6


def webhook_request(delivery):
    webhook = delivery.webhook
    if not webhook.enabled:
        raise UnsafeHost("webhook disabled before delivery")
    secret = decrypt_secret(webhook.signing_secret_ciphertext)
    body = json.dumps(
        {
            **delivery.payload,
            "event_id": str(delivery.id),
            "event_type": delivery.event_type,
            "instance_id": str(delivery.instance_id),
        }
    ).encode()
    signature = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return (
        webhook.url,
        body,
        {
            "Content-Type": "application/json",
            "X-IntraForge-Signature": f"sha256={signature}",
            "X-IntraForge-Event": delivery.event_type,
        },
    )


def workflow_request(delivery):
    attempt = delivery.attempt
    transition = attempt.transition
    body = json.dumps(
        {
            "event_id": str(delivery.id),
            "record_id": str(attempt.record_id),
            "transition": {"key": transition.key, "label": transition.label},
            "from_state": transition.from_state.key if transition.from_state is not None else None,
            "to_state": transition.to_state.key,
            "occurred_at": attempt.completed_at.isoformat() if attempt.completed_at else None,
        }
    ).encode()
    return delivery.url, body, {"Content-Type": "application/json"}


def deliver(delivery_id, *, workflow: bool = False) -> None:
    model = WorkflowNotificationDelivery if workflow else WebhookDelivery
    # Lock only the delivery, not nullable related objects. Concurrent queue
    # duplicates skip an active attempt. A dead process releases the DB lock.
    with transaction.atomic():
        delivery = model.objects.select_for_update(skip_locked=True).filter(pk=delivery_id).first()
        if delivery is None or delivery.delivered_at or delivery.exhausted_at:
            return
        if delivery.next_attempt_at > timezone.now():
            return
        if delivery.attempt_count >= MAX_ATTEMPTS:
            delivery.exhausted_at = timezone.now()
            delivery.save(update_fields=["exhausted_at"])
            return
        delivery.attempt_count += 1
        try:
            url, body, headers = workflow_request(delivery) if workflow else webhook_request(delivery)
            outbound_http.post(url, body, headers)
        except (UnsafeHost, SecretDecryptionError, ValueError):
            delivery.last_error = "Delivery configuration is invalid or destination is blocked."
            delivery.exhausted_at = timezone.now()
        except Exception as exc:  # noqa: BLE001 - durable retry with sanitized error
            delivery.last_error = f"Delivery failed ({type(exc).__name__})."
            delay = 30 * 2 ** (delivery.attempt_count - 1)
            delivery.next_attempt_at = timezone.now() + timedelta(seconds=delay)
            if delivery.attempt_count >= MAX_ATTEMPTS:
                delivery.exhausted_at = timezone.now()
        else:
            delivery.delivered_at = timezone.now()
            delivery.last_error = ""
        # Failure here can repeat remote acceptance. The stable event_id is
        # the receiver's idempotency key; this is deliberately not exactly-once.
        delivery.save(
            update_fields=[
                "attempt_count",
                "last_error",
                "next_attempt_at",
                "exhausted_at",
                "delivered_at",
            ]
        )
