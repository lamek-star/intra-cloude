from celery import shared_task
from celery.exceptions import MaxRetriesExceededError

from .models import ExportJob, RestoreJob
from .services import run_export, run_restore


@shared_task(
    bind=True,
    max_retries=2,
    default_retry_delay=30,
    # Same worker-crash gap imports/tasks.py::run_import_task documents and
    # fixes (Celery's default acks_late=False loses the task entirely if
    # the worker dies mid-run, with no exception for the except block below
    # to ever catch). Safe to apply the identical fix here, unlike
    # run_restore_task below: run_export builds the .icp from the
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


@shared_task(bind=True, max_retries=1, default_retry_delay=30)
def run_restore_task(self, job_id: str, wrapped_passphrase: str | None) -> None:
    # Deliberately NOT given the same acks_late=True fix as
    # run_export_task/run_import_task, after actually auditing it
    # (2026-09-08) rather than copying the pattern — restorer.restore_package
    # is atomic (transaction.atomic on both "default" and "tenant"), which
    # covers the common case: a worker killed *during* that block loses an
    # uncommitted transaction that Postgres rolls back on its own, so a
    # redelivered retry-from-scratch is safe there. The unsafe window is
    # narrower but real: run_restore's `finally` deletes the staged .icp
    # from object storage unconditionally, and the job isn't saved as
    # COMPLETED until *after* that `finally` runs. A worker killed in the
    # gap between "restore_package committed" and "job.status = COMPLETED
    # saved" would, on redelivery, either find the staged file already
    # deleted (raises cleanly, wrongly marks an actually-successful restore
    # as FAILED) or, if delete ordering were flipped to close that gap,
    # instead find it still present and silently create a *second* brand
    # new Organization for the same package (restore_package always
    # creates a new Organization — it has no idempotency check to skip a
    # re-run). Fixing this for real needs a durable idempotency marker
    # (e.g. persisting organization_id inside the same atomic block that
    # creates it, so a resumed run can detect "already restored" before
    # calling restore_package again) plus its own live SIGKILL experiment,
    # not a copy-paste of the import/export fix — tracked as an open item
    # in RELEASE_READINESS.md rather than shipped as a guess. One retry
    # only remains, as a narrow allowance for a transient in-process
    # failure (e.g. a dropped DB connection mid-restore raising an
    # exception this process can actually catch), not a crash-recovery
    # mechanism.
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
