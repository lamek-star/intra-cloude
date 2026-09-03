"""
`restore_backup` is the management command
Invoke-IntraCloudRestore.ps1/the Control Center actually shell out to
(same pattern list_backups/run_backup/verify_backup already established
-- see test_list_backups_command.py). These tests exercise the command
layer itself (argument validation, --yes gate, audit event) against
real BackupRecord rows; the restore mechanism's own correctness is
covered directly in test_backups.py's RestoreBackupTests.
"""

from io import StringIO
from unittest.mock import patch

from django.core.management import CommandError, call_command
from django.test import TestCase

from audit.models import AuditEvent
from system.models import BackupRecord


class RestoreBackupCommandTests(TestCase):
    def test_refuses_to_run_without_yes(self):
        record = BackupRecord.objects.create(
            backup_type=BackupRecord.BackupType.CONTROL_DB, status=BackupRecord.Status.SUCCESS,
            file_path="/backups/whatever.dump",
        )
        with self.assertRaisesMessage(CommandError, "--yes"):
            call_command("restore_backup", str(record.id))

    def test_rejects_a_record_id_that_is_not_a_valid_uuid(self):
        with self.assertRaisesMessage(CommandError, "not a valid backup record id"):
            call_command("restore_backup", "not-a-uuid", "--yes")

    def test_rejects_a_record_id_that_does_not_exist(self):
        with self.assertRaisesMessage(CommandError, "No backup record found"):
            call_command("restore_backup", "00000000-0000-0000-0000-000000000000", "--yes")

    def test_success_prints_confirmation_and_emits_an_audit_event(self):
        record = BackupRecord.objects.create(
            backup_type=BackupRecord.BackupType.CONTROL_DB, status=BackupRecord.Status.SUCCESS,
            file_path="/backups/whatever.dump",
        )
        fake_restored = BackupRecord.objects.get(id=record.id)
        fake_restored.restore_error = ""

        target = "system.management.commands.restore_backup.backups.restore_backup"
        with patch(target, return_value=fake_restored):
            out = StringIO()
            call_command("restore_backup", str(record.id), "--yes", stdout=out)

        self.assertIn(str(record.id), out.getvalue())
        self.assertIn("restored successfully", out.getvalue())

        event = AuditEvent.objects.get(action="system.backup.restore")
        self.assertEqual(event.result, AuditEvent.Result.SUCCESS)
        self.assertEqual(event.resource_id, str(record.id))
        self.assertEqual(event.context["backup_type"], "control_db")

    def test_failure_raises_CommandError_and_emits_an_error_audit_event(self):
        record = BackupRecord.objects.create(
            backup_type=BackupRecord.BackupType.CONTROL_DB, status=BackupRecord.Status.SUCCESS,
            file_path="/backups/whatever.dump",
        )
        fake_restored = BackupRecord.objects.get(id=record.id)
        fake_restored.restore_error = "pg_restore: error: could not connect"

        target = "system.management.commands.restore_backup.backups.restore_backup"
        with patch(target, return_value=fake_restored):
            with self.assertRaisesMessage(CommandError, "could not connect"):
                call_command("restore_backup", str(record.id), "--yes")

        event = AuditEvent.objects.get(action="system.backup.restore")
        self.assertEqual(event.result, AuditEvent.Result.ERROR)
