"""
Full round-trip: upload a CSV via storage, create a real tenant table via
the database builder, preview the CSV, run an import job (Celery in eager
mode — see config/settings/test.py), and verify the actual rows landed in
the real tenant PostgreSQL table.
"""

from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import OperationalError, connections
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import User
from audit.models import AuditEvent
from databases.models import TenantDatabase
from imports.models import ImportJob
from imports.services import _convert_value as real_convert_value
from imports.services import run_import
from organizations.models import Membership
from permissions.management.commands.seed_permissions import Command as SeedPermissionsCommand

CSV_CONTENT = b"name,age,active\nAlice,30,true\nBob,25,false\nCarol,not-a-number,true\n"


class ImportTestBase(APITestCase):
    databases = {"default", "tenant"}

    def setUp(self):
        SeedPermissionsCommand().handle()
        self.admin = User.objects.create_user(email="import-admin@example.com", password="x")
        self.client.force_login(self.admin)

        org = self.client.post(reverse("organization-list-create"), {"name": "Acme"})
        self.org_id = org.data["id"]
        ws = self.client.post(reverse("workspace-list-create", args=[self.org_id]), {"name": "WS"})
        proj = self.client.post(reverse("project-list-create", args=[ws.data["id"]]), {"name": "Proj"})
        self.project_id = proj.data["id"]

        bucket = self.client.post(reverse("bucket-list-create", args=[self.project_id]), {"name": "uploads"})
        self.bucket_id = bucket.data["id"]

        db = self.client.post(
            reverse("tenant-database-list-create", args=[self.project_id]), {"name": "AppDB"}
        )
        self.tenant_database_id = db.data["id"]
        self.schema_name = TenantDatabase.objects.get(id=self.tenant_database_id).schema_name

        table = self.client.post(
            reverse("table-list-create", args=[self.tenant_database_id]), {"name": "people"}
        )
        self.table_id = table.data["id"]
        self.client.post(
            reverse("column-create", args=[self.table_id]),
            {"name": "name", "data_type": "text"},
            format="json",
        )
        self.client.post(
            reverse("column-create", args=[self.table_id]),
            {"name": "age", "data_type": "integer"},
            format="json",
        )
        self.client.post(
            reverse("column-create", args=[self.table_id]),
            {"name": "active", "data_type": "boolean"},
            format="json",
        )

        upload = self.client.post(
            reverse("file-list-create", args=[self.bucket_id]),
            {"file": SimpleUploadedFile("people.csv", CSV_CONTENT, content_type="text/csv")},
            format="multipart",
        )
        self.file_id = upload.data["id"]

        self.column_mapping = [
            {"csv_column": "name", "target_column": "name", "target_type": "text"},
            {"csv_column": "age", "target_column": "age", "target_type": "integer"},
            {"csv_column": "active", "target_column": "active", "target_type": "boolean"},
        ]


class ImportPreviewTests(ImportTestBase):
    def test_preview_returns_headers_sample_and_inferred_types(self):
        response = self.client.get(reverse("import-preview", args=[self.file_id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["headers"], ["name", "age", "active"])
        self.assertEqual(len(response.data["sample_rows"]), 3)
        types = {c["csv_column"]: c["inferred_type"] for c in response.data["columns"]}
        # "age" mixes an integer-looking column with one bad value in the
        # sample ("not-a-number"), so the honest inference is text — the
        # user corrects it in the mapping, which is exactly the point
        # (Section 11: never silently auto-apply an inferred type).
        self.assertEqual(types["age"], "text")


class ImportJobRoundTripTests(ImportTestBase):
    def test_import_creates_rows_and_reports_the_bad_row(self):
        response = self.client.post(
            reverse("import-job-list-create", args=[self.table_id]),
            {
                "file_id": self.file_id,
                "encoding": "utf-8",
                "delimiter": ",",
                "column_mapping": self.column_mapping,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        job_id = response.data["id"]

        job = ImportJob.objects.get(id=job_id)
        self.assertEqual(job.status, ImportJob.Status.COMPLETED)
        self.assertEqual(job.imported_rows, 2)
        self.assertEqual(job.rejected_rows, 1)
        self.assertEqual(job.total_rows, 3)

        with connections["tenant"].cursor() as cursor:
            cursor.execute(f'SELECT name, age, active FROM "{self.schema_name}"."people" ORDER BY name')
            rows = cursor.fetchall()
        self.assertEqual(rows, [("Alice", 30, True), ("Bob", 25, False)])

        errors_response = self.client.get(reverse("import-job-error-list", args=[job_id]))
        self.assertEqual(len(errors_response.data), 1)
        self.assertEqual(errors_response.data[0]["row_number"], 3)

    def test_detail_endpoint_reflects_final_status(self):
        create = self.client.post(
            reverse("import-job-list-create", args=[self.table_id]),
            {
                "file_id": self.file_id,
                "encoding": "utf-8",
                "delimiter": ",",
                "column_mapping": self.column_mapping,
            },
            format="json",
        )
        detail = self.client.get(reverse("import-job-detail", args=[create.data["id"]]))
        self.assertEqual(detail.data["status"], "completed")

    def test_mapping_to_the_generated_id_column_is_rejected(self):
        bad_mapping = [
            *self.column_mapping,
            {"csv_column": "name", "target_column": "id", "target_type": "uuid"},
        ]
        response = self.client.post(
            reverse("import-job-list-create", args=[self.table_id]),
            {"file_id": self.file_id, "encoding": "utf-8", "delimiter": ",", "column_mapping": bad_mapping},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_mismatched_target_type_is_rejected(self):
        bad_mapping = [
            {"csv_column": "name", "target_column": "name", "target_type": "integer"},  # actually text
        ]
        response = self.client.post(
            reverse("import-job-list-create", args=[self.table_id]),
            {"file_id": self.file_id, "encoding": "utf-8", "delimiter": ",", "column_mapping": bad_mapping},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_connection_failure_is_reraised_and_progress_checkpointed_for_retry(self):
        """imports/services.py used to swallow every exception from the
        per-row block, including a broken connection, as if it were a
        bad row — meaning imports/tasks.py's configured Celery retry
        could never actually fire, and (a separate bug found while
        fixing that) the row that was mid-flight when it broke got
        checkpointed as already-done, silently dropping it on retry.
        This proves both are fixed: the failure propagates, and a
        second run_import() call (standing in for the real worker's
        retry, verified separately against a live worker) picks up
        exactly where it left off with nothing skipped or duplicated."""
        job = ImportJob.objects.create(
            file_id=self.file_id,
            table_id=self.table_id,
            encoding="utf-8",
            delimiter=",",
            column_mapping=self.column_mapping,
            created_by=self.admin,
        )

        calls = {"n": 0}

        def flaky_convert(raw, data_type):
            calls["n"] += 1
            if calls["n"] == 4:  # first field ("name") of row 2 (Bob)
                raise OperationalError("simulated connection loss")
            return real_convert_value(raw, data_type)

        with patch("imports.services._convert_value", side_effect=flaky_convert):
            with self.assertRaises(OperationalError):
                run_import(str(job.id))

        job.refresh_from_db()
        self.assertEqual(job.status, ImportJob.Status.RUNNING)  # not marked FAILED by run_import itself
        self.assertEqual(job.imported_rows, 1)  # row 1 (Alice) committed before the failure
        # row 2 (Bob) was in flight, not committed — must not be skipped on retry
        self.assertEqual(job.last_processed_row, 1)

        # Simulates the retry a real Celery worker would perform.
        run_import(str(job.id))
        job.refresh_from_db()
        self.assertEqual(job.status, ImportJob.Status.COMPLETED)
        self.assertEqual(job.imported_rows, 2)  # Alice + Bob (Bob was retried, not dropped)
        self.assertEqual(job.rejected_rows, 1)  # Carol's bad age, unaffected by the retry

        with connections["tenant"].cursor() as cursor:
            cursor.execute(f'SELECT name FROM "{self.schema_name}"."people" ORDER BY name')
            names = [row[0] for row in cursor.fetchall()]
        self.assertEqual(names, ["Alice", "Bob"])

    def test_member_without_dataset_import_permission_is_forbidden(self):
        member = User.objects.create_user(email="plain-import@example.com", password="x")
        Membership.objects.create(
            user=member, organization_id=self.org_id, status=Membership.Status.ACTIVE
        )
        self.client.force_login(member)

        response = self.client.post(
            reverse("import-job-list-create", args=[self.table_id]),
            {
                "file_id": self.file_id,
                "encoding": "utf-8",
                "delimiter": ",",
                "column_mapping": self.column_mapping,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class ImportAuditTests(ImportTestBase):
    """
    A bulk insert writes rows straight into a tenant table, so it has to leave
    an audit trail — previously the whole app emitted no audit events at all.
    """

    def _start_import(self):
        return self.client.post(
            reverse("import-job-list-create", args=[self.table_id]),
            {
                "file_id": self.file_id,
                "encoding": "utf-8",
                "delimiter": ",",
                "column_mapping": self.column_mapping,
            },
            format="json",
        )

    def test_a_completed_import_records_start_and_finish_with_row_counts(self):
        response = self._start_import()
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        job_id = response.data["id"]

        start = AuditEvent.objects.get(action="dataset.import.start", resource_id=str(job_id))
        self.assertEqual(start.result, AuditEvent.Result.SUCCESS)
        self.assertEqual(str(start.organization_id), str(self.org_id))
        self.assertEqual(start.context["table"], "people")

        finish = AuditEvent.objects.get(action="dataset.import.finish", resource_id=str(job_id))
        self.assertEqual(finish.result, AuditEvent.Result.SUCCESS)
        self.assertEqual(finish.context["imported_rows"], 2)
        self.assertEqual(finish.context["rejected_rows"], 1)

    def test_a_denied_import_is_audited_as_denied(self):
        member = User.objects.create_user(email="denied-import@example.com", password="x")
        Membership.objects.create(
            user=member, organization_id=self.org_id, status=Membership.Status.ACTIVE
        )
        self.client.force_login(member)

        response = self._start_import()
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        event = AuditEvent.objects.get(action="dataset.import.start", result=AuditEvent.Result.DENIED)
        self.assertEqual(event.actor_id, member.id)
        self.assertEqual(event.resource_id, str(self.table_id))


class ImportReadVisibilityTests(ImportTestBase):
    """An active organization member with no role/grant covering
    `database.read` must not be able to list/view import jobs or their
    per-row errors — matching the same class of gap already closed for
    databases/analytics/storage/environments/exports/applications
    (THREAT_MODEL.md Section 4a). ImportJobListCreateView.get/
    ImportJobDetailView.get/ImportJobErrorListView.get previously checked
    only organization membership via get_member_table/
    get_member_import_job, exposing job status and — via
    ImportJobErrorSerializer's `raw_row` field — the literal rejected CSV
    row content (real tenant data, not just metadata) to any member
    regardless of role or Sharing settings."""

    def setUp(self):
        super().setUp()
        created = self.client.post(
            reverse("import-job-list-create", args=[self.table_id]),
            {
                "file_id": self.file_id,
                "encoding": "utf-8",
                "delimiter": ",",
                "column_mapping": self.column_mapping,
            },
            format="json",
        )
        self.job_id = created.data["id"]

        self.outsider = User.objects.create_user(email="import-outsider@example.com", password="x")
        Membership.objects.create(
            user=self.outsider, organization_id=self.org_id, status=Membership.Status.ACTIVE
        )
        self.client.force_login(self.outsider)

    def test_member_without_database_read_cannot_list_import_jobs(self):
        resp = self.client.get(reverse("import-job-list-create", args=[self.table_id]))
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_member_without_database_read_cannot_view_job_detail(self):
        resp = self.client.get(reverse("import-job-detail", args=[self.job_id]))
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_member_without_database_read_cannot_view_job_errors(self):
        """The most sensitive of the three: raw_row exposes actual
        rejected data values, not just status metadata."""
        resp = self.client.get(reverse("import-job-error-list", args=[self.job_id]))
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_database_read_permission_restores_access(self):
        from organizations.models import Organization
        from permissions.services import assign_role

        assign_role(
            user=self.outsider,
            role_slug="viewer",
            organization=Organization.objects.get(id=self.org_id),
        )

        listed = self.client.get(reverse("import-job-list-create", args=[self.table_id]))
        self.assertEqual(listed.status_code, status.HTTP_200_OK)

        detail = self.client.get(reverse("import-job-detail", args=[self.job_id]))
        self.assertEqual(detail.status_code, status.HTTP_200_OK)

        errors = self.client.get(reverse("import-job-error-list", args=[self.job_id]))
        self.assertEqual(errors.status_code, status.HTTP_200_OK)


class ImportEnvironmentScopeTests(APITestCase):
    """The Phase 22 invariant ('an ApplicationCredential scoped to one
    Environment can never reach a resource bound to a different one') was
    enforced in databases'/storage's row/file views but never wired into
    the imports app at all — a Development-scoped credential could import
    a CSV from a Production-bound bucket into a Production-bound table
    (or vice versa) with a real database.read/write + storage.read
    ResourceGrant on both sides, since nothing in imports/views.py ever
    called check_environment_scope. Mirrors environments/tests/
    test_environments.py's EnvironmentCredentialAndIsolationTests setup."""

    databases = {"default", "tenant"}

    def setUp(self):
        SeedPermissionsCommand().handle()
        self.admin = User.objects.create_user(email="import-env-admin@example.com", password="x")
        self.client.force_login(self.admin)

        org = self.client.post(reverse("organization-list-create"), {"name": "Acme"})
        self.org_id = org.data["id"]
        ws = self.client.post(reverse("workspace-list-create", args=[self.org_id]), {"name": "WS"})
        proj = self.client.post(reverse("project-list-create", args=[ws.data["id"]]), {"name": "Proj"})
        self.project_id = proj.data["id"]

        app = self.client.post(reverse("application-list-create", args=[self.org_id]), {"name": "etl-bot"})
        self.application_id = app.data["id"]

        dev_env = self.client.post(
            reverse("environment-list-create", args=[self.application_id]),
            {"name": "Development", "environment_type": "development"},
            format="json",
        ).data
        prod_env = self.client.post(
            reverse("environment-list-create", args=[self.application_id]),
            {"name": "Production", "environment_type": "production"},
            format="json",
        ).data

        self.dev_db_id = self._create_tenant_database("dev-db")
        self.prod_db_id = self._create_tenant_database("prod-db")
        self.client.patch(
            reverse("environment-database-binding", args=[dev_env["id"]]),
            {"tenant_database_id": self.dev_db_id},
            format="json",
        )
        self.client.patch(
            reverse("environment-database-binding", args=[prod_env["id"]]),
            {"tenant_database_id": self.prod_db_id},
            format="json",
        )

        self.dev_bucket_id = self._create_bucket("dev-files")
        self.prod_bucket_id = self._create_bucket("prod-files")
        self.client.patch(
            reverse("environment-storage-binding", args=[dev_env["id"]]),
            {"bucket_id": self.dev_bucket_id},
            format="json",
        )
        self.client.patch(
            reverse("environment-storage-binding", args=[prod_env["id"]]),
            {"bucket_id": self.prod_bucket_id},
            format="json",
        )

        dev_cred = self.client.post(
            reverse("environment-credential-list-create", args=[dev_env["id"]])
        )
        self.dev_token = dev_cred.data["secret"]

        table = self.client.post(reverse("table-list-create", args=[self.prod_db_id]), {"name": "people"})
        self.prod_table_id = table.data["id"]
        self.client.post(
            reverse("column-create", args=[self.prod_table_id]),
            {"name": "name", "data_type": "text"},
            format="json",
        )

        upload = self.client.post(
            reverse("file-list-create", args=[self.prod_bucket_id]),
            {"file": SimpleUploadedFile("people.csv", b"name\nAlice\n", content_type="text/csv")},
            format="multipart",
        )
        self.prod_file_id = upload.data["id"]

        # A real, broad ResourceGrant on the *Production* database/bucket
        # for the Development credential's identity — proves the
        # environment-scope check itself is what blocks access below, not
        # merely an absent grant a misconfiguration could just as easily
        # supply by mistake (same discipline as environments' own
        # isolation test).
        from applications.models import Application
        from permissions.services import grant_resource_permission

        identity_user = Application.objects.get(id=self.application_id).service_account.identity_user
        for perm in ("database.read", "database.write"):
            grant_resource_permission(
                user=identity_user,
                permission_code=perm,
                organization_id=self.org_id,
                resource_type="databases.tenant_database",
                resource_id=self.prod_db_id,
                granted_by=self.admin,
            )
        grant_resource_permission(
            user=identity_user,
            permission_code="storage.read",
            organization_id=self.org_id,
            resource_type="storage.bucket",
            resource_id=self.prod_bucket_id,
            granted_by=self.admin,
        )
        self.client.logout()

    def _create_tenant_database(self, name):
        resp = self.client.post(
            reverse("tenant-database-list-create", args=[self.project_id]), {"name": name}
        )
        return resp.data["id"]

    def _create_bucket(self, name):
        resp = self.client.post(reverse("bucket-list-create", args=[self.project_id]), {"name": name})
        return resp.data["id"]

    def _auth_headers(self, token):
        return {"HTTP_AUTHORIZATION": f"Bearer {token}"}

    def test_development_credential_cannot_preview_a_production_bucket_file(self):
        resp = self.client.get(
            reverse("import-preview", args=[self.prod_file_id]), **self._auth_headers(self.dev_token)
        )
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_development_credential_cannot_list_import_jobs_on_a_production_table(self):
        resp = self.client.get(
            reverse("import-job-list-create", args=[self.prod_table_id]), **self._auth_headers(self.dev_token)
        )
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_development_credential_cannot_import_into_a_production_table(self):
        """The write path: despite holding real database.write on the
        production TenantDatabase and storage.read on the production
        Bucket (see setUp), the environment-scope check must still block
        this — otherwise a Development integration could bulk-write into
        Production data through the CSV import path alone."""
        mapping = [{"csv_column": "name", "target_column": "name", "target_type": "text"}]
        resp = self.client.post(
            reverse("import-job-list-create", args=[self.prod_table_id]),
            {"file_id": self.prod_file_id, "encoding": "utf-8", "delimiter": ",", "column_mapping": mapping},
            format="json",
            **self._auth_headers(self.dev_token),
        )
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(ImportJob.objects.filter(table_id=self.prod_table_id).count(), 0)
