from celery import shared_task
from celery.exceptions import MaxRetriesExceededError

from .models import ExportJob, RestoreJob
from .services import run_export, run_restore


@shared_task(bind=True, max_retries=2, default_retry_delay=30)
def run_export_task(self, job_id: str, wrapped_passphrase: str | None) -> None:
    try:
        run_export(job_id, wrapped_passphrase)
    except Exception as exc:  # noqa: BLE001 - retry on any failure; final failure already recorded by run_export
        try:
            raise self.retry(exc=exc)
        except MaxRetriesExceededError:
            ExportJob.objects.filter(id=job_id).update(
                status=ExportJob.Status.FAILED, error_message=str(exc)[:2000]
            )
            raise


@shared_task(bind=True, max_retries=1, default_retry_delay=30)
def run_restore_task(self, job_id: str, wrapped_passphrase: str | None) -> None:
    # Retries are far less safe here than for run_export_task: a
    # restore that failed partway (e.g. the process was killed) could
    # in principle be re-attempted since the whole thing is transactional
    # (restorer.restore_package), but re-running from scratch on a job
    # already marked FAILED by a previous attempt is not something an
    # operator should get silently — one retry only, as a narrow
    # allowance for a transient failure (e.g. a dropped DB connection
    # mid-restore), not a general safety net.
    try:
        run_restore(job_id, wrapped_passphrase)
    except Exception as exc:  # noqa: BLE001 - retry on any failure; final failure already recorded by run_restore
        try:
            raise self.retry(exc=exc)
        except MaxRetriesExceededError:
            RestoreJob.objects.filter(id=job_id).update(
                status=RestoreJob.Status.FAILED, error_message=str(exc)[:2000]
            )
            raise
