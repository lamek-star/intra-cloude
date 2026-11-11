from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import User
from audit.models import AuditEvent
from organizations.models import Membership
from permissions.management.commands.seed_permissions import Command as SeedPermissionsCommand


class WorkspaceProjectTests(APITestCase):
    def setUp(self):
        SeedPermissionsCommand().handle()
        self.user = User.objects.create_user(email="ws@example.com", password="x")
        self.client.force_login(self.user)
        resp = self.client.post(reverse("organization-list-create"), {"name": "Acme"})
        self.org_id = resp.data["id"]

    def test_create_and_list_workspace(self):
        resp = self.client.post(
            reverse("workspace-list-create", args=[self.org_id]), {"name": "Marketing"}
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        workspace_id = resp.data["id"]

        listing = self.client.get(reverse("workspace-list-create", args=[self.org_id]))
        self.assertEqual([w["id"] for w in listing.data], [workspace_id])

        detail = self.client.get(reverse("workspace-detail", args=[workspace_id]))
        self.assertEqual(detail.status_code, status.HTTP_200_OK)

        event = AuditEvent.objects.get(action="workspace.create", resource_id=workspace_id)
        self.assertEqual(str(event.organization_id), self.org_id)
        self.assertEqual(event.actor_id, self.user.id)
        self.assertEqual(event.context["name"], "Marketing")

    def test_create_and_list_project(self):
        ws = self.client.post(
            reverse("workspace-list-create", args=[self.org_id]), {"name": "Marketing"}
        )
        workspace_id = ws.data["id"]

        resp = self.client.post(
            reverse("project-list-create", args=[workspace_id]), {"name": "Q1 Campaign"}
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        project_id = resp.data["id"]

        detail = self.client.get(reverse("project-detail", args=[project_id]))
        self.assertEqual(detail.status_code, status.HTTP_200_OK)

        event = AuditEvent.objects.get(action="project.create", resource_id=project_id)
        self.assertEqual(str(event.organization_id), self.org_id)
        self.assertEqual(event.actor_id, self.user.id)
        self.assertEqual(event.context["name"], "Q1 Campaign")

    def test_non_member_cannot_see_workspace(self):
        ws = self.client.post(
            reverse("workspace-list-create", args=[self.org_id]), {"name": "Private"}
        )
        workspace_id = ws.data["id"]

        outsider = User.objects.create_user(email="outsider@example.com", password="x")
        self.client.force_login(outsider)

        detail = self.client.get(reverse("workspace-detail", args=[workspace_id]))
        self.assertEqual(detail.status_code, status.HTTP_404_NOT_FOUND)


class WorkspaceProjectPermissionTests(APITestCase):
    """
    Creating a Workspace or Project previously required only active
    organization membership -- no permission at all existed to gate it,
    unlike every resource one tier down (database.create, storage.manage
    for buckets). Any invited member, regardless of role, could create
    new organizational structure. Fixed by adding workspace.manage,
    granted by default to organization-administrator (automatically, via
    the "all permissions" grant), database-administrator,
    storage-administrator, and developer -- not editor/viewer/auditor,
    matching their existing "work within existing structure" character.
    """

    def setUp(self):
        SeedPermissionsCommand().handle()
        self.admin = User.objects.create_user(email="ws-admin@example.com", password="x")
        self.client.force_login(self.admin)
        org = self.client.post(reverse("organization-list-create"), {"name": "Acme"})
        self.org_id = org.data["id"]

    def _add_plain_member(self, email):
        member = User.objects.create_user(email=email, password="x")
        Membership.objects.create(
            user=member, organization_id=self.org_id, status=Membership.Status.ACTIVE
        )
        return member

    def test_plain_member_cannot_create_workspace(self):
        member = self._add_plain_member("ws-plain@example.com")
        self.client.force_login(member)
        resp = self.client.post(reverse("workspace-list-create", args=[self.org_id]), {"name": "Nope"})
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

        event = AuditEvent.objects.get(action="workspace.create", actor=member)
        self.assertEqual(event.result, AuditEvent.Result.DENIED)

    def test_plain_member_cannot_create_project(self):
        ws = self.client.post(reverse("workspace-list-create", args=[self.org_id]), {"name": "Eng"})
        workspace_id = ws.data["id"]

        member = self._add_plain_member("ws-plain2@example.com")
        self.client.force_login(member)
        resp = self.client.post(reverse("project-list-create", args=[workspace_id]), {"name": "Nope"})
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

        event = AuditEvent.objects.get(action="project.create", actor=member)
        self.assertEqual(event.result, AuditEvent.Result.DENIED)

    def test_developer_role_can_create_workspace_and_project(self):
        from organizations.models import Organization
        from permissions.services import assign_role

        developer = self._add_plain_member("ws-dev@example.com")
        assign_role(
            user=developer, role_slug="developer", organization=Organization.objects.get(id=self.org_id)
        )
        self.client.force_login(developer)

        ws = self.client.post(reverse("workspace-list-create", args=[self.org_id]), {"name": "Eng"})
        self.assertEqual(ws.status_code, status.HTTP_201_CREATED)

        proj = self.client.post(
            reverse("project-list-create", args=[ws.data["id"]]), {"name": "Platform"}
        )
        self.assertEqual(proj.status_code, status.HTTP_201_CREATED)
