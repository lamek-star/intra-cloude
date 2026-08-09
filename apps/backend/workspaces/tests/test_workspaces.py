from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import User
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

    def test_non_member_cannot_see_workspace(self):
        ws = self.client.post(
            reverse("workspace-list-create", args=[self.org_id]), {"name": "Private"}
        )
        workspace_id = ws.data["id"]

        outsider = User.objects.create_user(email="outsider@example.com", password="x")
        self.client.force_login(outsider)

        detail = self.client.get(reverse("workspace-detail", args=[workspace_id]))
        self.assertEqual(detail.status_code, status.HTTP_404_NOT_FOUND)
