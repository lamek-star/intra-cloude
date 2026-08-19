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
