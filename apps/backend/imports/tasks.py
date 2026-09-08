from celery import shared_task
from celery.exceptions import MaxRetriesExceededError

from audit.models import AuditEvent

from .models import ImportJob
from .services import record_import_outcome, run_import


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=30,
    # Celery's default (acks_late=False) acknowledges a task the moment a
    # worker picks it up, before it runs -- so a worker that dies mid-task
    # (OOM-kill, container restart, a deploy) simply loses it: no
    # exception is ever raised in this process for the except block below
    # to catch, self.retry() never fires, and the job is left at RUNNING
    # forever with no error and no dataset.import.finish audit event.
    # Live-verified: started a real 60k-row import against the actual
    # worker container, SIGKILLed it mid-run (imported_rows=6000),
    # restarted it, and the job sat at RUNNING/6000 indefinitely with no
    # further progress. acks_late + reject_on_worker_lost makes the
    # broker redeliver the task to a worker that comes back up, which
    # re-enters run_import(job_id) and resumes from last_processed_row --
    # already proven safe (no dropped/duplicated rows) by
    # test_connection_failure_is_reraised_and_progress_checkpointed_for_retry.
    # Deliberately not made a Celery-wide default here: run_restore_task
    # (exports/tasks.py) has its own, narrower, explicitly-documented
    # retry-safety margin that a blanket change would silently override.
    acks_late=True,
    reject_on_worker_lost=True,
)
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
            job = ImportJob.objects.select_related("table", "created_by").get(id=job_id)
            record_import_outcome(job, AuditEvent.Result.ERROR)
            raise
