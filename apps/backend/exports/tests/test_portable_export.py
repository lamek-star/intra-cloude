"""
The mandatory portable-export round-trip scenario (Section 46 of the
master prompt): create a fully-populated organization, export it, import
the package as a fresh installation would, and verify everything came
back — organization, files (byte-for-byte), database schema,
relationships, records, and permissions/membership, with checksums
verified along the way. "Fresh installation" is simulated by importing
into a brand-new Organization within the same test database — which is
exactly what exports.restorer always does, by design (see
restorer.py's module docstring).
"""

import io
import zipfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import User
from databases.models import DBTable, TenantDatabase
from organizations.models import Membership
from permissions.management.commands.seed_permissions import Command as SeedPermissionsCommand
from storage.models import Bucket, FileObject

FILE_CONTENT = b"quarterly report contents, not that it matters\n" * 50


class PortableExportRoundTripTests(APITestCase):
    databases = {"default", "tenant"}

    def setUp(self):
        SeedPermissionsCommand().handle()
        self.admin = User.objects.create_user(email="export-admin@example.com", password="x")
        self.viewer = User.objects.create_user(email="export-viewer@example.com", password="x")
        self.client.force_login(self.admin)

    def _build_source_organization(self):
        org = self.client.post(reverse("organization-list-create"), {"name": "SourceOrg"})
        org_id = org.data["id"]

        self.client.post(
            reverse("membership-list-create", args=[org_id]), {"email": self.viewer.email}
        )
        memberships = self.client.get(reverse("membership-list-create", args=[org_id])).data
        viewer_membership_id = next(
            m["id"] for m in memberships if m["user"]["id"] == str(self.viewer.id)
        )
        self.client.post(
            reverse("membership-role-assign", args=[org_id, viewer_membership_id]),
            {"role_slug": "viewer"},
        )

        ws = self.client.post(reverse("workspace-list-create", args=[org_id]), {"name": "WS"})
        proj = self.client.post(reverse("project-list-create", args=[ws.data["id"]]), {"name": "Proj"})
        project_id = proj.data["id"]

        # --- Storage: a real uploaded file, in a folder ---
        bucket = self.client.post(reverse("bucket-list-create", args=[project_id]), {"name": "docs"})
        bucket_id = bucket.data["id"]
        folder = self.client.post(reverse("folder-list-create", args=[bucket_id]), {"name": "reports"})
        upload = self.client.post(
            reverse("file-list-create", args=[bucket_id]),
            {
                "file": SimpleUploadedFile("q1.txt", FILE_CONTENT, content_type="text/plain"),
                "display_filename": "q1.txt",
                "folder": folder.data["id"],
            },
            format="multipart",
        )
        self.assertEqual(upload.status_code, status.HTTP_201_CREATED)

        # --- Database: two tables with a foreign key and real rows ---
        db = self.client.post(
            reverse("tenant-database-list-create", args=[project_id]), {"name": "AppDB"}
        )
        db_id = db.data["id"]

        customers = self.client.post(reverse("table-list-create", args=[db_id]), {"name": "customers"})
        customers_id = customers.data["id"]
        self.client.post(
            reverse("column-create", args=[customers_id]),
            {"name": "name", "data_type": "text"},
            format="json",
        )

        orders = self.client.post(reverse("table-list-create", args=[db_id]), {"name": "orders"})
        orders_id = orders.data["id"]
        customer_ref_col = self.client.post(
            reverse("column-create", args=[orders_id]),
            {"name": "customer_id", "data_type": "uuid"},
            format="json",
        )
        self.client.post(
            reverse("column-create", args=[orders_id]),
            {"name": "total", "data_type": "decimal", "precision": 10, "scale": 2},
            format="json",
        )

        # customers.id is the auto PK — fetch its column id to reference it.
        customers_columns = self.client.get(reverse("table-detail", args=[customers_id])).data["columns"]
        customers_pk_id = next(c["id"] for c in customers_columns if c["name"] == "id")

        fk = self.client.post(
            reverse("foreign-key-create", args=[orders_id]),
            {
                "column_id": customer_ref_col.data["id"],
                "references_table_id": customers_id,
                "references_column_id": customers_pk_id,
                "on_delete": "cascade",
            },
            format="json",
        )
        self.assertEqual(fk.status_code, status.HTTP_201_CREATED)

        customer_row = self.client.post(
            reverse("row-list-create", args=[customers_id]), {"name": "Acme Corp"}, format="json"
        )
        self.assertEqual(customer_row.status_code, status.HTTP_201_CREATED)
        order_row = self.client.post(
            reverse("row-list-create", args=[orders_id]),
            {"customer_id": customer_row.data["id"], "total": "199.99"},
            format="json",
        )
        self.assertEqual(order_row.status_code, status.HTTP_201_CREATED)

        return {
            "org_id": org_id,
            "file_checksum": upload.data["checksum_sha256"],
            "customer_name": "Acme Corp",
            "customer_id": customer_row.data["id"],
            "order_total": "199.99",
        }

    def test_full_round_trip(self):
        source = self._build_source_organization()

        # --- Export ---
        export = self.client.post(reverse("export-job-list-create", args=[source["org_id"]]), {})
        self.assertEqual(export.status_code, status.HTTP_201_CREATED)
        export_job_id = export.data["id"]

        detail = self.client.get(reverse("export-job-detail", args=[export_job_id]))
        self.assertEqual(detail.data["status"], "completed")
        self.assertTrue(detail.data["checksum_sha256"])

        download = self.client.get(reverse("export-job-download", args=[export_job_id]))
        self.assertEqual(download.status_code, status.HTTP_200_OK)
        package_bytes = b"".join(download.streaming_content)
        self.assertTrue(len(package_bytes) > 0)

        # --- "Fresh installation": import the package ---
        restore = self.client.post(
            reverse("restore-job-list-create"),
            {"package": SimpleUploadedFile("export.icp", package_bytes)},
            format="multipart",
        )
        self.assertEqual(restore.status_code, status.HTTP_201_CREATED)
        restore_job_id = restore.data["id"]

        restore_detail = self.client.get(reverse("restore-job-detail", args=[restore_job_id]))
        self.assertEqual(
            restore_detail.data["status"], "completed", restore_detail.data.get("error_message")
        )
        report = restore_detail.data["report"]
        new_org_id = report["organization_id"]
        self.assertNotEqual(new_org_id, source["org_id"])  # a genuinely new organization

        # --- Organization structure restored ---
        self.assertEqual(report["workspaces"], 1)
        self.assertEqual(report["projects"], 1)
        self.assertEqual(report["tenant_databases"], 1)
        self.assertEqual(report["tables"], 2)
        self.assertEqual(report["rows_imported"], 2)
        self.assertEqual(report["buckets"], 1)
        self.assertEqual(report["files_restored"], 1)
        self.assertEqual(report["files_quarantined"], 0)
        # The viewer's membership: same test DB, so their user account
        # exists on "this installation" and should restore successfully.
        self.assertEqual(report["memberships_restored"], 2)  # admin (creator) + viewer
        self.assertEqual(report["memberships_skipped"], [])

        new_membership = Membership.objects.get(user=self.viewer, organization_id=new_org_id)
        self.assertEqual(new_membership.status, Membership.Status.ACTIVE)

        # --- File restored byte-for-byte ---
        new_bucket = Bucket.objects.get(project__workspace__organization_id=new_org_id, name="docs")
        new_file = FileObject.objects.get(bucket=new_bucket, display_filename="q1.txt")
        self.assertEqual(new_file.checksum_sha256, source["file_checksum"])
        self.assertEqual(new_file.folder.name, "reports")

        self.client.force_login(self.admin)
        download_url = reverse("file-download", args=[new_file.id])
        file_resp = self.client.get(download_url)
        self.assertEqual(file_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(b"".join(file_resp.streaming_content), FILE_CONTENT)

        # --- Database schema, relationship, and row data restored ---
        new_tenant_db = TenantDatabase.objects.get(
            project__workspace__organization_id=new_org_id, name="AppDB"
        )
        new_customers = DBTable.objects.get(tenant_database=new_tenant_db, name="customers")
        new_orders = DBTable.objects.get(tenant_database=new_tenant_db, name="orders")
        fk = new_orders.columns.get(name="customer_id").foreign_key
        self.assertEqual(fk.references_table_id, new_customers.id)
        self.assertEqual(fk.on_delete, "cascade")

        customer_rows = self.client.get(reverse("row-list-create", args=[new_customers.id])).data
        self.assertEqual(customer_rows["count"], 1)
        self.assertEqual(customer_rows["results"][0]["name"], source["customer_name"])
        # The restored order's customer_id must point at the restored
        # customer's *new* row id — the export preserved the original
        # UUIDs across both tables, so FK integrity survives the round
        # trip without any id remapping.
        restored_customer_id = customer_rows["results"][0]["id"]
        order_rows = self.client.get(reverse("row-list-create", args=[new_orders.id])).data
        self.assertEqual(order_rows["count"], 1)
        self.assertEqual(str(order_rows["results"][0]["customer_id"]), str(restored_customer_id))
        self.assertEqual(str(order_rows["results"][0]["total"]), source["order_total"])

    def test_encrypted_export_round_trip_and_wrong_passphrase_is_rejected(self):
        # Exercises the encryption/decryption logic directly
        # (container.py + restorer.open_package) rather than through the
        # API's async job endpoint for the *failure* case: Celery's
        # eager test-mode retry() raises synchronously back through
        # .delay() on any failure (a known eager-mode-only quirk, not a
        # production behavior — see imports/tasks.py's equivalent note
        # from the Phase 12 hardening pass), which would crash the POST
        # request itself rather than leave a queryable FAILED job. The
        # successful path further below still goes through the real API.
        source = self._build_source_organization()

        export = self.client.post(
            reverse("export-job-list-create", args=[source["org_id"]]),
            {"passphrase": "correct horse battery staple"},
        )
        export_job_id = export.data["id"]
        self.assertTrue(self.client.get(reverse("export-job-detail", args=[export_job_id])).data["encrypted"])

        package_bytes = b"".join(
            self.client.get(reverse("export-job-download", args=[export_job_id])).streaming_content
        )

        from exports import restorer
        from exports.container import DecryptionFailed

        with self.assertRaises(DecryptionFailed):
            restorer.open_package(package_bytes, passphrase="wrong password entirely")
        with self.assertRaises(DecryptionFailed):
            restorer.open_package(package_bytes, passphrase=None)  # encrypted, none supplied

        right = self.client.post(
            reverse("restore-job-list-create"),
            {
                "package": SimpleUploadedFile("export.icp", package_bytes),
                "passphrase": "correct horse battery staple",
            },
            format="multipart",
        )
        right_detail = self.client.get(reverse("restore-job-detail", args=[right.data["id"]]))
        self.assertEqual(right_detail.data["status"], "completed", right_detail.data.get("error_message"))

    def test_member_without_export_permission_is_forbidden(self):
        source = self._build_source_organization()
        self.client.force_login(self.viewer)
        resp = self.client.post(reverse("export-job-list-create", args=[source["org_id"]]), {})
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_tampered_package_is_rejected(self):
        # Same rationale as the wrong-passphrase test above for testing
        # restorer.py directly rather than through the async API.
        source = self._build_source_organization()
        export = self.client.post(reverse("export-job-list-create", args=[source["org_id"]]), {})
        package_bytes = bytearray(
            b"".join(
                self.client.get(
                    reverse("export-job-download", args=[export.data["id"]])
                ).streaming_content
            )
        )

        # Corrupt one byte inside manifest.json's own *compressed data*
        # specifically, computed from the ZIP's real local-file-header
        # layout for that member — not a blind "flip the middle byte of
        # the whole package", which can just as easily land on ZIP
        # structural metadata (a length/offset field) instead of
        # checksummed file data, producing a flaky pass/fail depending
        # on package size (confirmed by actually running this test
        # repeatedly: ~1 in 5 runs missed the corruption entirely).
        header_len = int.from_bytes(bytes(package_bytes[8:12]), "big")
        zip_start = 12 + header_len
        zf = zipfile.ZipFile(io.BytesIO(bytes(package_bytes[zip_start:])))
        info = zf.getinfo("manifest.json")
        local_header_size = 30 + len(info.filename.encode()) + len(info.extra)
        data_offset = zip_start + info.header_offset + local_header_size
        package_bytes[data_offset] ^= 0xFF

        from exports import restorer

        with self.assertRaises(restorer.PackageValidationError):
            zf2, manifest = restorer.open_package(bytes(package_bytes), passphrase=None)
            restorer.verify_checksums(zf2, manifest)
