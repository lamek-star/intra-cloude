"""Disaster recovery from backup FILES, with no BackupRecord to start from.

`restore_backup <record_id>` needs a BackupRecord row, and those rows live in
the control database -- the very thing a total loss takes away. After a
disaster the operator has a fresh install and the backup files from an
external drive; `restore_backup_file` must work from the files alone. Found by
the destructive recovery drill (scripts/qualification/recovery-drill): on a
fresh install the record-id path fails with "No backup record found".

Each test simulates the disaster faithfully: it deletes the BackupRecord row
that a real total loss would have destroyed, then restores from the file.
"""

import io
import os
import tempfile

from django.conf import settings
from django.core.management import CommandError, call_command
from django.test import TransactionTestCase

from accounts.models import User
from organizations.models import Organization
from storage.backends import get_client
from system import backups
from system.models import BackupRecord


class RestoreFromFileTests(TransactionTestCase):
    databases = {"default", "tenant"}

    def test_control_db_is_restored_from_the_file_alone(self):
        user = User.objects.create_user(email="dr-file@example.com", password="x")
        org = Organization.objects.create(name="dr-file-org", slug="dr-file-org", created_by=user)
        record = backups.run_backup(BackupRecord.BackupType.CONTROL_DB)
        path, org_id = record.file_path, org.id

        org.delete()  # the disaster damages the live data...
        BackupRecord.objects.filter(id=record.id).delete()  # ...and takes the record with it
        self.assertFalse(Organization.objects.filter(id=org_id).exists())

        error = backups.restore_backup_from_file(BackupRecord.BackupType.CONTROL_DB, path)

        self.assertEqual(error, "")
        self.assertTrue(Organization.objects.filter(id=org_id).exists())

    def test_tenant_db_is_restored_from_the_file_alone(self):
        record = backups.run_backup(BackupRecord.BackupType.TENANT_DB)
        path = record.file_path
        BackupRecord.objects.filter(id=record.id).delete()
        self.assertEqual(backups.restore_backup_from_file(BackupRecord.BackupType.TENANT_DB, path), "")

    def test_object_storage_is_restored_from_the_file_alone(self):
        client = get_client()
        key = f"restore-file-test/{self.id()}.txt"
        content = b"business file as of backup time\n" * 20
        client.put_stream(key, io.BytesIO(content), "text/plain")
        try:
            record = backups.run_backup(BackupRecord.BackupType.OBJECT_STORAGE)
            path = record.file_path
            client.delete(key)  # the disaster
            BackupRecord.objects.filter(id=record.id).delete()

            error = backups.restore_backup_from_file(BackupRecord.BackupType.OBJECT_STORAGE, path)

            self.assertEqual(error, "")
            self.assertEqual(client.get_stream(key).read(), content)
        finally:
            client.delete(key)

    def test_a_file_outside_the_backup_directory_is_refused(self):
        with tempfile.NamedTemporaryFile(suffix=".dump") as stray:
            error = backups.restore_backup_from_file(BackupRecord.BackupType.CONTROL_DB, stray.name)
        self.assertIn("must be inside", error)

    def test_a_path_that_escapes_the_backup_directory_is_refused(self):
        sneaky = os.path.join(settings.BACKUP_DIR, "..", "..", "etc", "passwd")
        error = backups.restore_backup_from_file(BackupRecord.BackupType.CONTROL_DB, sneaky)
        self.assertIn("must be inside", error)

    def test_a_missing_file_is_reported_without_touching_the_database(self):
        missing = os.path.join(settings.BACKUP_DIR, "control_db_missing.dump")
        error = backups.restore_backup_from_file(BackupRecord.BackupType.CONTROL_DB, missing)
        self.assertIn("not found", error)

    def test_configuration_and_unknown_types_are_refused(self):
        path = os.path.join(settings.BACKUP_DIR, "x.dump")
        self.assertIn("manual", backups.restore_backup_from_file(BackupRecord.BackupType.CONFIGURATION, path))
        self.assertIn("unsupported", backups.restore_backup_from_file("bogus", path))

    def test_the_command_requires_yes(self):
        path = os.path.join(settings.BACKUP_DIR, "x.dump")
        with self.assertRaisesMessage(CommandError, "--yes"):
            call_command("restore_backup_file", path, "--type", "control_db")

    def test_the_command_restores_from_a_file_and_reports_success(self):
        record = backups.run_backup(BackupRecord.BackupType.TENANT_DB)
        out = io.StringIO()
        call_command("restore_backup_file", record.file_path, "--type", "tenant_db", "--yes", stdout=out)
        self.assertIn("restored", out.getvalue().lower())

    def test_the_command_fails_loudly_when_the_restore_fails(self):
        path = os.path.join(settings.BACKUP_DIR, "control_db_missing.dump")
        with self.assertRaisesMessage(CommandError, "not found"):
            call_command("restore_backup_file", path, "--type", "control_db", "--yes")
