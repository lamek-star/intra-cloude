import json

from django.core.management.base import BaseCommand

from system.backup_inspection import inspect_backup_set


class Command(BaseCommand):
    help = (
        "Checks a backup set before restoring it, without touching any live data: every file readable "
        "and intact (decrypted, archive structure, stored files re-hashed), which applications it holds, "
        "and whether this IntraForge version can restore it. Prints JSON; exit code 1 when it must not "
        "be restored."
    )

    def add_arguments(self, parser):
        parser.add_argument("--control", required=True)
        parser.add_argument("--tenant", required=True)
        parser.add_argument("--objects", required=True)

    def handle(self, *args, **options):
        report = inspect_backup_set(options["control"], options["tenant"], options["objects"])
        self.stdout.write(json.dumps(report))
        if not report["ok"]:
            raise SystemExit(1)
