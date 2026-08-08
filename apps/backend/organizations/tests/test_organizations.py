from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import User
from organizations.models import Membership
from permissions.management.commands.seed_permissions import Command as SeedPermissionsCommand


def seed():
    SeedPermissionsCommand().handle()


class CreateOrganizationTests(APITestCase):
    def setUp(self):
        seed()
        self.user = User.objects.create_user(email="owner@example.com", password="x")
        self.client.force_login(self.user)

    def test_creator_becomes_active_member_and_administrator(self):
        response = self.client.post(reverse("organization-list-create"), {"name": "Acme"})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        org_id = response.data["id"]

        membership = Membership.objects.get(user=self.user, organization_id=org_id)
        self.assertEqual(membership.status, Membership.Status.ACTIVE)

        detail = self.client.get(reverse("organization-detail", args=[org_id]))
        self.assertEqual(detail.status_code, status.HTTP_200_OK)

    def test_list_only_returns_orgs_the_user_belongs_to(self):
        self.client.post(reverse("organization-list-create"), {"name": "Mine"})

        other_owner = User.objects.create_user(email="other@example.com", password="x")
        self.client.force_login(other_owner)
        self.client.post(reverse("organization-list-create"), {"name": "TheirsOnly"})

        response = self.client.get(reverse("organization-list-create"))
        names = {org["name"] for org in response.data}
        self.assertEqual(names, {"TheirsOnly"})


class MembershipTests(APITestCase):
    def setUp(self):
        seed()
        self.admin = User.objects.create_user(email="admin@example.com", password="x")
        self.client.force_login(self.admin)
        response = self.client.post(reverse("organization-list-create"), {"name": "Acme"})
        self.org_id = response.data["id"]

    def test_admin_can_add_an_existing_user_as_a_member(self):
        User.objects.create_user(email="invitee@example.com", password="x")
        response = self.client.post(
            reverse("membership-list-create", args=[self.org_id]), {"email": "invitee@example.com"}
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        members = self.client.get(reverse("membership-list-create", args=[self.org_id]))
        emails = {m["user"]["email"] for m in members.data}
        self.assertEqual(emails, {"admin@example.com", "invitee@example.com"})

    def test_adding_a_member_twice_is_rejected(self):
        User.objects.create_user(email="invitee2@example.com", password="x")
        url = reverse("membership-list-create", args=[self.org_id])
        self.client.post(url, {"email": "invitee2@example.com"})
        response = self.client.post(url, {"email": "invitee2@example.com"})
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

    def test_adding_an_unknown_user_returns_404(self):
        response = self.client.post(
            reverse("membership-list-create", args=[self.org_id]), {"email": "ghost@example.com"}
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_non_admin_member_cannot_add_members(self):
        plain_member = User.objects.create_user(email="plain@example.com", password="x")
        Membership.objects.create(
            user=plain_member, organization_id=self.org_id, status=Membership.Status.ACTIVE
        )
        self.client.force_login(plain_member)

        User.objects.create_user(email="target@example.com", password="x")
        response = self.client.post(
            reverse("membership-list-create", args=[self.org_id]), {"email": "target@example.com"}
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_assign_a_role_to_a_member(self):
        member = User.objects.create_user(email="member@example.com", password="x")
        membership = Membership.objects.create(
            user=member, organization_id=self.org_id, status=Membership.Status.ACTIVE
        )
        response = self.client.post(
            reverse("membership-role-assign", args=[self.org_id, membership.id]),
            {"role_slug": "viewer"},
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
