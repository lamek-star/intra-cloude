import hashlib
import os

from django.core.management.base import BaseCommand, CommandError

from audit import services as audit
from audit.models import AuditEvent
from system import backups
from system.models import BackupRecord


class Command(BaseCommand):
    help = (
        "Disaster recovery: restores one backup FILE into the real, live target it was backed up "
        "from, with no BackupRecord needed -- for a fresh install after a total loss, when the "
        "control database that held the records is gone. The file must be inside BACKUP_DIR. "
        "Destructive; requires --yes. Restore control_db first, then tenant_db, then "
        "object_storage, with the application stack stopped. See docs/operations/BACKUP_RESTORE.md."
    )

    def add_arguments(self, parser):
        parser.add_argument("file_path", help="Backup file inside BACKUP_DIR (.dump/.tar, or encrypted .icb)")
        parser.add_argument(
            "--type",
            required=True,
            dest="backup_type",
            choices=[
                BackupRecord.BackupType.CONTROL_DB,
                BackupRecord.BackupType.TENANT_DB,
                BackupRecord.BackupType.OBJECT_STORAGE,
            ],
            help="What the file contains (the file name starts with this).",
        )
        parser.add_argument(
            "--replace",
            action="store_true",
            help=(
                "Databases only: make the database exactly the backup, in one transaction (everything "
                "created after the backup is removed). For restoring a whole installation to a point in "
                "time, including a backup made by an earlier version."
            ),
        )
        parser.add_argument(
            "--yes",
            action="store_true",
            help="Required acknowledgement that this replaces the target's live data.",
        )

    def handle(self, *args, **options):
        if not options["yes"]:
            raise CommandError(
                "Refusing to restore without --yes -- this replaces the target's current live "
                "data and cannot be undone except by restoring an earlier backup."
            )
        backup_type, file_path = options["backup_type"], options["file_path"]
        error = backups.restore_backup_from_file(backup_type, file_path, replace=options["replace"])

        # Best-effort evidence: after a control-database restore the audit table is the restored
        # one, and a failure to write here must not turn a completed restore into a reported failure.
        try:
            audit.record(
                actor=None,
                organization_id=None,
                action="system.backup.restore_file",
                resource_type="backup_file",
                result=AuditEvent.Result.ERROR if error else AuditEvent.Result.SUCCESS,
                context={
                    "backup_type": backup_type,
                    "file": os.path.basename(file_path),
                    "mode": "replace" if options["replace"] else "additive",
                },
            )
        except Exception as exc:  # noqa: BLE001
            self.stderr.write(f"warning: could not write the audit event ({type(exc).__name__})")

        if error:
            raise CommandError(f"Restore of {os.path.basename(file_path)} failed: {error}")
        digest = ""
        try:
            with open(os.path.realpath(file_path), "rb") as handle:
                digest = hashlib.sha256(handle.read()).hexdigest()[:16]
        except OSError:
            pass
        self.stdout.write(
            self.style.SUCCESS(
                f"{backup_type} restored from {os.path.basename(file_path)}"
                + (f" (sha256 {digest}...)" if digest else "")
            )
        )
