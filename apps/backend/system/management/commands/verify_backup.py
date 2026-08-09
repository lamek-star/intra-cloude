from django.core.management.base import BaseCommand, CommandError

from system import backups
from system.models import BackupRecord


class Command(BaseCommand):
    help = (
        "Restores the most recent successful backup of the given type into an "
        "isolated database and validates it (the automated restoration test "
        "job — docs/operations/BACKUP_RESTORE.md Section 7)."
    )

    def add_arguments(self, parser):
        parser.add_argument("backup_type", choices=[c.value for c in BackupRecord.BackupType])

    def handle(self, *args, **options):
        latest = (
            BackupRecord.objects.filter(
                backup_type=options["backup_type"], status=BackupRecord.Status.SUCCESS
            )
            .order_by("-started_at")
            .first()
        )
        if latest is None:
            raise CommandError(f"No successful {options['backup_type']} backup found to verify.")

        record = backups.verify_backup_restorable(latest)
        if record.verified_restorable:
            self.stdout.write(
                self.style.SUCCESS(f"Backup {record.id} restored and validated successfully.")
            )
        else:
            raise CommandError(
                f"Backup {record.id} failed restoration verification: {record.verification_error}"
            )
