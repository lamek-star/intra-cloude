"""
Phase 9: internal sharing. Verifies ShareGrant creation/revocation
actually changes what the target principal can do — not just that a row
exists — by driving the same storage/database-row endpoints a real
client would use, as the shared principal.
"""

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import User
from audit.models import AuditEvent
from organizations.models import Membership
from permissions.management.commands.seed_permissions import Command as SeedPermissionsCommand
from permissions.models import ResourceGrant


class SharingTestBase(APITestCase):
    databases = {"default", "tenant"}

    def setUp(self):
        SeedPermissionsCommand().handle()
        self.admin = User.objects.create_user(email="share-admin@example.com", password="x")
        self.client.force_login(self.admin)

        org = self.client.post(reverse("organization-list-create"), {"name": "Acme"})
        self.org_id = org.data["id"]
        ws = self.client.post(reverse("workspace-list-create", args=[self.org_id]), {"name": "WS"})
        proj = self.client.post(reverse("project-list-create", args=[ws.data["id"]]), {"name": "Proj"})
        self.project_id = proj.data["id"]
        bucket = self.client.post(
            reverse("bucket-list-create", args=[self.project_id]), {"name": "docs"}
        )
        self.bucket_id = bucket.data["id"]
        self.client.post(
            reverse("file-list-create", args=[self.bucket_id]),
            {"file": SimpleUploadedFile("a.txt", b"hello", content_type="text/plain")},
            format="multipart",
        )

        self.member = User.objects.create_user(email="share-member@example.com", password="x")
        Membership.objects.create(
            user=self.member, organization_id=self.org_id, status=Membership.Status.ACTIVE
        )

    def _share(self, **overrides):
        payload = {
            "resource_type": "storage.bucket",
            "resource_id": self.bucket_id,
            "principal_type": "user",
            "user_id": str(self.member.id),
            "level": "read",
        }
        payload.update(overrides)
        return self.client.post(
            reverse("share-grant-list-create", args=[self.org_id]), payload, format="json"
        )

    def _upload(self):
        return self.client.post(
            reverse("file-list-create", args=[self.bucket_id]),
            {"file": SimpleUploadedFile("b.txt", b"world", content_type="text/plain")},
            format="multipart",
        )


class UserLevelSharingTests(SharingTestBase):
    def test_read_level_share_grants_read_but_not_write(self):
        share = self._share(level="read")
        self.assertEqual(share.status_code, status.HTTP_201_CREATED)

        self.client.force_login(self.member)
        self.assertEqual(
            self.client.get(reverse("file-list-create", args=[self.bucket_id])).status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(self._upload().status_code, status.HTTP_403_FORBIDDEN)

    def test_write_level_share_grants_read_and_write(self):
        share = self._share(level="write")
        self.assertEqual(share.status_code, status.HTTP_201_CREATED)

        self.client.force_login(self.member)
        self.assertEqual(
            self.client.get(reverse("file-list-create", args=[self.bucket_id])).status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(self._upload().status_code, status.HTTP_201_CREATED)

    def test_before_any_share_the_member_has_no_access(self):
        self.client.force_login(self.member)
        resp = self.client.get(reverse("file-list-create", args=[self.bucket_id]))
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_revoking_a_share_removes_access(self):
        share = self._share(level="read")
        share_id = share.data["id"]

        self.client.force_login(self.member)
        self.assertEqual(
            self.client.get(reverse("file-list-create", args=[self.bucket_id])).status_code,
            status.HTTP_200_OK,
        )

        self.client.force_login(self.admin)
        revoke = self.client.delete(reverse("share-grant-detail", args=[share_id]))
        self.assertEqual(revoke.status_code, status.HTTP_204_NO_CONTENT)

        self.client.force_login(self.member)
        resp = self.client.get(reverse("file-list-create", args=[self.bucket_id]))
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_member_without_sharing_manage_cannot_create_a_share(self):
        plain = User.objects.create_user(email="share-plain@example.com", password="x")
        Membership.objects.create(user=plain, organization_id=self.org_id, status=Membership.Status.ACTIVE)
        self.client.force_login(plain)

        resp = self._share(level="read")
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_sharing_a_resource_id_outside_the_organization_is_rejected(self):
        import uuid

        resp = self._share(resource_id=str(uuid.uuid4()))
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_admin_level_tenant_database_share_grants_all_three_permissions(self):
        db = self.client.post(
            reverse("tenant-database-list-create", args=[self.project_id]), {"name": "AppDB"}
        )
        resp = self._share(
            resource_type="databases.tenant_database", resource_id=db.data["id"], level="admin"
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        grants = ResourceGrant.objects.filter(
            user=self.member, resource_type="databases.tenant_database", resource_id=db.data["id"]
        )
        self.assertEqual(
            set(grants.values_list("permission_id", flat=True)),
            {"database.read", "database.write", "dataset.export"},
        )

    def test_write_level_is_rejected_for_connected_databases_read_only_resource(self):
        import uuid

        resp = self._share(
            resource_type="databases.connected_database", resource_id=str(uuid.uuid4()), level="write"
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)


class TeamAndOrganizationLevelSharingTests(SharingTestBase):
    def test_sharing_with_a_team_grants_access_to_its_current_members(self):
        team = self.client.post(reverse("team-list-create", args=[self.org_id]), {"name": "Eng"})
        self.client.post(
            reverse("team-member-list-create", args=[team.data["id"]]), {"user_id": str(self.member.id)}
        )

        share = self._share(principal_type="team", team_id=team.data["id"], user_id=None, level="read")
        self.assertEqual(share.status_code, status.HTTP_201_CREATED)

        self.client.force_login(self.member)
        resp = self.client.get(reverse("file-list-create", args=[self.bucket_id]))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_sharing_with_the_whole_organization_grants_access_to_active_members(self):
        share = self._share(principal_type="organization", user_id=None, level="read")
        self.assertEqual(share.status_code, status.HTTP_201_CREATED)

        self.client.force_login(self.member)
        resp = self.client.get(reverse("file-list-create", args=[self.bucket_id]))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)


class ExternalSharingToggleTests(SharingTestBase):
    def test_enabling_is_rejected_when_the_deployment_flag_is_off(self):
        resp = self.client.patch(
            reverse("external-sharing-setting", args=[self.org_id]), {"enabled": True}, format="json"
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    @override_settings(FEATURE_EXTERNAL_SHARING_ENABLED=True)
    def test_enabling_succeeds_when_the_deployment_flag_is_on_and_is_audited(self):
        resp = self.client.patch(
            reverse("external-sharing-setting", args=[self.org_id]), {"enabled": True}, format="json"
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(resp.data["external_sharing_enabled"])
        self.assertTrue(
            AuditEvent.objects.filter(
                organization_id=self.org_id, action="sharing.external.enable"
            ).exists()
        )

    def test_disabling_is_always_allowed_regardless_of_the_deployment_flag(self):
        resp = self.client.patch(
            reverse("external-sharing-setting", args=[self.org_id]), {"enabled": False}, format="json"
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertFalse(resp.data["external_sharing_enabled"])

    def test_member_without_sharing_manage_cannot_toggle(self):
        plain = User.objects.create_user(email="share-plain2@example.com", password="x")
        Membership.objects.create(user=plain, organization_id=self.org_id, status=Membership.Status.ACTIVE)
        self.client.force_login(plain)

        resp = self.client.patch(
            reverse("external-sharing-setting", args=[self.org_id]), {"enabled": False}, format="json"
        )
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)
