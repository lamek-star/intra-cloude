import uuid

from django.core.management.base import BaseCommand, CommandError

from audit import services as audit
from audit.models import AuditEvent
from system import backups
from system.models import BackupRecord


class Command(BaseCommand):
    help = (
        "Restores one backup record into the real, live target it was backed up from -- "
        "destructive, replaces the target's current content. Requires --yes. See "
        "docs/operations/BACKUP_RESTORE.md Section 6."
    )

    def add_arguments(self, parser):
        parser.add_argument("record_id", type=str, help="BackupRecord id (UUID)")
        parser.add_argument(
            "--yes", action="store_true",
            help="Required acknowledgement that this replaces the target's live data.",
        )

    def handle(self, *args, **options):
        if not options["yes"]:
            raise CommandError(
                "Refusing to restore without --yes -- this replaces the target's current live "
                "data and cannot be undone except by restoring an earlier backup."
            )

        try:
            record_id = uuid.UUID(options["record_id"])
        except ValueError as exc:
            raise CommandError(f"'{options['record_id']}' is not a valid backup record id.") from exc

        try:
            record = BackupRecord.objects.get(id=record_id)
        except BackupRecord.DoesNotExist as exc:
            raise CommandError(f"No backup record found with id {record_id}.") from exc

        restored = backups.restore_backup(record)
        success = not restored.restore_error

        audit.record(
            actor=None,
            organization_id=None,
            action="system.backup.restore",
            resource_type="backup_record",
            resource_id=restored.id,
            result=AuditEvent.Result.SUCCESS if success else AuditEvent.Result.ERROR,
            context={"backup_type": restored.backup_type, "file_path": restored.file_path},
        )

        if success:
            self.stdout.write(self.style.SUCCESS(f"Backup {restored.id} restored successfully."))
        else:
            raise CommandError(f"Backup {restored.id} restore failed: {restored.restore_error}")
