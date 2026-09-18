"""Phase 10 -- reliable webhooks (docs/implementation/APP_PLATFORM_ROADMAP.md,
docs/implementation/APP_PLATFORM_PHASE10.md). Closes the one gap `docs/
EXTERNAL_APP_API_CONTRACT.md` previously listed outright as **NOT YET
IMPLEMENTED**: "Webhooks or any push/event-notification mechanism out of
App Platform toward an external application."

Reuses `environments.EnvironmentWebhook` (Phase 22) as the *entire*
subscription/signing-secret store -- no new configuration concept, no
new encrypted-secret model. An App Platform event only ever reaches a
webhook when the *emitting instance's own runtime database* is bound to
that webhook's Environment: the same binding
`environments.services.check_environment_scope` already uses to restrict
an Environment-scoped credential's *inbound* access, read in the
opposite direction here for *outbound* dispatch. An instance with no
Environment binding at all therefore has no possible subscribers, by
construction -- never a silent broadcast to every webhook an
organization happens to have configured somewhere unrelated.

Event types (the vocabulary a webhook's own `event_types` filters
against; an empty list subscribes to all of them):

- `app_instance.record.create` / `.record.update` / `.record.delete`
- `app_instance.workflow.transition`

Payloads are deliberately thin (ids and an event type only, never a
record's actual field values) -- the same "fetch details via the real
API, don't trust a push payload as the source of truth" posture most
mature webhook systems use, and it sidesteps a real risk this codebase
is otherwise careful about: a slow, broken, or malicious receiver
logging or mishandling a payload that happens to carry business data."""

import logging
from functools import partial

from django.db import transaction

from .models import RuntimeProvision, WebhookDelivery

EVENT_RECORD_CREATE = "app_instance.record.create"
EVENT_RECORD_UPDATE = "app_instance.record.update"
EVENT_RECORD_DELETE = "app_instance.record.delete"
EVENT_WORKFLOW_TRANSITION = "app_instance.workflow.transition"
logger = logging.getLogger(__name__)


def subscribers(receipt, event_type):
    from environments.models import EnvironmentWebhook

    if receipt is None or receipt.database is None or receipt.database.environment_id is None:
        return []
    return [
        webhook
        for webhook in EnvironmentWebhook.objects.filter(
            environment_id=receipt.database.environment_id, enabled=True
        )
        if not webhook.event_types or event_type in webhook.event_types
    ]


def publish_delivery(receipt, event_type, payload, webhook_id, *, identity=None):
    from environments.models import EnvironmentWebhook

    # A deleted, disabled, or rebound subscription must not receive an old event.
    webhook = EnvironmentWebhook.objects.filter(
        pk=webhook_id, environment_id=receipt.database.environment_id, enabled=True
    ).first()
    if webhook is None:
        return
    defaults = {
        "webhook": webhook,
        "instance": receipt.instance,
        "event_type": event_type,
        "payload": payload,
    }
    if identity is None:
        delivery = WebhookDelivery.objects.create(**defaults)
    else:
        delivery, _ = WebhookDelivery.objects.get_or_create(pk=identity, defaults=defaults)
    transaction.on_commit(partial(enqueue_safely, delivery.id))


def enqueue_safely(delivery_id):
    try:
        _enqueue(delivery_id)
    except Exception:  # noqa: BLE001 - durable pending delivery is retried by the recovery task
        logger.exception("Webhook queue publication deferred for delivery %s", delivery_id)


def dispatch_event(receipt: RuntimeProvision | None, instance, event_type: str, payload: dict) -> None:
    """Called by records.py/workflows.py immediately after the triggering
    change's own transaction has committed (every call site wraps this in
    `transaction.on_commit`, the exact precedent workflows.py's own
    `_enqueue_delivery` already established for `notify_url` delivery) --
    queuing a delivery for a change that then rolls back would deliver an
    event that never really happened.

    `receipt` is `None`/unprovisioned/unbound for an instance with no
    completed runtime, or one whose database was never bound to any
    Environment -- both mean "no possible subscribers," not an error, so
    this is a silent no-op rather than a raise."""
    for webhook in subscribers(receipt, event_type):
        publish_delivery(receipt, event_type, payload, webhook.pk)


def _enqueue(delivery_id):
    # Deferred import -- see workflows.py's own _enqueue_delivery for why:
    # keeps this module free of a Celery import for any test/context that
    # never dispatches a subscribed event.
    from .tasks import deliver_app_platform_webhook

    deliver_app_platform_webhook.delay(str(delivery_id))
