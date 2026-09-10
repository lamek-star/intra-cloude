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
from app_platform import instances, templates
from app_platform.tests.test_foundation import sample
from audit.models import AuditEvent
from organizations.models import Membership, Organization
from permissions.management.commands.seed_permissions import Command as SeedPermissionsCommand
from permissions.models import ResourceGrant
from workspaces.models import Project


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


class AppInstanceSharingTests(SharingTestBase):
    """App Platform Phase 3 step 4 ("basic permissions"): an app instance's
    metadata (definitions, not the records it stores once provisioned --
    see RESOURCE_TYPE_TENANT_DATABASE above for that) reuses this same
    sharing mechanism rather than a bespoke one."""

    def _install_instance(self):
        org = Organization.objects.get(pk=self.org_id)
        project = Project.objects.get(pk=self.project_id)
        template = templates.create_template(self.admin, org, {"label": "App", "draft": sample()})
        version = templates.publish_template(self.admin, template)
        return instances.install(
            self.admin, project, {"label": "Runtime", "template_version": str(version.id)}
        )

    def test_before_any_share_the_member_has_no_access(self):
        instance = self._install_instance()
        self.client.force_login(self.member)
        resp = self.client.get(f"/api/v1/app-instances/{instance.id}/")
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_read_level_share_grants_read_but_not_manage(self):
        instance = self._install_instance()
        share = self._share(resource_type="app_instance", resource_id=str(instance.id), level="read")
        self.assertEqual(share.status_code, status.HTTP_201_CREATED)

        self.client.force_login(self.member)
        read = self.client.get(f"/api/v1/app-instances/{instance.id}/")
        self.assertEqual(read.status_code, status.HTTP_200_OK)
        rename = self.client.patch(
            f"/api/v1/app-instances/{instance.id}/", {"label": "Renamed"}, format="json"
        )
        self.assertEqual(rename.status_code, status.HTTP_403_FORBIDDEN)

    def test_write_level_share_grants_read_and_manage(self):
        instance = self._install_instance()
        share = self._share(resource_type="app_instance", resource_id=str(instance.id), level="write")
        self.assertEqual(share.status_code, status.HTTP_201_CREATED)

        self.client.force_login(self.member)
        rename = self.client.patch(
            f"/api/v1/app-instances/{instance.id}/", {"label": "Renamed"}, format="json"
        )
        self.assertEqual(rename.status_code, status.HTTP_200_OK)

    def test_admin_level_app_instance_share_grants_all_three_permissions(self):
        instance = self._install_instance()
        resp = self._share(resource_type="app_instance", resource_id=str(instance.id), level="admin")
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        grants = ResourceGrant.objects.filter(
            user=self.member, resource_type="app_instance", resource_id=instance.id
        )
        self.assertEqual(
            set(grants.values_list("permission_id", flat=True)),
            {"app_instance.read", "app_instance.manage", "app_instance.schema.manage"},
        )

    def test_revoking_an_app_instance_share_removes_access(self):
        instance = self._install_instance()
        share = self._share(resource_type="app_instance", resource_id=str(instance.id), level="read")
        share_id = share.data["id"]

        self.client.force_login(self.member)
        self.assertEqual(
            self.client.get(f"/api/v1/app-instances/{instance.id}/").status_code, status.HTTP_200_OK
        )

        self.client.force_login(self.admin)
        revoke = self.client.delete(reverse("share-grant-detail", args=[share_id]))
        self.assertEqual(revoke.status_code, status.HTTP_204_NO_CONTENT)

        self.client.force_login(self.member)
        resp = self.client.get(f"/api/v1/app-instances/{instance.id}/")
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_sharing_an_app_instance_id_outside_the_organization_is_rejected(self):
        import uuid

        resp = self._share(resource_type="app_instance", resource_id=str(uuid.uuid4()))
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
