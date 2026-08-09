from django.core.management.base import BaseCommand, CommandError

from system import backups
from system.models import BackupRecord


class Command(BaseCommand):
    help = (
        "Runs a pg_dump backup of the control-plane or tenant database "
        "(manual trigger; normally scheduled via Celery Beat, see "
        "config/settings/base.py CELERY_BEAT_SCHEDULE)."
    )

    def add_arguments(self, parser):
        parser.add_argument("backup_type", choices=[c.value for c in BackupRecord.BackupType])

    def handle(self, *args, **options):
        record = backups.run_backup(options["backup_type"])
        if record.status == BackupRecord.Status.SUCCESS:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Backup {record.id} succeeded: {record.file_path} ({record.size_bytes} bytes)"
                )
            )
        else:
            raise CommandError(f"Backup {record.id} failed: {record.error_message}")
