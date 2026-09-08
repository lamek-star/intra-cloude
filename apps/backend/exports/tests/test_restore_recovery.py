"""Real PostgreSQL/MinIO recovery invariants, including separate connections.

Only fault locations / broker dispatch are patched; publication, constraints,
DDL, file bytes, permissions and audit writes are real.
"""

import io
import os
import signal
import subprocess
import sys
import tempfile
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from unittest import skipUnless
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connections, transaction
from django.urls import reverse
from psycopg import sql
from rest_framework.test import APITransactionTestCase

from accounts.models import User
from audit.models import AuditEvent
from databases.models import TenantDatabase
from exports import builder, recovery, restorer, services
from exports.models import RestoreJob
from exports.tests import test_portable_export as portable
from organizations.models import Organization
from permissions.management.commands.seed_permissions import Command as SeedPermissionsCommand
from storage.backends import get_client
from storage.models import FileObject


class SimulatedCrash(BaseException):
    pass


class RestoreRecoveryTests(APITransactionTestCase):
    databases = {"default", "tenant"}

    def setUp(self):
        SeedPermissionsCommand().handle()
        self.admin = User.objects.create_user(email="recovery-admin@example.com", password="x")
        self.viewer = User.objects.create_user(email="recovery-viewer@example.com", password="x")
        self.client.force_login(self.admin)
        self.source = portable.PortableExportRoundTripTests._build_source_organization(self)
        self.package, _ = builder.build_export(
            organization=Organization.objects.get(id=self.source["org_id"])
        )
        self.job = self.stage()

    def stage(self, **kwargs):
        with patch("exports.tasks.run_restore_task.delay"):
            return services.stage_restore_upload(
                actor=self.admin, uploaded_file=io.BytesIO(self.package), **kwargs
            )

    def tearDown(self):
        # Only schemas from this test's real catalog or its job namespaces.
        ids = set(TenantDatabase.objects.values_list("id", flat=True))
        ids.update(
            uuid.uuid5(job_id, "database:0:0:0") for job_id in RestoreJob.objects.values_list("id", flat=True)
        )
        with connections["tenant"].cursor() as cursor:
            for database_id in ids:
                cursor.execute(
                    sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE").format(
                        sql.Identifier(f"db_{database_id.hex}")
                    )
                )
        super().tearDown()

    def assert_restored_once(self):
        self.job.refresh_from_db()
        self.assertEqual(self.job.status, "completed", self.job.error_message)
        self.assertEqual(Organization.objects.count(), 2)
        org = self.job.organization
        self.assertEqual(org.workspaces.count(), 1)
        self.assertEqual(org.workspaces.get().projects.count(), 1)
        self.assertEqual(TenantDatabase.objects.filter(project__workspace__organization=org).count(), 1)
        file_obj = FileObject.objects.get(bucket__project__workspace__organization=org)
        body = get_client().get_stream(file_obj.object_key)
        try:
            self.assertEqual(body.read(), portable.FILE_CONTENT)
        finally:
            body.close()
        self.assertEqual(
            AuditEvent.objects.filter(
                action="import.restore", resource_id=str(self.job.id), result="success"
            ).count(),
            1,
        )
        self.assertEqual(AuditEvent.objects.filter(action="organization.create", organization=org).count(), 1)
        db = TenantDatabase.objects.get(project__workspace__organization=org)
        with connections["tenant"].cursor() as cursor:
            cursor.execute(sql.SQL("SELECT count(*) FROM {}.orders").format(sql.Identifier(db.schema_name)))
            self.assertEqual(cursor.fetchone()[0], 1)
        self.assertEqual(self.job.report["files_restored"], 1)
        self.assertEqual(self.job.report["rows_imported"], 2)

    def test_normal_and_duplicate_delivery(self):
        from exports.tasks import run_restore_task

        run_restore_task.run(str(self.job.id), None)
        run_restore_task.run(str(self.job.id), None)
        self.assert_restored_once()

    def test_failure_before_work_retains_source_for_retry(self):
        with patch("exports.recovery.prepare_restore", side_effect=ConnectionError("temporary outage")):
            with self.assertRaises(ConnectionError):
                recovery.run_restore(str(self.job.id), None)
        self.job.refresh_from_db()
        self.assertEqual(self.job.status, "failed")
        body = get_client().get_stream(self.job.source_object_key)
        try:
            self.assertTrue(body.read())
        finally:
            body.close()
        recovery.run_restore(str(self.job.id), None)
        self.assert_restored_once()
        self.assertEqual(
            AuditEvent.objects.filter(
                action="import.restore", resource_id=str(self.job.id), result="error"
            ).count(),
            1,
        )

    def test_crash_after_object_upload_reuses_same_key(self):
        from storage.backends import ObjectStorageClient

        original = ObjectStorageClient.put_stream

        def crash(client, *args, **kwargs):
            original(client, *args, **kwargs)
            raise SimulatedCrash()

        with patch.object(ObjectStorageClient, "put_stream", crash):
            with self.assertRaises(SimulatedCrash):
                recovery.run_restore(str(self.job.id), None)
        recovery.run_restore(str(self.job.id), None)
        self.assert_restored_once()
        keys = [
            key for key, _ in get_client().list_all_keys() if key.startswith(f"restore-files/{self.job.id}/")
        ]
        self.assertEqual(len(keys), 1)

    def test_exhausted_task_retry_keeps_failure_and_input(self):
        from exports.tasks import run_restore_task

        with patch("exports.recovery.prepare_restore", side_effect=ConnectionError("outage")):
            with self.assertRaises(ConnectionError):
                run_restore_task.apply(args=[str(self.job.id), None], retries=1)
        self.job.refresh_from_db()
        self.assertEqual(self.job.status, "failed")
        recovery.run_restore(str(self.job.id), None)
        self.assert_restored_once()

    def test_outer_catalog_rollback_keeps_retry_input(self):
        with self.assertRaises(SimulatedCrash):
            with transaction.atomic():
                recovery.run_restore(str(self.job.id), None)
                body = get_client().get_stream(self.job.source_object_key)
                try:
                    self.assertEqual(body.read(), self.package)
                finally:
                    body.close()
                raise SimulatedCrash()
        recovery.run_restore(str(self.job.id), None)
        self.assert_restored_once()

    def test_crash_after_organization_creation(self):
        original = restorer.create_organization

        def crash(**kwargs):
            original(**kwargs)
            raise SimulatedCrash()

        with patch("exports.restorer.create_organization", side_effect=crash):
            with self.assertRaises(SimulatedCrash):
                recovery.run_restore(str(self.job.id), None)
        self.assertEqual(Organization.objects.count(), 1)
        recovery.run_restore(str(self.job.id), None)
        self.assert_restored_once()

    def test_crash_after_partial_children(self):
        original = restorer._restore_tenant_database

        def crash(*args, **kwargs):
            original(*args, **kwargs)
            raise SimulatedCrash()

        with patch("exports.restorer._restore_tenant_database", side_effect=crash):
            with self.assertRaises(SimulatedCrash):
                recovery.run_restore(str(self.job.id), None)
        recovery.run_restore(str(self.job.id), None)
        self.assert_restored_once()

    def test_crash_after_file_catalog_creation(self):
        original = restorer.publish_upload

        def crash(**kwargs):
            original(**kwargs)
            raise SimulatedCrash()

        with patch("exports.restorer.publish_upload", side_effect=crash):
            with self.assertRaises(SimulatedCrash):
                recovery.run_restore(str(self.job.id), None)
        recovery.run_restore(str(self.job.id), None)
        self.assert_restored_once()
        keys = [
            key for key, _ in get_client().list_all_keys() if key.startswith(f"restore-files/{self.job.id}/")
        ]
        self.assertEqual(len(keys), 1)

    def test_tenant_commit_before_control_commit_is_reconciled(self):
        original = RestoreJob.save

        def crash(instance, *args, **kwargs):
            if instance.status == "completed":
                raise SimulatedCrash()
            return original(instance, *args, **kwargs)

        with patch.object(RestoreJob, "save", crash):
            with self.assertRaises(SimulatedCrash):
                recovery.run_restore(str(self.job.id), None)
        self.assertEqual(Organization.objects.count(), 1)
        schema = f"db_{uuid.uuid5(self.job.id, 'database:0:0:0').hex}"
        with connections["tenant"].cursor() as cursor:
            cursor.execute("SELECT 1 FROM pg_namespace WHERE nspname=%s", [schema])
            self.assertIsNotNone(cursor.fetchone())
        recovery.run_restore(str(self.job.id), None)
        self.assert_restored_once()
        self.assertEqual(
            AuditEvent.objects.filter(
                action="import.restore.reconcile", resource_id=str(self.job.id)
            ).count(),
            1,
        )

    def test_completion_then_crash_does_not_republish(self):
        with patch("exports.recovery.cleanup_completed_source", side_effect=SimulatedCrash):
            with self.assertRaises(SimulatedCrash):
                recovery.run_restore(str(self.job.id), None)
        recovery.run_restore(str(self.job.id), None)
        self.assert_restored_once()

    def test_concurrent_executions_publish_once(self):
        barrier = threading.Barrier(2)
        original = recovery.prepare_restore

        def prepare(*args):
            plan = original(*args)
            barrier.wait(timeout=20)
            return plan

        def run():
            try:
                recovery.run_restore(str(self.job.id), None)
            finally:
                connections.close_all()

        with patch("exports.recovery.prepare_restore", side_effect=prepare):
            with ThreadPoolExecutor(max_workers=2) as pool:
                futures = [pool.submit(run), pool.submit(run)]
                for future in futures:
                    future.result(timeout=40)
        self.assert_restored_once()

    def test_idempotency_key_scope_conflict_and_owner_visibility(self):
        key = uuid.uuid4()
        first = self.stage(idempotency_key=key)
        second = self.stage(idempotency_key=key)
        self.assertEqual(first.id, second.id)
        with self.assertRaises(services.RestoreRequestConflict):
            self.stage(idempotency_key=key, passphrase="different secret")
        with patch("exports.tasks.run_restore_task.delay"):
            outsider_job = services.stage_restore_upload(
                actor=self.viewer, uploaded_file=io.BytesIO(self.package), idempotency_key=key
            )
        self.assertNotEqual(first.id, outsider_job.id)
        self.client.force_login(self.viewer)
        self.assertEqual(self.client.get(reverse("restore-job-detail", args=[first.id])).status_code, 404)

    def test_api_duplicate_submission_and_conflict(self):
        key = str(uuid.uuid4())

        def post(content=self.package, key_value=key):
            return self.client.post(
                reverse("restore-job-list-create"),
                {"package": SimpleUploadedFile("test.icp", content)},
                format="multipart",
                HTTP_IDEMPOTENCY_KEY=key_value,
            )

        first, second = post(), post()
        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 201)
        self.assertEqual(first.data["id"], second.data["id"])
        self.assertEqual(Organization.objects.count(), 2)
        self.assertEqual(post(b"different").status_code, 409)
        self.assertEqual(post(key_value="not-a-uuid").status_code, 400)
        self.client.logout()
        self.assertIn(post().status_code, (401, 403))

    def test_concurrent_api_keys_create_one_job(self):
        key = uuid.uuid4()
        barrier = threading.Barrier(2)

        def stage():
            try:
                barrier.wait(timeout=10)
                return services.stage_restore_upload(
                    actor=self.admin, uploaded_file=io.BytesIO(self.package), idempotency_key=key
                ).id
            finally:
                connections.close_all()

        with patch("exports.tasks.run_restore_task.delay"):
            with ThreadPoolExecutor(max_workers=2) as pool:
                first, second = pool.submit(stage), pool.submit(stage)
                self.assertEqual(first.result(timeout=30), second.result(timeout=30))
        self.assertEqual(RestoreJob.objects.filter(created_by=self.admin, idempotency_key=key).count(), 1)

    def test_late_failing_execution_cannot_downgrade_completed(self):
        recovery.run_restore(str(self.job.id), None)
        self.assertFalse(recovery._record_failure(self.job.id, ConnectionError("late loser")))
        self.assert_restored_once()

    def test_success_audit_failure_rolls_back_publication(self):
        original = recovery.audit.record

        def fail(**kwargs):
            if kwargs["action"] == "import.restore" and "report" in kwargs.get("context", {}):
                raise SimulatedCrash()
            return original(**kwargs)

        with patch("exports.recovery.audit.record", side_effect=fail):
            with self.assertRaises(SimulatedCrash):
                recovery.run_restore(str(self.job.id), None)
        self.job.refresh_from_db()
        self.assertNotEqual(self.job.status, "completed")
        self.assertEqual(Organization.objects.count(), 1)
        recovery.run_restore(str(self.job.id), None)
        self.assert_restored_once()

    def test_completed_job_stays_completed_after_target_deleted(self):
        recovery.run_restore(str(self.job.id), None)
        self.job.refresh_from_db()
        self.job.organization.delete()
        recovery.run_restore(str(self.job.id), None)
        self.job.refresh_from_db()
        self.assertEqual(self.job.status, "completed")
        self.assertEqual(Organization.objects.count(), 1)

    def test_changed_staged_package_is_rejected(self):
        get_client().put_stream(
            self.job.source_object_key, io.BytesIO(b"tampered"), "application/octet-stream"
        )
        with self.assertRaises(restorer.PackageValidationError):
            recovery.run_restore(str(self.job.id), None)
        self.assertEqual(Organization.objects.count(), 1)

    def test_legacy_incomplete_job_is_not_replayed(self):
        RestoreJob.objects.filter(id=self.job.id).update(recovery_version=0)
        with self.assertRaises(recovery.RestoreReconciliationRequired):
            recovery.run_restore(str(self.job.id), None)
        self.assertEqual(Organization.objects.count(), 1)

    def test_inactive_owner_is_denied(self):
        self.admin.is_active = False
        self.admin.save(update_fields=["is_active"])
        with self.assertRaises(PermissionError):
            recovery.run_restore(str(self.job.id), None)
        self.assertEqual(Organization.objects.count(), 1)

    def test_upload_preparation_has_no_open_database_transaction(self):
        from storage.backends import ObjectStorageClient

        original = ObjectStorageClient.put_stream

        def put(client, *args, **kwargs):
            self.assertFalse(connections["default"].in_atomic_block)
            self.assertFalse(connections["tenant"].in_atomic_block)
            return original(client, *args, **kwargs)

        with patch.object(ObjectStorageClient, "put_stream", put):
            recovery.run_restore(str(self.job.id), None)
        self.assert_restored_once()

    def test_real_process_kill_between_database_commits(self):
        if not hasattr(signal, "SIGKILL"):
            self.skipTest("requires POSIX SIGKILL; exercised on Linux integration runners")
        env = os.environ.copy()
        env["CONTROL_DB_NAME"] = connections["default"].settings_dict["NAME"]
        env["TENANT_DB_NAME"] = connections["tenant"].settings_dict["NAME"]
        script = """
import os, signal, sys, django
django.setup()
from exports.models import RestoreJob
from exports.recovery import run_restore
original = RestoreJob.save
def kill(instance, *args, **kwargs):
    if instance.status == 'completed':
        os.kill(os.getpid(), signal.SIGKILL)
    return original(instance, *args, **kwargs)
RestoreJob.save = kill
run_restore(sys.argv[1], None)
"""
        result = subprocess.run([sys.executable, "-c", script, str(self.job.id)], env=env, timeout=60)
        self.assertEqual(result.returncode, -signal.SIGKILL)
        recovery.run_restore(str(self.job.id), None)
        self.assert_restored_once()

    def _worker_crash_probe(self, boundary):
        from config.celery import app

        env = os.environ.copy()
        env["CONTROL_DB_NAME"] = connections["default"].settings_dict["NAME"]
        env["TENANT_DB_NAME"] = connections["tenant"].settings_dict["NAME"]
        queue = f"restore-probe-{uuid.uuid4().hex}"
        with tempfile.TemporaryDirectory(prefix="restore-worker-probe-") as directory:
            with tempfile.TemporaryFile(mode="w+") as logfile:
                worker = subprocess.Popen(
                    [
                        sys.executable,
                        "-m",
                        "exports.tests.worker_probe",
                        str(self.job.id),
                        boundary,
                        f"{directory}/killed",
                        queue,
                    ],
                    env=env,
                    stdout=logfile,
                    stderr=subprocess.STDOUT,
                )
                result = None
                try:
                    result = app.send_task(
                        "exports.tasks.run_restore_task", args=[str(self.job.id), None], queue=queue
                    )
                    deadline = time.monotonic() + 60
                    transcript = ""
                    while time.monotonic() < deadline:
                        self.job.refresh_from_db()
                        logfile.seek(0)
                        transcript = logfile.read()
                        if (
                            self.job.status == "completed"
                            and "WorkerLostError" in transcript
                            and "succeeded" in transcript
                        ):
                            break
                        if worker.poll() is not None:
                            self.fail(f"Probe worker exited early:\n{transcript}")
                        time.sleep(0.2)
                    self.assertIn("WorkerLostError", transcript)
                    self.assertGreaterEqual(transcript.count(" received"), 2)
                    self.assertIn("succeeded", transcript)
                    self.assert_restored_once()
                finally:
                    worker.terminate()
                    try:
                        worker.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        worker.kill()
                        worker.wait(timeout=10)
                    if result is not None:
                        result.forget()

    @skipUnless(os.environ.get("RUN_RESTORE_WORKER_TESTS") == "1", "opt-in real broker/prefork SIGKILL probe")
    def test_celery_worker_crash_after_tenant_commit(self):
        self._worker_crash_probe("tenant_commit")

    @skipUnless(os.environ.get("RUN_RESTORE_WORKER_TESTS") == "1", "opt-in real broker/prefork SIGKILL probe")
    def test_celery_worker_crash_after_completed_commit(self):
        self._worker_crash_probe("completed")
