"""Real PostgreSQL migration/backup/concurrency and MinIO portable-scope evidence."""

import io
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

from django.core.management import call_command
from django.db import IntegrityError, close_old_connections, connection, transaction
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase

from accounts.models import User
from app_platform import instances, templates
from app_platform.models import AppInstance, AppTemplate, AppTemplateVersion
from app_platform.tests.test_foundation import project_for, sample
from exports import builder, recovery, restorer
from exports.models import RestoreJob
from exports.services import stage_restore_upload
from organizations.models import Organization
from organizations.services import create_organization
from system import backups
from system.models import BackupRecord


class DurabilityTests(TransactionTestCase):
    databases = {"default", "tenant"}

    def setUp(self):
        call_command("seed_permissions", verbosity=0)
        self.actor = User.objects.create_user(email="durability@example.com", password="test-password")
        self.org = create_organization(name="Durable", created_by=self.actor)
        self.project = project_for(self.actor, self.org)
        self.template = templates.create_template(
            self.actor, self.org, {"label": "Example", "draft": sample()}
        )
        self.version = templates.publish_template(self.actor, self.template)
        self.instance = instances.install(
            self.actor,
            self.project,
            {
                "label": "Installed",
                "template_version": str(self.version.id),
            },
        )

    def test_concurrent_publication_allocates_distinct_versions(self):
        def publish():
            close_old_connections()
            try:
                actor = User.objects.get(pk=self.actor.pk)
                template = AppTemplate.objects.get(pk=self.template.pk)
                return templates.publish_template(actor, template).number
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: publish(), range(2)))
        self.assertEqual(sorted(results), [2, 3])
        self.assertEqual(self.template.versions.count(), 3)

    def test_control_backup_restores_metadata_identity_and_immutable_guards(self):
        record = backups.run_backup(BackupRecord.BackupType.CONTROL_DB)
        self.assertEqual(record.status, BackupRecord.Status.SUCCESS, record.error_message)
        model = self.instance.models.get(key="item")
        original_model_id, original_source_id = model.id, model.source_definition_id
        instances.update_definition(self.actor, model, {"label": "After backup"})
        result = backups.restore_backup(record)
        self.assertEqual(result.restore_error, "")
        restored = AppInstance.objects.get(pk=self.instance.pk)
        restored_model = restored.models.get(key="item")
        self.assertEqual(restored_model.label, "Item")
        self.assertEqual(
            (restored_model.id, restored_model.source_definition_id), (original_model_id, original_source_id)
        )
        self.assertEqual(restored.source_version_id, self.version.id)
        self.assertEqual(restored.relationships.get().source_model_id, original_model_id)
        with self.assertRaises(IntegrityError), transaction.atomic():
            AppTemplateVersion.objects.filter(pk=self.version.pk).update(number=100)

    def test_portable_export_reports_exclusion_and_restore_does_not_claim_metadata(self):
        package, _ = builder.build_export(organization=self.org)
        zf, manifest = restorer.open_package(package)
        with zf:
            self.assertIn("app_platform", manifest["excluded"])
            self.assertIn("App Platform", manifest["warnings"][0])
            self.assertFalse(any("app_platform" in name for name in zf.namelist()))
        with patch("exports.tasks.run_restore_task.delay"):
            job = stage_restore_upload(actor=self.actor, uploaded_file=io.BytesIO(package))
        recovery.run_restore(str(job.id), None)
        job.refresh_from_db()
        self.assertEqual(job.status, RestoreJob.Status.COMPLETED)
        self.assertTrue(any("no templates or app instances" in item for item in job.report["warnings"]))
        self.assertFalse(AppTemplate.objects.filter(organization_id=job.organization_id).exists())
        self.assertFalse(AppInstance.objects.filter(organization_id=job.organization_id).exists())
        recovery.run_restore(str(job.id), None)
        self.assertEqual(Organization.objects.count(), 2)
        self.assertEqual(AppInstance.objects.count(), 1)


class FoundationMigrationTests(TransactionTestCase):
    def test_fresh_additive_migration_preserves_existing_organization(self):
        actor = User.objects.create_user(email="fresh-migration@example.com")
        org = Organization.objects.create(name="Existing", slug="existing", created_by=actor)
        current = MigrationExecutor(connection).loader.graph.leaf_nodes("app_platform")
        try:
            MigrationExecutor(connection).migrate([("app_platform", None)])
            self.assertNotIn("app_platform_apptemplate", connection.introspection.table_names())
            MigrationExecutor(connection).migrate(current)
            self.assertEqual(Organization.objects.get(pk=org.pk).name, "Existing")
            self.assertIn("app_platform_apptemplate", connection.introspection.table_names())
            self.assertFalse(MigrationExecutor(connection).migration_plan(current))
        finally:
            MigrationExecutor(connection).migrate(current)

    def test_guard_upgrade_preserves_published_snapshot_and_enforces_immutability(self):
        actor = User.objects.create_user(email="guard-migration@example.com")
        org = Organization.objects.create(name="Existing", slug="existing", created_by=actor)
        current = MigrationExecutor(connection).loader.graph.leaf_nodes("app_platform")
        try:
            executor = MigrationExecutor(connection)
            executor.migrate([("app_platform", "0001_initial")])
            old = executor.loader.project_state([("app_platform", "0001_initial")]).apps
            template = old.get_model("app_platform", "AppTemplate").objects.create(
                organization_id=org.pk,
                created_by_id=actor.pk,
                label="Existing draft",
            )
            version = old.get_model("app_platform", "AppTemplateVersion").objects.create(
                template_id=template.pk,
                number=1,
                created_by_id=actor.pk,
                definition={"schema_version": 1, "models": [], "relationships": []},
                checksum_sha256="a" * 64,
            )
            MigrationExecutor(connection).migrate(current)
            self.assertEqual(AppTemplateVersion.objects.get(pk=version.pk).definition["schema_version"], 1)
            with self.assertRaises(IntegrityError), transaction.atomic():
                AppTemplateVersion.objects.filter(pk=version.pk).update(number=2)
        finally:
            MigrationExecutor(connection).migrate(current)
