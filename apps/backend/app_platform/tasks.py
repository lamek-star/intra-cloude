from celery import shared_task

from accounts.models import User

from .provisioning import execute


@shared_task(bind=True, max_retries=1, default_retry_delay=30, acks_late=True, reject_on_worker_lost=True)
def provision_runtime_task(self, instance_id: str, actor_id: str):
    try:
        execute(instance_id, User.objects.get(pk=actor_id))
    except Exception as exc:  # noqa: BLE001 - persisted failure and bounded retry, preserving cause
        raise self.retry(exc=exc) from exc
