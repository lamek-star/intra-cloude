from celery import shared_task

from .services import run_import


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def run_import_task(self, job_id: str) -> None:
    run_import(job_id)
