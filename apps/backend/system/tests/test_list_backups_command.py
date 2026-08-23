"""
Phase 18: `list_backups --json` is the interface the Windows Control
Center's Backup & Restore screen reads BackupRecord history through
(shelled into the running distro, same pattern as the pre-removal backup
step in installer/scripts/Uninstall-IntraCloudDistro.ps1). These tests
exercise the command itself, not just the query -- real Django command
invocation via call_command, real BackupRecord rows.
"""

import json
from io import StringIO

from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from system.models import BackupRecord


class ListBackupsCommandTests(TestCase):
    def test_json_output_includes_every_field_the_control_center_needs(self):
        record = BackupRecord.objects.create(
            backup_type=BackupRecord.BackupType.TENANT_DB,
            status=BackupRecord.Status.SUCCESS,
            file_path="/backups/tenant_db/x.dump",
            size_bytes=1234,
            verified_restorable=True,
            verified_at=timezone.now(),
        )
        record.completed_at = timezone.now()
        record.save()

        out = StringIO()
        call_command("list_backups", "--json", stdout=out)
        payload = json.loads(out.getvalue())

        self.assertEqual(len(payload), 1)
        row = payload[0]
        self.assertEqual(row["id"], str(record.id))
        self.assertEqual(row["backup_type"], "tenant_db")
        self.assertEqual(row["status"], "success")
        self.assertEqual(row["size_bytes"], 1234)
        self.assertTrue(row["verified_restorable"])
        self.assertIsNotNone(row["completed_at"])
        self.assertIsNotNone(row["verified_at"])

    def test_json_output_is_empty_array_not_error_when_no_backups_exist(self):
        out = StringIO()
        call_command("list_backups", "--json", stdout=out)
        self.assertEqual(json.loads(out.getvalue()), [])

    def test_most_recent_backup_is_listed_first(self):
        older = BackupRecord.objects.create(backup_type=BackupRecord.BackupType.CONTROL_DB)
        yesterday = timezone.now() - timezone.timedelta(days=1)
        BackupRecord.objects.filter(pk=older.pk).update(started_at=yesterday)
        newer = BackupRecord.objects.create(backup_type=BackupRecord.BackupType.CONTROL_DB)

        out = StringIO()
        call_command("list_backups", "--json", stdout=out)
        payload = json.loads(out.getvalue())

        self.assertEqual(payload[0]["id"], str(newer.id))
        self.assertEqual(payload[1]["id"], str(older.id))

    def test_backup_type_filter_excludes_other_types(self):
        BackupRecord.objects.create(backup_type=BackupRecord.BackupType.CONTROL_DB)
        tenant = BackupRecord.objects.create(backup_type=BackupRecord.BackupType.TENANT_DB)

        out = StringIO()
        call_command("list_backups", "--json", "--backup-type", "tenant_db", stdout=out)
        payload = json.loads(out.getvalue())

        self.assertEqual(len(payload), 1)
        self.assertEqual(payload[0]["id"], str(tenant.id))

    def test_limit_caps_the_number_of_rows_returned(self):
        for _ in range(3):
            BackupRecord.objects.create(backup_type=BackupRecord.BackupType.CONFIGURATION)

        out = StringIO()
        call_command("list_backups", "--json", "--limit", "2", stdout=out)
        payload = json.loads(out.getvalue())

        self.assertEqual(len(payload), 2)

    def test_human_readable_output_does_not_crash_and_mentions_the_backup_id(self):
        record = BackupRecord.objects.create(backup_type=BackupRecord.BackupType.OBJECT_STORAGE)

        out = StringIO()
        call_command("list_backups", stdout=out)

        self.assertIn(str(record.id), out.getvalue())

    def test_human_readable_output_with_no_backups_says_so_rather_than_printing_nothing(self):
        out = StringIO()
        call_command("list_backups", stdout=out)
        self.assertIn("No backup records found.", out.getvalue())
