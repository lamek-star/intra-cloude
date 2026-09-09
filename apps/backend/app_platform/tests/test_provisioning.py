import io
import os
import signal
import subprocess
import sys
import tempfile
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

from django.core.management import call_command
from django.db import IntegrityError, close_old_connections, connections, transaction
from django.test import TransactionTestCase
from django.utils import timezone
from psycopg import sql
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.test import APIClient

from accounts.models import User
from app_platform import instances, provisioning, runtime_build, templates
from app_platform.models import RuntimeProvision
from app_platform.runtime_plan import plan_runtime
from app_platform.tests.test_foundation import project_for, sample
from audit.models import AuditEvent
from databases import rows, services
from databases.models import DBColumn, DBTable, TenantDatabase
from exports import builder, recovery
from exports.services import stage_restore_upload
from organizations.models import Membership
from organizations.services import create_organization
from permissions.services import grant_resource_permission
from system import backups
from system.models import BackupRecord


class ProvisioningTests(TransactionTestCase):
    databases = {"default", "tenant"}

    def setUp(self):
        self.extra_schemas = set()
        call_command("seed_permissions", verbosity=0)
        self.actor = User.objects.create_user(email="provision@example.com")
        self.other = User.objects.create_user(email="provision-other@example.com")
        self.org = create_organization(name="Provision", created_by=self.actor)
        self.project = project_for(self.actor, self.org)
        definition = sample()
        definition["models"][0]["fields"][0]["required"] = True
        template = templates.create_template(self.actor, self.org, {"label": "App", "draft": definition})
        version = templates.publish_template(self.actor, template)
        self.instance = instances.install(
            self.actor, self.project, {"label": "Runtime", "template_version": str(version.id)}
        )
        self.plan = plan_runtime(self.actor, self.instance)
        self.url = f"/api/v1/app-instances/{self.instance.id}/runtime/"
        self.client = APIClient()
        self.client.force_authenticate(self.actor)

    def tearDown(self):
        # Exact schema derived from this isolated test's own newly created UUID.
        with connections["tenant"].cursor() as cursor:
            for schema in {self.plan["schema_name"], *self.extra_schemas}:
                cursor.execute(sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE").format(sql.Identifier(schema)))
        super().tearDown()

    def reserve(self):
        return provisioning.reserve(self.actor, self.instance, self.plan["fingerprint"])

    def ready(self):
        self.reserve()
        return provisioning.execute(self.instance.id, self.actor)

    def schema_exists(self):
        with connections["tenant"].cursor() as cursor:
            cursor.execute("SELECT 1 FROM pg_namespace WHERE nspname=%s", [self.plan["schema_name"]])
            return bool(cursor.fetchone())

    def item(self, receipt):
        model = self.instance.models.get(key="item")
        return DBTable.objects.get(pk=receipt.bindings["models"][str(model.id)])

    def values(self):
        field = self.instance.models.get(key="item").fields.get(key="name")
        return {f"f_{field.id.hex}": "A real stored part"}

    def test_async_api_reserves_once_polls_and_returns_ready_on_repeat(self):
        self.assertEqual(self.client.get(self.url).status_code, 404)
        with patch("app_platform.runtime_views.provision_runtime_task.delay") as enqueue:
            response = self.client.post(self.url, {"fingerprint": self.plan["fingerprint"]}, format="json")
            self.assertEqual(response.status_code, 202, response.data)
            self.assertEqual(response.data["status"], "pending")
            enqueue.assert_called_once_with(str(self.instance.id), str(self.actor.id))
        self.assertFalse(self.schema_exists())
        ready = provisioning.execute(self.instance.id, self.actor)
        self.assertEqual(self.client.get(self.url).data["database_id"], str(ready.database_id))
        with patch("app_platform.runtime_views.provision_runtime_task.delay") as enqueue:
            self.assertEqual(
                self.client.post(
                    self.url, {"fingerprint": self.plan["fingerprint"]}, format="json"
                ).status_code,
                200,
            )
            enqueue.assert_not_called()
        self.assertEqual(RuntimeProvision.objects.count(), 1)

    def test_stale_plan_and_mass_assignment_are_rejected(self):
        response = self.client.post(self.url, {"fingerprint": "0" * 64}, format="json")
        self.assertEqual(response.status_code, 409)
        response = self.client.post(
            self.url,
            {
                "fingerprint": self.plan["fingerprint"],
                "database_id": str(uuid.uuid4()),
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(RuntimeProvision.objects.exists())

    def test_organization_boundary_and_capabilities(self):
        self.client.force_authenticate(self.other)
        self.assertEqual(self.client.get(self.url).status_code, 404)
        self.assertEqual(
            self.client.post(
                self.url,
                {
                    "fingerprint": self.plan["fingerprint"],
                },
                format="json",
            ).status_code,
            404,
        )
        Membership.objects.create(user=self.other, organization=self.org, status="active")
        grant_resource_permission(
            user=self.other,
            permission_code="app_instance.schema.manage",
            organization_id=self.org.id,
            resource_type="app_instance",
            resource_id=self.instance.id,
            granted_by=self.actor,
        )
        with self.assertRaises(PermissionDenied):
            provisioning.reserve(self.other, self.instance, self.plan["fingerprint"])
        self.assertFalse(RuntimeProvision.objects.exists())

    def test_queued_actor_authority_is_rechecked(self):
        self.reserve()
        self.actor.is_active = False
        self.actor.save(update_fields=["is_active"])
        with self.assertRaises(PermissionDenied):
            provisioning.execute(self.instance.id, self.actor)
        self.assertFalse(self.schema_exists())
        self.assertFalse(TenantDatabase.objects.exists())

    def test_enqueue_outage_keeps_one_retryable_receipt(self):
        with patch(
            "app_platform.runtime_views.provision_runtime_task.delay", side_effect=RuntimeError("offline")
        ):
            response = self.client.post(self.url, {"fingerprint": self.plan["fingerprint"]}, format="json")
        self.assertEqual(response.status_code, 500)
        self.assertEqual(RuntimeProvision.objects.count(), 1)
        self.assertFalse(self.schema_exists())
        with patch("app_platform.runtime_views.provision_runtime_task.delay") as enqueue:
            response = self.client.post(self.url, {"fingerprint": self.plan["fingerprint"]}, format="json")
        self.assertEqual(response.status_code, 202)
        enqueue.assert_called_once()
        self.assertEqual(RuntimeProvision.objects.count(), 1)

    def test_reservation_freezes_structure_but_allows_display_labels(self):
        self.reserve()
        model = self.instance.models.get(key="item")
        instances.update_definition(self.actor, model, {"label": "Renamed item"})
        self.assertEqual(plan_runtime(self.actor, self.instance), self.plan)
        with self.assertRaises(ValidationError):
            instances.add_field(self.actor, model, {"key": "new", "label": "New", "data_type": "text"})
        field = model.fields.get(key="name")
        with self.assertRaises(IntegrityError), transaction.atomic():
            type(field).objects.filter(pk=field.pk).update(required=False)
        with self.assertRaises(IntegrityError), transaction.atomic():
            RuntimeProvision.objects.filter(pk=self.instance.id).update(fingerprint="0" * 64)

    def test_failure_before_tenant_commit_rolls_back_and_retains_receipt(self):
        self.reserve()
        with patch(
            "app_platform.runtime_build.services.create_table", side_effect=RuntimeError("secret value")
        ):
            with self.assertRaises(RuntimeError):
                provisioning.execute(self.instance.id, self.actor)
        self.assertFalse(self.schema_exists())
        self.assertFalse(TenantDatabase.objects.exists())
        receipt = RuntimeProvision.objects.get(pk=self.instance.id)
        self.assertNotIn("secret value", receipt.last_error)
        self.assertEqual(provisioning.status(receipt)["status"], "failed")
        self.assertIsNotNone(provisioning.execute(self.instance.id, self.actor).completed_at)

    def test_failure_after_tenant_commit_reconciles_only_unpublished_schema(self):
        self.reserve()
        with patch("app_platform.provisioning.event", side_effect=RuntimeError("audit unavailable")):
            with self.assertRaises(RuntimeError):
                provisioning.execute(self.instance.id, self.actor)
        self.assertTrue(self.schema_exists())
        self.assertFalse(TenantDatabase.objects.exists())
        receipt = provisioning.execute(self.instance.id, self.actor)
        self.assertEqual(str(receipt.database_id), self.plan["database_id"])
        self.assertEqual(TenantDatabase.objects.count(), 1)

    def test_unmarked_schema_is_not_destroyed(self):
        self.reserve()
        with connections["tenant"].cursor() as cursor:
            cursor.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(self.plan["schema_name"])))
        with self.assertRaises(runtime_build.RuntimeReconciliationRequired):
            provisioning.execute(self.instance.id, self.actor)
        self.assertTrue(self.schema_exists())

    def test_existing_catalog_owner_is_not_destroyed(self):
        self.reserve()
        database = services.create_tenant_database(
            actor=self.actor,
            project=self.project,
            name="Existing",
            _database_id=uuid.UUID(self.plan["database_id"]),
        )
        with self.assertRaises(runtime_build.RuntimeReconciliationRequired):
            provisioning.execute(self.instance.id, self.actor)
        self.assertTrue(self.schema_exists())
        self.assertTrue(TenantDatabase.objects.filter(pk=database.pk).exists())

    def test_real_records_foreign_keys_and_repeat_preserve_data(self):
        receipt = self.ready()
        table = self.item(receipt)
        data = rows.insert_row(table, self.values())
        relation = self.plan["relationships"][0]
        with self.assertRaises(IntegrityError), transaction.atomic(using="tenant"):
            rows.insert_row(table, {**self.values(), relation["column"]: str(uuid.uuid4())})
        target = DBTable.objects.get(pk=receipt.bindings["models"][relation["target_model"]])
        parent = rows.insert_row(target, {})
        rows.update_row(table, data["id"], {relation["column"]: parent["id"]})
        with self.assertRaises(IntegrityError), transaction.atomic(using="tenant"):
            rows.delete_row(target, parent["id"])
        with patch("app_platform.runtime_build.build", side_effect=AssertionError("Must not rebuild")):
            replay = provisioning.execute(self.instance.id, self.actor)
        self.assertEqual(replay.bindings, receipt.bindings)
        self.assertEqual(rows.get_row(table, data["id"])[relation["column"]], parent["id"])

    def test_published_schema_rejects_builder_and_direct_catalog_mutations(self):
        receipt = self.ready()
        table = self.item(receipt)
        for operation in (
            lambda: services.delete_table(actor=self.actor, table=table),
            lambda: services.delete_tenant_database(actor=self.actor, tenant_database=receipt.database),
            lambda: services.add_column(actor=self.actor, table=table, name="extra", data_type="text"),
        ):
            with self.assertRaises(services.SchemaValidationError):
                operation()
        with self.assertRaises(IntegrityError), transaction.atomic():
            DBColumn.objects.filter(table=table, is_primary_key=False).delete()
        with self.assertRaises(IntegrityError), transaction.atomic():
            RuntimeProvision.objects.filter(pk=self.instance.id).update(bindings={})
        self.assertEqual(rows.list_rows(table=table)["count"], 0)

    def test_receipt_rejects_a_database_from_another_organization(self):
        self.reserve()
        other_org = create_organization(name="Other", created_by=self.other)
        other_project = project_for(self.other, other_org)
        # Catalog-only hostile assignment: never create or touch another schema.
        database = TenantDatabase.objects.create(
            id=self.plan["database_id"],
            project=other_project,
            created_by=self.other,
            name="Foreign",
            schema_name=self.plan["schema_name"],
        )
        with self.assertRaises(IntegrityError), transaction.atomic():
            RuntimeProvision.objects.filter(pk=self.instance.id).update(
                database=database,
                completed_at=timezone.now(),
            )

    def test_concurrent_execution_publishes_once(self):
        self.reserve()

        def run(_):
            close_old_connections()
            try:
                return provisioning.execute(self.instance.id, User.objects.get(pk=self.actor.pk)).database_id
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(run, range(2)))
        self.assertEqual(results[0], results[1])
        self.assertEqual(TenantDatabase.objects.count(), 1)
        self.assertEqual(AuditEvent.objects.filter(action="app_instance.runtime.ready").count(), 1)

    def kill_process(self, before_publication):
        environment = os.environ.copy()
        environment["CONTROL_DB_NAME"] = connections["default"].settings_dict["NAME"]
        environment["TENANT_DB_NAME"] = connections["tenant"].settings_dict["NAME"]
        code = f"""
import django, os, signal
django.setup()
from accounts.models import User
from app_platform.models import RuntimeProvision
from app_platform.provisioning import execute
original = RuntimeProvision.save
def interrupted(self, *args, **kwargs):
    if self.completed_at and {before_publication!r}:
        os.kill(os.getpid(), signal.SIGKILL)
    return original(self, *args, **kwargs)
RuntimeProvision.save = interrupted
execute('{self.instance.id}', User.objects.get(pk='{self.actor.id}'))
os.kill(os.getpid(), signal.SIGKILL)
"""
        result = subprocess.run(
            [sys.executable, "-c", code], env=environment, capture_output=True, timeout=60
        )
        self.assertEqual(result.returncode, -signal.SIGKILL, result.stderr.decode())

    def test_real_process_kill_between_commits_is_recoverable(self):
        self.reserve()
        self.kill_process(True)
        self.assertTrue(self.schema_exists())
        self.assertFalse(TenantDatabase.objects.exists())
        receipt = provisioning.execute(self.instance.id, self.actor)
        self.assertIsNotNone(receipt.completed_at)
        self.assertEqual(TenantDatabase.objects.count(), 1)

    def test_real_process_kill_after_publication_does_not_rebuild(self):
        self.reserve()
        self.kill_process(False)
        receipt = RuntimeProvision.objects.get(pk=self.instance.id)
        table = self.item(receipt)
        row = rows.insert_row(table, self.values())
        with patch("app_platform.runtime_build.build", side_effect=AssertionError("Must not rebuild")):
            provisioning.execute(self.instance.id, self.actor)
        self.assertEqual(rows.get_row(table, row["id"]), row)

    def test_full_backups_restore_binding_and_populated_records(self):
        receipt = self.ready()
        table = self.item(receipt)
        row = rows.insert_row(table, self.values())
        records = [
            backups.run_backup(kind)
            for kind in (
                BackupRecord.BackupType.CONTROL_DB,
                BackupRecord.BackupType.TENANT_DB,
            )
        ]
        for record in records:
            self.assertEqual(record.status, BackupRecord.Status.SUCCESS, record.error_message)
        rows.delete_row(table, row["id"])
        # Restore tenant first, then the matching control snapshot; isolated test databases only.
        for record in reversed(records):
            result = backups.restore_backup(record)
            self.assertEqual(result.restore_error, "")
        restored = RuntimeProvision.objects.get(pk=self.instance.id)
        self.assertEqual(restored.bindings, receipt.bindings)
        self.assertEqual(rows.get_row(self.item(restored), row["id"]), row)
        self.assertEqual(provisioning.execute(self.instance.id, self.actor).database_id, receipt.database_id)

    def test_portable_restore_preserves_data_without_claiming_an_app(self):
        receipt = self.ready()
        table = self.item(receipt)
        row = rows.insert_row(table, self.values())
        package, _ = builder.build_export(organization=self.org)
        with patch("exports.tasks.run_restore_task.delay"):
            job = stage_restore_upload(actor=self.actor, uploaded_file=io.BytesIO(package))
        recovery.run_restore(str(job.id), None)
        job.refresh_from_db()
        restored = TenantDatabase.objects.get(project__workspace__organization_id=job.organization_id)
        self.extra_schemas.add(restored.schema_name)
        self.assertEqual(rows.get_row(restored.tables.get(name=table.name), row["id"]), row)
        self.assertEqual(RuntimeProvision.objects.count(), 1)
        self.assertTrue(any("no templates or app instances" in warning for warning in job.report["warnings"]))

    def test_real_celery_worker_loss_redelivers_and_completes_once(self):
        from config.celery import app

        self.reserve()
        environment = os.environ.copy()
        environment["CONTROL_DB_NAME"] = connections["default"].settings_dict["NAME"]
        environment["TENANT_DB_NAME"] = connections["tenant"].settings_dict["NAME"]
        queue = f"runtime-probe-{uuid.uuid4().hex}"
        with tempfile.TemporaryDirectory(prefix="runtime-probe-") as directory:
            with tempfile.TemporaryFile(mode="w+") as log:
                worker = subprocess.Popen(
                    [
                        sys.executable,
                        "-m",
                        "app_platform.tests.provision_worker_probe",
                        str(self.instance.id),
                        f"{directory}/killed",
                        queue,
                    ],
                    env=environment,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                )
                result = None
                try:
                    result = app.send_task(
                        "app_platform.tasks.provision_runtime_task",
                        args=[str(self.instance.id), str(self.actor.id)],
                        queue=queue,
                    )
                    deadline = time.monotonic() + 60
                    transcript = ""
                    while time.monotonic() < deadline:
                        log.seek(0)
                        transcript = log.read()
                        if "WorkerLostError" in transcript and "succeeded" in transcript:
                            break
                        if worker.poll() is not None:
                            self.fail(f"Worker exited early: {transcript}")
                        time.sleep(0.2)
                    self.assertIn("WorkerLostError", transcript)
                    self.assertGreaterEqual(transcript.count(" received"), 2)
                    self.assertIn("succeeded", transcript)
                    self.assertIsNotNone(RuntimeProvision.objects.get(pk=self.instance.id).completed_at)
                    self.assertEqual(TenantDatabase.objects.count(), 1)
                    self.assertEqual(
                        AuditEvent.objects.filter(action="app_instance.runtime.ready").count(), 1
                    )
                finally:
                    worker.terminate()
                    try:
                        worker.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        worker.kill()
                        worker.wait(timeout=10)
                    if result is not None:
                        result.forget()
