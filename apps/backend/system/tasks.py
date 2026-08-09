from celery import shared_task

from . import backups
from .models import BackupRecord


@shared_task
def run_backup_task(backup_type: str) -> str:
    record = backups.run_backup(backup_type)
    return str(record.id)


@shared_task
def verify_latest_backup_task(backup_type: str) -> str | None:
    """The automated restoration test job (docs/operations/BACKUP_RESTORE.md
    Section 7) — restores the most recent successful backup of the given
    type into an isolated database and records whether it validated."""
    latest = (
        BackupRecord.objects.filter(backup_type=backup_type, status=BackupRecord.Status.SUCCESS)
        .order_by("-started_at")
        .first()
    )
    if latest is None:
        return None
    record = backups.verify_backup_restorable(latest)
    return str(record.id)
