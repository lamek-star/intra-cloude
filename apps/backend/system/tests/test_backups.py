"""
Phase 11: real pg_dump/pg_restore backup and restore-verification against
the live control-plane and tenant PostgreSQL servers this test run is
already using — not mocks. Unlike Phase 8's connected-database tests,
these don't need any fixture data to be visible to the external pg_dump
process (they only prove the dump/restore/validate cycle itself works),
so the default transaction-wrapped TestCase is fine here.
"""

import hashlib
import io
import json
import os
import tarfile
from pathlib import Path
from unittest.mock import patch

from django.test import TestCase, TransactionTestCase, override_settings

from exports import container as backup_container
from organizations.models import Organization
from storage.backends import get_client
from system import backups
from system.models import BackupRecord

TEST_BACKUP_ENCRYPTION_KEY = "a-real-generated-backup-encryption-key-1!"


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


class RestoreBackupTests(TransactionTestCase):
    """Real restore into the *live* target a backup came from -- not the
    throwaway isolated target VerifyBackupRestorableTests above proves
    restorability against. TransactionTestCase, not TestCase: restoring
    control_db/tenant_db closes and reopens this process's own ORM
    connection to the target mid-restore (system/backups.py::
    _restore_postgres_backup), which TestCase's enclosing atomic
    transaction/savepoint machinery does not tolerate -- confirmed
    directly (TestCase raised TransactionManagementError on teardown
    the first time this was tried), not assumed."""

    databases = {"default", "tenant"}

    def test_control_db_backup_restores_the_live_target_to_the_backup_point(self):
        from accounts.models import User

        user = User.objects.create_user(email="restore-fixture@example.com", password="x")
        kept = Organization.objects.create(
            name="kept-before-backup", slug="kept-before-backup", created_by=user
        )
        record = backups.run_backup(BackupRecord.BackupType.CONTROL_DB)

        # Mutate the live database after the backup was taken -- this is
        # exactly the "accidental destructive operation" scenario
        # BACKUP_RESTORE.md Section 8 describes restore as the recovery
        # path for.
        Organization.objects.create(name="created-after-backup", slug="created-after-backup", created_by=user)
        kept_id = kept.id
        kept.delete()

        restored = backups.restore_backup(record)

        self.assertEqual(restored.restore_error, "", restored.restore_error)
        self.assertIsNotNone(restored.restored_at)
        self.assertTrue(Organization.objects.filter(id=kept_id).exists())
        self.assertFalse(Organization.objects.filter(slug="created-after-backup").exists())

    def test_tenant_db_backup_restores_into_the_live_target(self):
        record = backups.run_backup(BackupRecord.BackupType.TENANT_DB)
        restored = backups.restore_backup(record)
        self.assertEqual(restored.restore_error, "", restored.restore_error)
        self.assertIsNotNone(restored.restored_at)

    def test_restoring_a_backup_with_a_missing_file_fails_gracefully(self):
        record = BackupRecord.objects.create(
            backup_type=BackupRecord.BackupType.CONTROL_DB,
            status=BackupRecord.Status.SUCCESS,
            file_path="/backups/this-file-does-not-exist.dump",
        )
        restored = backups.restore_backup(record)
        self.assertTrue(restored.restore_error)

    def test_restoring_a_never_completed_backup_is_rejected_without_touching_postgres(self):
        record = BackupRecord.objects.create(
            backup_type=BackupRecord.BackupType.CONTROL_DB, status=BackupRecord.Status.FAILED
        )
        restored = backups.restore_backup(record)
        self.assertIn("did not complete successfully", restored.restore_error)

    def test_configuration_restore_is_refused_by_design_not_attempted(self):
        record = backups.run_backup(BackupRecord.BackupType.CONFIGURATION)
        restored = backups.restore_backup(record)
        self.assertIn("manual operator procedure", restored.restore_error)
        self.assertIsNotNone(restored.restored_at)


class ObjectStorageBackupTests(BackupTestBase):
    """Phase 15: real MinIO objects, archived and restored for real —
    not a fixture-free proof like the Postgres tests above, since
    object storage isn't part of the transaction-wrapped test database
    at all (storage/tests/test_storage.py's own tests already rely on
    this: a plain TestCase talks to real MinIO regardless)."""

    def setUp(self):
        self.client_ = get_client()
        self.key = f"backup-test/{self.id()}.txt"
        self.content = b"real object storage content for a real backup\n" * 10
        self.client_.put_stream(self.key, io.BytesIO(self.content), "text/plain")

    def tearDown(self):
        self.client_.delete(self.key)

    def test_object_storage_backup_produces_a_real_tar_with_a_manifest(self):
        record = backups.run_backup(BackupRecord.BackupType.OBJECT_STORAGE)
        self.assertEqual(record.status, BackupRecord.Status.SUCCESS)
        self.assertTrue(os.path.isfile(record.file_path))

        with tarfile.open(record.file_path, "r") as tar:
            names = tar.getnames()
            self.assertIn(self.key, names)
            self.assertIn("_manifest.json", names)
            manifest = json.loads(tar.extractfile("_manifest.json").read())
            self.assertEqual(manifest[self.key], hashlib.sha256(self.content).hexdigest())
            self.assertEqual(tar.extractfile(self.key).read(), self.content)

    def test_object_storage_backup_restores_and_validates_successfully(self):
        record = backups.run_backup(BackupRecord.BackupType.OBJECT_STORAGE)
        verified = backups.verify_backup_restorable(record)
        self.assertTrue(verified.verified_restorable, verified.verification_error)

    def test_restore_test_scratch_objects_are_cleaned_up_afterward(self):
        record = backups.run_backup(BackupRecord.BackupType.OBJECT_STORAGE)
        backups.verify_backup_restorable(record)

        scratch_prefix = f"_restore_test_{record.id.hex[:16]}/"
        remaining = list(self.client_.list_all_keys())
        self.assertFalse(any(key.startswith(scratch_prefix) for key, _size in remaining))

    def test_tampered_archive_fails_verification(self):
        record = backups.run_backup(BackupRecord.BackupType.OBJECT_STORAGE)

        # Flip a byte inside this test's own object *data*, at a
        # precisely computed offset (tarfile's own offset_data/size for
        # that member) — not a blind "flip the last N bytes of the
        # file", which lands in tar's end-of-archive zero-padding and
        # corrupts nothing real (confirmed by actually running it that
        # way: verification came back True, the corruption went
        # undetected).
        with tarfile.open(record.file_path, "r") as tar:
            member = tar.getmember(self.key)
            offset = member.offset_data + member.size // 2
        with open(record.file_path, "r+b") as f:
            f.seek(offset)
            original = f.read(1)
            f.seek(offset)
            f.write(bytes([original[0] ^ 0xFF]))

        verified = backups.verify_backup_restorable(record)
        self.assertFalse(verified.verified_restorable)


class ObjectStorageRestoreTests(BackupTestBase):
    """Real restore into the object's actual key, not the scratch prefix
    verify_backup_restorable uses -- proves an operator can genuinely
    recover an overwritten/corrupted object, and that restore never
    touches an object the backup never captured."""

    def setUp(self):
        self.client_ = get_client()
        self.key = f"restore-test/{self.id()}.txt"
        self.content = b"the real content as of backup time\n" * 10
        self.client_.put_stream(self.key, io.BytesIO(self.content), "text/plain")

    def tearDown(self):
        self.client_.delete(self.key)

    def test_restore_brings_back_the_backed_up_content_after_the_object_is_overwritten(self):
        record = backups.run_backup(BackupRecord.BackupType.OBJECT_STORAGE)
        self.client_.put_stream(self.key, io.BytesIO(b"corrupted after the backup was taken"), "text/plain")

        restored = backups.restore_backup(record)

        self.assertEqual(restored.restore_error, "", restored.restore_error)
        self.assertIsNotNone(restored.restored_at)
        self.assertEqual(self.client_.get_stream(self.key).read(), self.content)

    def test_restore_does_not_delete_an_object_created_after_the_backup(self):
        record = backups.run_backup(BackupRecord.BackupType.OBJECT_STORAGE)
        new_key = f"restore-test/{self.id()}-created-after-backup.txt"
        self.client_.put_stream(new_key, io.BytesIO(b"created after backup"), "text/plain")
        try:
            backups.restore_backup(record)
            self.assertEqual(self.client_.get_stream(new_key).read(), b"created after backup")
        finally:
            self.client_.delete(new_key)

    def test_restoring_a_tampered_archive_fails_gracefully_without_partial_corruption(self):
        record = backups.run_backup(BackupRecord.BackupType.OBJECT_STORAGE)
        with tarfile.open(record.file_path, "r") as tar:
            member = tar.getmember(self.key)
            offset = member.offset_data + member.size // 2
        with open(record.file_path, "r+b") as f:
            f.seek(offset)
            original = f.read(1)
            f.seek(offset)
            f.write(bytes([original[0] ^ 0xFF]))

        restored = backups.restore_backup(record)
        self.assertTrue(restored.restore_error)


class ConfigurationBackupTests(BackupTestBase):
    def test_unencrypted_configuration_backup_redacts_secrets(self):
        record = backups.run_backup(BackupRecord.BackupType.CONFIGURATION)
        self.assertEqual(record.status, BackupRecord.Status.SUCCESS)
        self.assertTrue(record.file_path.endswith(".json"))

        with open(record.file_path) as f:
            config = json.load(f)
        self.assertIn("<redacted", config["SECRET_KEY"])
        self.assertIn("<redacted", config["CONTROL_DB_PASSWORD"])
        # Non-secret keys are still real.
        self.assertEqual(config["CONTROL_DB_NAME"], os.environ["CONTROL_DB_NAME"])

    def test_unencrypted_configuration_backup_still_verifies(self):
        # Verification only proves every expected key is present — it
        # can't prove the (deliberately redacted) secret values are
        # correct, since they were never captured.
        record = backups.run_backup(BackupRecord.BackupType.CONFIGURATION)
        verified = backups.verify_backup_restorable(record)
        self.assertTrue(verified.verified_restorable, verified.verification_error)

    @override_settings(BACKUP_ENCRYPTION_KEY=TEST_BACKUP_ENCRYPTION_KEY)
    def test_encrypted_configuration_backup_includes_real_secret_values(self):
        record = backups.run_backup(BackupRecord.BackupType.CONFIGURATION)
        self.assertTrue(record.file_path.endswith(".icb"))

        with open(record.file_path, "rb") as f:
            data = f.read()
        plaintext = backup_container.read_container_payload(data, passphrase=TEST_BACKUP_ENCRYPTION_KEY)
        config = json.loads(plaintext)
        self.assertEqual(config["SECRET_KEY"], os.environ["SECRET_KEY"])
        self.assertEqual(config["CONTROL_DB_PASSWORD"], os.environ["CONTROL_DB_PASSWORD"])

        verified = backups.verify_backup_restorable(record)
        self.assertTrue(verified.verified_restorable, verified.verification_error)

    @override_settings(BACKUP_ENCRYPTION_KEY=TEST_BACKUP_ENCRYPTION_KEY)
    def test_encrypted_configuration_backup_wrong_key_fails_to_decrypt(self):
        record = backups.run_backup(BackupRecord.BackupType.CONFIGURATION)
        data = Path(record.file_path).read_bytes()
        with self.assertRaises(backup_container.DecryptionFailed):
            backup_container.read_container_payload(data, passphrase="the wrong key entirely")


class EncryptedPostgresBackupTests(BackupTestBase):
    @override_settings(BACKUP_ENCRYPTION_KEY=TEST_BACKUP_ENCRYPTION_KEY)
    def test_control_db_backup_is_encrypted_at_rest_and_still_restorable(self):
        record = backups.run_backup(BackupRecord.BackupType.CONTROL_DB)
        self.assertEqual(record.status, BackupRecord.Status.SUCCESS)
        self.assertTrue(record.file_path.endswith(".icb"))

        # The file on disk is genuinely not a plain pg_dump — pg_restore
        # would reject it outright if fed directly, unencrypted.
        with open(record.file_path, "rb") as f:
            header = f.read(16)
        self.assertNotIn(b"PGDMP", header)

        verified = backups.verify_backup_restorable(record)
        self.assertTrue(verified.verified_restorable, verified.verification_error)

    def test_verifying_an_encrypted_backup_without_the_key_fails_gracefully(self):
        with override_settings(BACKUP_ENCRYPTION_KEY=TEST_BACKUP_ENCRYPTION_KEY):
            record = backups.run_backup(BackupRecord.BackupType.CONTROL_DB)
        # Simulates the key being lost/rotated away by the time restore
        # is attempted — must fail cleanly, never silently skip
        # decryption and feed ciphertext to pg_restore.
        verified = backups.verify_backup_restorable(record)
        self.assertFalse(verified.verified_restorable)
        self.assertIn("BACKUP_ENCRYPTION_KEY", verified.verification_error)
