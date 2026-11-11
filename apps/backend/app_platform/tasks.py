"""Provisioning and at-least-once HTTP delivery with durable retry scheduling.

HTTP acceptance and a local success marker cannot commit atomically.
Receivers must deduplicate event_id, including after worker-crash redelivery.
"""

from celery import shared_task
from django.utils import timezone

from accounts.models import User

from .models import RuntimeProvision, WebhookDelivery, WorkflowNotificationDelivery
from .provisioning import execute


@shared_task(bind=True, max_retries=1, default_retry_delay=30, acks_late=True, reject_on_worker_lost=True)
def provision_runtime_task(self, instance_id: str, actor_id: str):
    try:
        execute(instance_id, User.objects.get(pk=actor_id))
    except Exception as exc:  # noqa: BLE001 - persisted failure and bounded retry, preserving cause
        raise self.retry(exc=exc) from exc


@shared_task(acks_late=True, reject_on_worker_lost=True)
def deliver_workflow_notification(delivery_id: str) -> None:
    from .delivery_transport import deliver

    deliver(delivery_id, workflow=True)


@shared_task(acks_late=True, reject_on_worker_lost=True)
def deliver_app_platform_webhook(delivery_id: str) -> None:
    from .delivery_transport import deliver

    deliver(delivery_id)


@shared_task
def recover_operation_publication() -> None:
    """Recover pending events and due deliveries after broker/process outages."""
    from .operation_journal import publish_safely
    from .webhooks import enqueue_safely
    from .workflows import _enqueue_delivery

    for identity in (
        RuntimeProvision.objects.filter(completed_at__isnull=False, database__isnull=False)
        .values_list("pk", flat=True)
        .iterator()
    ):
        publish_safely(identity)
    for model, enqueue in (
        (WebhookDelivery, enqueue_safely),
        (WorkflowNotificationDelivery, _enqueue_delivery),
    ):
        for identity in model.objects.filter(
            delivered_at__isnull=True, exhausted_at__isnull=True, next_attempt_at__lte=timezone.now()
        ).values_list("pk", flat=True)[:1000]:
            enqueue(identity)
