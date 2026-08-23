import json

from django.core.management.base import BaseCommand

from system.models import BackupRecord


class Command(BaseCommand):
    help = (
        "Lists BackupRecord rows, most recent first. --json emits the "
        "shape the Windows Control Center (Phase 18) consumes via "
        "`docker compose exec -T backend python manage.py list_backups --json`, "
        "the same in-distro shell-out pattern Uninstall-IntraCloudDistro.ps1's "
        "pre-removal backup step already uses -- not a new trust boundary."
    )

    def add_arguments(self, parser):
        parser.add_argument("--json", action="store_true", dest="as_json")
        parser.add_argument("--limit", type=int, default=50)
        parser.add_argument(
            "--backup-type",
            dest="backup_type",
            choices=[c.value for c in BackupRecord.BackupType],
            default=None,
        )

    def handle(self, *args, **options):
        queryset = BackupRecord.objects.all()
        if options["backup_type"]:
            queryset = queryset.filter(backup_type=options["backup_type"])
        records = list(queryset[: options["limit"]])

        if options["as_json"]:
            payload = [
                {
                    "id": str(record.id),
                    "backup_type": record.backup_type,
                    "status": record.status,
                    "file_path": record.file_path,
                    "size_bytes": record.size_bytes,
                    "error_message": record.error_message,
                    "started_at": record.started_at.isoformat(),
                    "completed_at": record.completed_at.isoformat() if record.completed_at else None,
                    "verified_restorable": record.verified_restorable,
                    "verified_at": record.verified_at.isoformat() if record.verified_at else None,
                }
                for record in records
            ]
            self.stdout.write(json.dumps(payload))
            return

        if not records:
            self.stdout.write("No backup records found.")
            return

        for record in records:
            verified = "verified" if record.verified_restorable else "unverified"
            self.stdout.write(
                f"{record.started_at:%Y-%m-%d %H:%M:%S}  {record.backup_type:15s}  "
                f"{record.status:8s}  {verified:10s}  {record.id}"
            )
