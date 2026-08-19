from celery import shared_task
from celery.exceptions import MaxRetriesExceededError

from .models import ImportJob
from .services import run_import


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def run_import_task(self, job_id: str) -> None:
    try:
        run_import(job_id)
    except Exception as exc:  # noqa: BLE001 - any failure here should trigger a retry, not just a known subset
        try:
            # self.retry() raises Retry itself when a retry is scheduled —
            # this only reaches MaxRetriesExceededError once retries are
            # truly exhausted, which is the one place the job should
            # actually be marked FAILED (run_import's own checkpoint has
            # already preserved progress for whichever attempt this was).
            raise self.retry(exc=exc)
        except MaxRetriesExceededError:
            ImportJob.objects.filter(id=job_id).update(
                status=ImportJob.Status.FAILED, error_message=str(exc)[:2000]
            )
            raise
