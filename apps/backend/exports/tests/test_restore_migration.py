"""Upgrade preserves old jobs without falsely declaring them replay-safe."""

from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase

from accounts.models import User


class RestoreRecoveryMigrationTests(TransactionTestCase):
    def test_existing_jobs_remain_legacy_and_new_jobs_use_recovery_version(self):
        previous = [("exports", "0001_initial")]
        current = [("exports", "0002_restore_recovery_identity")]
        # Only exports is rolled back. The accounts table still has its
        # current MFA fields, so its fixture must use the current model.
        actor = User.objects.create_user(email="migration-test@example.com")
        executor = MigrationExecutor(connection)
        try:
            executor.migrate(previous)
            old = executor.loader.project_state(previous).apps
            job = old.get_model("exports", "RestoreJob").objects.create(
                created_by_id=actor.id, source_object_key="legacy.icp", status="restoring"
            )
            executor = MigrationExecutor(connection)
            executor.migrate(current)
            new = executor.loader.project_state(current).apps.get_model("exports", "RestoreJob")
            migrated = new.objects.get(id=job.id)
            self.assertEqual(migrated.recovery_version, 0)
            self.assertEqual(migrated.status, "restoring")
            self.assertEqual(migrated.source_object_key, "legacy.icp")
            self.assertIsNone(migrated.idempotency_key)
            self.assertEqual(new.objects.create(created_by_id=actor.id).recovery_version, 1)
        finally:
            MigrationExecutor(connection).migrate(current)
