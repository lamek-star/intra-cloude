from celery import shared_task
from celery.exceptions import MaxRetriesExceededError

from .models import ExportJob
from .services import run_export, run_restore


@shared_task(
    bind=True,
    max_retries=2,
    default_retry_delay=30,
    # Same worker-crash gap imports/tasks.py::run_import_task documents and
    # fixes (Celery's default acks_late=False loses the task entirely if
    # the worker dies mid-run, with no exception for the except block below
    # to ever catch). Safe here because run_export builds the .icp from the
    # *existing* Organization's current data and writes it to a
    # deterministic object_key (f"{prefix}/{org_id}/{job_id}.icp"), so a
    # redelivered re-run after a crash just rebuilds and overwrites the
    # same key — no new rows are created, nothing is duplicated.
    acks_late=True,
    reject_on_worker_lost=True,
)
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


@shared_task(
    bind=True, max_retries=1, default_retry_delay=30,
    acks_late=True, reject_on_worker_lost=True,
)
def run_restore_task(self, job_id: str, wrapped_passphrase: str | None) -> None:
    # Database publication and repeatable external preparation make duplicate
    # execution safe. Failure evidence/input is retained by run_restore.
    try:
        run_restore(job_id, wrapped_passphrase)
    except Exception as exc:  # noqa: BLE001 - retain original exception when retry budget is exhausted
        raise self.retry(exc=exc) from exc
