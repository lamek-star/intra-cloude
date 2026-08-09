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
