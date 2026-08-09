"""
Cross-organization IDOR/BOLA regression tests
(docs/security/THREAT_MODEL.md Section 4). Every resource type gains a
case here as it's introduced — this file starts with the resources Phase 2
introduces (Organization, Membership, RoleAssignment) and is extended, not
replaced, by later phases.

Run from the repo root: `pytest` (see pytest.ini — this directory isn't
under apps/backend, so it needs the root config's `pythonpath`).
"""

from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connections
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import User
from organizations.models import Membership
from permissions.management.commands.seed_permissions import Command as SeedPermissionsCommand


class CrossOrganizationIsolationTests(APITestCase):
    def setUp(self):
        SeedPermissionsCommand().handle()

        self.org_a_admin = User.objects.create_user(email="a-admin@example.com", password="x")
        self.client.force_login(self.org_a_admin)
        resp = self.client.post(reverse("organization-list-create"), {"name": "Org A"})
        self.org_a_id = resp.data["id"]

        self.org_b_admin = User.objects.create_user(email="b-admin@example.com", password="x")
        self.client.force_login(self.org_b_admin)
        resp = self.client.post(reverse("organization-list-create"), {"name": "Org B"})
        self.org_b_id = resp.data["id"]
        self.org_b_membership_id = Membership.objects.get(
            user=self.org_b_admin, organization_id=self.org_b_id
        ).id

        # Act as Org A's admin for the rest of each test — the actor with
        # no legitimate access to Org B.
        self.client.force_login(self.org_a_admin)

    def test_cannot_read_another_orgs_detail_by_guessing_its_id(self):
        response = self.client.get(reverse("organization-detail", args=[self.org_b_id]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_cannot_list_another_orgs_members(self):
        response = self.client.get(reverse("membership-list-create", args=[self.org_b_id]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_cannot_add_a_member_to_another_org(self):
        User.objects.create_user(email="intruder-target@example.com", password="x")
        response = self.client.post(
            reverse("membership-list-create", args=[self.org_b_id]),
            {"email": "intruder-target@example.com"},
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertFalse(
            Membership.objects.filter(
                organization_id=self.org_b_id, user__email="intruder-target@example.com"
            ).exists()
        )

    def test_cannot_assign_a_role_within_another_org(self):
        response = self.client.post(
            reverse("membership-role-assign", args=[self.org_b_id, self.org_b_membership_id]),
            {"role_slug": "database-administrator"},
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_own_orgs_admin_role_grants_nothing_in_the_other_org(self):
        """Being Organization Administrator of Org A must not translate
        into any permission — role-based or otherwise — inside Org B."""
        from permissions.services import has_permission

        for code in ("users.manage", "permissions.manage", "database.create", "storage.manage"):
            self.assertFalse(
                has_permission(self.org_a_admin, code, organization_id=self.org_b_id),
                f"Org A admin must not hold {code!r} in Org B",
            )


class CrossOrganizationStorageIsolationTests(APITestCase):
    """Extends the suite above to the storage resources introduced in
    Phase 3: Workspace -> Project -> Bucket -> FileObject."""

    def setUp(self):
        SeedPermissionsCommand().handle()

        self.org_a_admin = User.objects.create_user(email="storage-a-admin@example.com", password="x")
        self.client.force_login(self.org_a_admin)
        org_a = self.client.post(reverse("organization-list-create"), {"name": "Storage Org A"})
        ws_a = self.client.post(
            reverse("workspace-list-create", args=[org_a.data["id"]]), {"name": "WS"}
        )
        proj_a = self.client.post(
            reverse("project-list-create", args=[ws_a.data["id"]]), {"name": "Proj"}
        )
        bucket_a = self.client.post(
            reverse("bucket-list-create", args=[proj_a.data["id"]]), {"name": "bucket"}
        )
        self.bucket_a_id = bucket_a.data["id"]
        upload = self.client.post(
            reverse("file-list-create", args=[self.bucket_a_id]),
            {"file": SimpleUploadedFile("secret.txt", b"org a secret", content_type="text/plain")},
            format="multipart",
        )
        self.file_a_id = upload.data["id"]

        self.org_b_admin = User.objects.create_user(email="storage-b-admin@example.com", password="x")
        self.client.force_login(self.org_b_admin)
        self.client.post(reverse("organization-list-create"), {"name": "Storage Org B"})

        # Act as Org B's admin — no legitimate access to anything under Org A.
        self.client.force_login(self.org_b_admin)

    def test_cannot_list_another_orgs_bucket_files(self):
        response = self.client.get(reverse("file-list-create", args=[self.bucket_a_id]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_cannot_read_another_orgs_file_metadata(self):
        response = self.client.get(reverse("file-detail", args=[self.file_a_id]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_cannot_download_another_orgs_file(self):
        response = self.client.get(reverse("file-download", args=[self.file_a_id]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_cannot_delete_another_orgs_file(self):
        response = self.client.delete(reverse("file-detail", args=[self.file_a_id]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_cannot_upload_into_another_orgs_bucket(self):
        response = self.client.post(
            reverse("file-list-create", args=[self.bucket_a_id]),
            {"file": SimpleUploadedFile("intrusion.txt", b"x", content_type="text/plain")},
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class CrossOrganizationDatabaseIsolationTests(APITestCase):
    """Extends the suite to the database-builder resources introduced in
    Phase 4: TenantDatabase -> DBTable -> DBColumn."""

    databases = {"default", "tenant"}

    def setUp(self):
        SeedPermissionsCommand().handle()

        self.org_a_admin = User.objects.create_user(email="db-a-admin@example.com", password="x")
        self.client.force_login(self.org_a_admin)
        org_a = self.client.post(reverse("organization-list-create"), {"name": "DB Org A"})
        ws_a = self.client.post(reverse("workspace-list-create", args=[org_a.data["id"]]), {"name": "WS"})
        proj_a = self.client.post(reverse("project-list-create", args=[ws_a.data["id"]]), {"name": "Proj"})
        db_a = self.client.post(
            reverse("tenant-database-list-create", args=[proj_a.data["id"]]), {"name": "AppDB"}
        )
        self.tenant_database_a_id = db_a.data["id"]
        table_a = self.client.post(
            reverse("table-list-create", args=[self.tenant_database_a_id]), {"name": "customers"}
        )
        self.table_a_id = table_a.data["id"]

        self.org_b_admin = User.objects.create_user(email="db-b-admin@example.com", password="x")
        self.client.force_login(self.org_b_admin)
        self.client.post(reverse("organization-list-create"), {"name": "DB Org B"})

        # Act as Org B's admin — no legitimate access to anything under Org A.
        self.client.force_login(self.org_b_admin)

    def test_cannot_read_another_orgs_tenant_database(self):
        response = self.client.get(reverse("tenant-database-detail", args=[self.tenant_database_a_id]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_cannot_list_tables_in_another_orgs_database(self):
        response = self.client.get(reverse("table-list-create", args=[self.tenant_database_a_id]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_cannot_create_table_in_another_orgs_database(self):
        response = self.client.post(
            reverse("table-list-create", args=[self.tenant_database_a_id]), {"name": "intrusion"}
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_cannot_read_another_orgs_table(self):
        response = self.client.get(reverse("table-detail", args=[self.table_a_id]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_cannot_add_column_to_another_orgs_table(self):
        response = self.client.post(
            reverse("column-create", args=[self.table_a_id]),
            {"name": "intrusion", "data_type": "text"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_cannot_delete_another_orgs_database(self):
        response = self.client.delete(reverse("tenant-database-detail", args=[self.tenant_database_a_id]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class CrossOrganizationImportIsolationTests(APITestCase):
    """Extends the suite to the CSV-import resources introduced in
    Phase 5: ImportJob."""

    databases = {"default", "tenant"}

    def setUp(self):
        SeedPermissionsCommand().handle()

        self.org_a_admin = User.objects.create_user(email="import-a-admin@example.com", password="x")
        self.client.force_login(self.org_a_admin)
        org_a = self.client.post(reverse("organization-list-create"), {"name": "Import Org A"})
        ws_a = self.client.post(reverse("workspace-list-create", args=[org_a.data["id"]]), {"name": "WS"})
        proj_a = self.client.post(reverse("project-list-create", args=[ws_a.data["id"]]), {"name": "Proj"})
        bucket_a = self.client.post(
            reverse("bucket-list-create", args=[proj_a.data["id"]]), {"name": "uploads"}
        )
        db_a = self.client.post(
            reverse("tenant-database-list-create", args=[proj_a.data["id"]]), {"name": "AppDB"}
        )
        table_a = self.client.post(
            reverse("table-list-create", args=[db_a.data["id"]]), {"name": "people"}
        )
        self.table_a_id = table_a.data["id"]
        self.client.post(
            reverse("column-create", args=[self.table_a_id]),
            {"name": "name", "data_type": "text"},
            format="json",
        )
        upload = self.client.post(
            reverse("file-list-create", args=[bucket_a.data["id"]]),
            {"file": SimpleUploadedFile("people.csv", b"name\nalice\n", content_type="text/csv")},
            format="multipart",
        )
        self.file_a_id = upload.data["id"]
        job = self.client.post(
            reverse("import-job-list-create", args=[self.table_a_id]),
            {
                "file_id": self.file_a_id,
                "encoding": "utf-8",
                "delimiter": ",",
                "column_mapping": [{"csv_column": "name", "target_column": "name", "target_type": "text"}],
            },
            format="json",
        )
        self.job_a_id = job.data["id"]

        self.org_b_admin = User.objects.create_user(email="import-b-admin@example.com", password="x")
        self.client.force_login(self.org_b_admin)
        self.client.post(reverse("organization-list-create"), {"name": "Import Org B"})

        # Act as Org B's admin — no legitimate access to anything under Org A.
        self.client.force_login(self.org_b_admin)

    def test_cannot_preview_another_orgs_file(self):
        response = self.client.get(reverse("import-preview", args=[self.file_a_id]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_cannot_list_another_orgs_import_jobs(self):
        response = self.client.get(reverse("import-job-list-create", args=[self.table_a_id]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_cannot_read_another_orgs_import_job(self):
        response = self.client.get(reverse("import-job-detail", args=[self.job_a_id]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_cannot_read_another_orgs_import_errors(self):
        response = self.client.get(reverse("import-job-error-list", args=[self.job_a_id]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_cannot_start_an_import_against_another_orgs_table(self):
        response = self.client.post(
            reverse("import-job-list-create", args=[self.table_a_id]),
            {
                "file_id": self.file_a_id,
                "encoding": "utf-8",
                "delimiter": ",",
                "column_mapping": [{"csv_column": "name", "target_column": "name", "target_type": "text"}],
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class CrossOrganizationRowIsolationTests(APITestCase):
    """Extends the suite to the data-explorer row resources introduced in
    Phase 6."""

    databases = {"default", "tenant"}

    def setUp(self):
        SeedPermissionsCommand().handle()

        self.org_a_admin = User.objects.create_user(email="rows-a-admin@example.com", password="x")
        self.client.force_login(self.org_a_admin)
        org_a = self.client.post(reverse("organization-list-create"), {"name": "Rows Org A"})
        ws_a = self.client.post(reverse("workspace-list-create", args=[org_a.data["id"]]), {"name": "WS"})
        proj_a = self.client.post(reverse("project-list-create", args=[ws_a.data["id"]]), {"name": "Proj"})
        db_a = self.client.post(
            reverse("tenant-database-list-create", args=[proj_a.data["id"]]), {"name": "AppDB"}
        )
        table_a = self.client.post(
            reverse("table-list-create", args=[db_a.data["id"]]), {"name": "secrets"}
        )
        self.table_a_id = table_a.data["id"]
        self.client.post(
            reverse("column-create", args=[self.table_a_id]),
            {"name": "value", "data_type": "text"},
            format="json",
        )
        row_a = self.client.post(
            reverse("row-list-create", args=[self.table_a_id]), {"value": "org a secret"}, format="json"
        )
        self.row_a_id = row_a.data["id"]

        self.org_b_admin = User.objects.create_user(email="rows-b-admin@example.com", password="x")
        self.client.force_login(self.org_b_admin)
        self.client.post(reverse("organization-list-create"), {"name": "Rows Org B"})

        # Act as Org B's admin — no legitimate access to anything under Org A.
        self.client.force_login(self.org_b_admin)

    def test_cannot_list_another_orgs_rows(self):
        response = self.client.get(reverse("row-list-create", args=[self.table_a_id]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_cannot_read_another_orgs_row(self):
        response = self.client.get(reverse("row-detail", args=[self.table_a_id, self.row_a_id]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_cannot_insert_into_another_orgs_table(self):
        response = self.client.post(
            reverse("row-list-create", args=[self.table_a_id]), {"value": "intrusion"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_cannot_update_another_orgs_row(self):
        response = self.client.patch(
            reverse("row-detail", args=[self.table_a_id, self.row_a_id]),
            {"value": "overwritten"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_cannot_delete_another_orgs_row(self):
        response = self.client.delete(reverse("row-detail", args=[self.table_a_id, self.row_a_id]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_cannot_export_another_orgs_table(self):
        response = self.client.get(reverse("row-export", args=[self.table_a_id]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class CrossOrganizationApplicationIsolationTests(APITestCase):
    """Extends the suite to the application/service-account resources
    introduced in Phase 7."""

    databases = {"default", "tenant"}

    def setUp(self):
        SeedPermissionsCommand().handle()

        self.org_a_admin = User.objects.create_user(email="apps-a-admin@example.com", password="x")
        self.client.force_login(self.org_a_admin)
        org_a = self.client.post(reverse("organization-list-create"), {"name": "Apps Org A"})
        app_a = self.client.post(
            reverse("application-list-create", args=[org_a.data["id"]]), {"name": "Bot A"}
        )
        self.application_a_id = app_a.data["id"]
        credential_a = self.client.post(
            reverse("application-credential-list-create", args=[self.application_a_id])
        )
        self.credential_a_id = credential_a.data["id"]

        self.org_b_admin = User.objects.create_user(email="apps-b-admin@example.com", password="x")
        self.client.force_login(self.org_b_admin)
        self.client.post(reverse("organization-list-create"), {"name": "Apps Org B"})

        # Act as Org B's admin — no legitimate access to anything under Org A.
        self.client.force_login(self.org_b_admin)

    def test_cannot_read_another_orgs_application(self):
        response = self.client.get(reverse("application-detail", args=[self.application_a_id]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_cannot_list_another_orgs_application_credentials(self):
        response = self.client.get(
            reverse("application-credential-list-create", args=[self.application_a_id])
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_cannot_issue_a_credential_for_another_orgs_application(self):
        response = self.client.post(
            reverse("application-credential-list-create", args=[self.application_a_id])
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_cannot_revoke_another_orgs_credential(self):
        response = self.client.post(
            reverse("application-credential-revoke", args=[self.application_a_id, self.credential_a_id])
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_cannot_grant_resource_access_to_another_orgs_application(self):
        response = self.client.post(
            reverse("application-resource-grant-list-create", args=[self.application_a_id]),
            {"permission_code": "storage.read", "resource_type": "storage.bucket", "resource_id": "x"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class CrossOrganizationConnectedDatabaseIsolationTests(APITestCase):
    """Extends the suite to the external-database-connector resources
    introduced in Phase 8: ConnectedDatabase."""

    databases = {"default", "tenant"}

    def setUp(self):
        SeedPermissionsCommand().handle()

        tenant_settings = connections["tenant"].settings_dict
        self.real_host = tenant_settings["HOST"] or "localhost"
        self.real_port = int(tenant_settings["PORT"] or 5432)
        self.real_database = tenant_settings["NAME"]
        self.real_user = tenant_settings["USER"]
        self.real_password = tenant_settings["PASSWORD"]

        self.org_a_admin = User.objects.create_user(email="conn-a-admin@example.com", password="x")
        self.client.force_login(self.org_a_admin)
        org_a = self.client.post(reverse("organization-list-create"), {"name": "Conn Org A"})
        ws_a = self.client.post(reverse("workspace-list-create", args=[org_a.data["id"]]), {"name": "WS"})
        proj_a = self.client.post(reverse("project-list-create", args=[ws_a.data["id"]]), {"name": "Proj"})
        self.project_a_id = proj_a.data["id"]
        connection_a = self.client.post(
            reverse("connected-database-list-create", args=[self.project_a_id]),
            {
                "name": "Warehouse",
                "engine": "postgresql",
                "host": self.real_host,
                "port": self.real_port,
                "database_name": self.real_database,
                "username": self.real_user,
                "password": self.real_password,
                "sslmode": "prefer",
            },
            format="json",
        )
        self.connected_database_a_id = connection_a.data["id"]

        self.org_b_admin = User.objects.create_user(email="conn-b-admin@example.com", password="x")
        self.client.force_login(self.org_b_admin)
        self.client.post(reverse("organization-list-create"), {"name": "Conn Org B"})

        # Act as Org B's admin — no legitimate access to anything under Org A.
        self.client.force_login(self.org_b_admin)

    def test_cannot_list_another_orgs_connected_databases(self):
        response = self.client.get(reverse("connected-database-list-create", args=[self.project_a_id]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_cannot_read_another_orgs_connected_database(self):
        response = self.client.get(reverse("connected-database-detail", args=[self.connected_database_a_id]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_cannot_test_another_orgs_connected_database(self):
        response = self.client.post(reverse("connected-database-test", args=[self.connected_database_a_id]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_cannot_read_another_orgs_connected_database_schema(self):
        response = self.client.get(reverse("connected-database-schema", args=[self.connected_database_a_id]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_cannot_read_another_orgs_connected_database_rows(self):
        response = self.client.get(
            reverse("connected-database-table-rows", args=[self.connected_database_a_id, "whatever"])
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_cannot_delete_another_orgs_connected_database(self):
        response = self.client.delete(
            reverse("connected-database-detail", args=[self.connected_database_a_id])
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class CrossOrganizationSharingIsolationTests(APITestCase):
    """Extends the suite to the sharing resources introduced in Phase 9:
    ShareGrant and Team."""

    databases = {"default", "tenant"}

    def setUp(self):
        SeedPermissionsCommand().handle()

        self.org_a_admin = User.objects.create_user(email="share-a-admin@example.com", password="x")
        self.client.force_login(self.org_a_admin)
        org_a = self.client.post(reverse("organization-list-create"), {"name": "Share Org A"})
        self.org_a_id = org_a.data["id"]
        ws_a = self.client.post(reverse("workspace-list-create", args=[self.org_a_id]), {"name": "WS"})
        proj_a = self.client.post(reverse("project-list-create", args=[ws_a.data["id"]]), {"name": "Proj"})
        bucket_a = self.client.post(
            reverse("bucket-list-create", args=[proj_a.data["id"]]), {"name": "docs"}
        )
        self.bucket_a_id = bucket_a.data["id"]

        self.org_a_member = User.objects.create_user(email="share-a-member@example.com", password="x")
        Membership.objects.create(
            user=self.org_a_member, organization_id=self.org_a_id, status=Membership.Status.ACTIVE
        )
        share_a = self.client.post(
            reverse("share-grant-list-create", args=[self.org_a_id]),
            {
                "resource_type": "storage.bucket",
                "resource_id": self.bucket_a_id,
                "principal_type": "user",
                "user_id": str(self.org_a_member.id),
                "level": "read",
            },
            format="json",
        )
        self.share_a_id = share_a.data["id"]

        team_a = self.client.post(reverse("team-list-create", args=[self.org_a_id]), {"name": "Eng"})
        self.team_a_id = team_a.data["id"]

        self.org_b_admin = User.objects.create_user(email="share-b-admin@example.com", password="x")
        self.client.force_login(self.org_b_admin)
        self.client.post(reverse("organization-list-create"), {"name": "Share Org B"})

        # Act as Org B's admin — no legitimate access to anything under Org A.
        self.client.force_login(self.org_b_admin)

    def test_cannot_list_another_orgs_shares(self):
        response = self.client.get(reverse("share-grant-list-create", args=[self.org_a_id]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_cannot_read_another_orgs_share(self):
        response = self.client.get(reverse("share-grant-detail", args=[self.share_a_id]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_cannot_revoke_another_orgs_share(self):
        response = self.client.delete(reverse("share-grant-detail", args=[self.share_a_id]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_cannot_create_a_share_for_another_orgs_bucket(self):
        response = self.client.post(
            reverse("share-grant-list-create", args=[self.org_a_id]),
            {
                "resource_type": "storage.bucket",
                "resource_id": self.bucket_a_id,
                "principal_type": "user",
                "user_id": str(self.org_a_member.id),
                "level": "read",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_cannot_add_a_member_to_another_orgs_team(self):
        response = self.client.post(
            reverse("team-member-list-create", args=[self.team_a_id]),
            {"user_id": str(self.org_a_member.id)},
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_cannot_toggle_another_orgs_external_sharing_setting(self):
        response = self.client.patch(
            reverse("external-sharing-setting", args=[self.org_a_id]), {"enabled": True}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
