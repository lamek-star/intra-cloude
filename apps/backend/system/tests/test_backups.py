"""
Phase 11: real pg_dump/pg_restore backup and restore-verification against
the live control-plane and tenant PostgreSQL servers this test run is
already using — not mocks. Unlike Phase 8's connected-database tests,
these don't need any fixture data to be visible to the external pg_dump
process (they only prove the dump/restore/validate cycle itself works),
so the default transaction-wrapped TestCase is fine here.
"""

import os
from unittest.mock import patch

from django.test import TestCase

from system import backups
from system.models import BackupRecord


class BackupTestBase(TestCase):
    databases = {"default", "tenant"}


class RunBackupTests(BackupTestBase):
    def test_control_db_backup_produces_a_real_nonempty_dump_file(self):
        record = backups.run_backup(BackupRecord.BackupType.CONTROL_DB)
        self.assertEqual(record.status, BackupRecord.Status.SUCCESS)
        self.assertTrue(os.path.isfile(record.file_path))
        self.assertGreater(record.size_bytes, 0)
        self.assertEqual(os.path.getsize(record.file_path), record.size_bytes)

    def test_tenant_db_backup_produces_a_real_nonempty_dump_file(self):
        record = backups.run_backup(BackupRecord.BackupType.TENANT_DB)
        self.assertEqual(record.status, BackupRecord.Status.SUCCESS)
        self.assertTrue(os.path.isfile(record.file_path))
        self.assertGreater(record.size_bytes, 0)

    def test_backup_against_unreachable_database_fails_without_raising(self):
        # The BackupRecord itself is still written through the real
        # "default" ORM connection (the same one this test's own
        # transaction wrapper uses) — only the pg_dump subprocess's
        # target host is faked, via the one function that resolves it,
        # rather than trying to override Django's live DATABASES setting
        # for an alias that's already mid-transaction for this very test.
        bad_db = {"HOST": "192.0.2.1", "PORT": 5432, "USER": "x", "PASSWORD": "x", "NAME": "x"}
        with patch("system.backups._db_settings", return_value=bad_db):
            record = backups.run_backup(BackupRecord.BackupType.CONTROL_DB)
        self.assertEqual(record.status, BackupRecord.Status.FAILED)
        self.assertTrue(record.error_message)


class VerifyBackupRestorableTests(BackupTestBase):
    def test_a_real_backup_restores_and_validates_successfully(self):
        record = backups.run_backup(BackupRecord.BackupType.CONTROL_DB)
        verified = backups.verify_backup_restorable(record)

        self.assertTrue(verified.verified_restorable)
        self.assertEqual(verified.verification_error, "")
        self.assertIsNotNone(verified.verified_at)

    def test_tenant_backup_restores_and_validates_successfully(self):
        record = backups.run_backup(BackupRecord.BackupType.TENANT_DB)
        verified = backups.verify_backup_restorable(record)

        self.assertTrue(verified.verified_restorable)

    def test_the_isolated_restore_test_database_is_dropped_afterward(self):
        record = backups.run_backup(BackupRecord.BackupType.CONTROL_DB)
        backups.verify_backup_restorable(record)

        test_db_name = f"restore_test_{record.id.hex[:16]}"
        with backups._admin_connect(backups._db_settings(record.backup_type)) as conn, conn.cursor() as cur:
            cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", [test_db_name])
            self.assertIsNone(cur.fetchone())

    def test_verifying_a_backup_with_a_missing_file_fails_gracefully(self):
        record = BackupRecord.objects.create(
            backup_type=BackupRecord.BackupType.CONTROL_DB,
            status=BackupRecord.Status.SUCCESS,
            file_path="/backups/this-file-does-not-exist.dump",
        )
        verified = backups.verify_backup_restorable(record)
        self.assertFalse(verified.verified_restorable)
        self.assertTrue(verified.verification_error)

    def test_verifying_a_never_completed_backup_is_rejected_without_touching_postgres(self):
        record = BackupRecord.objects.create(
            backup_type=BackupRecord.BackupType.CONTROL_DB, status=BackupRecord.Status.FAILED
        )
        verified = backups.verify_backup_restorable(record)
        self.assertFalse(verified.verified_restorable)
        self.assertIn("did not complete successfully", verified.verification_error)
