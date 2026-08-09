from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import User
from organizations.models import Membership, Team
from permissions.management.commands.seed_permissions import Command as SeedPermissionsCommand


class TeamTestBase(APITestCase):
    def setUp(self):
        SeedPermissionsCommand().handle()
        self.admin = User.objects.create_user(email="team-admin@example.com", password="x")
        self.client.force_login(self.admin)
        org = self.client.post(reverse("organization-list-create"), {"name": "Acme"})
        self.org_id = org.data["id"]


class TeamCreationTests(TeamTestBase):
    def test_create_and_list_teams(self):
        resp = self.client.post(reverse("team-list-create", args=[self.org_id]), {"name": "Engineering"})
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

        listing = self.client.get(reverse("team-list-create", args=[self.org_id]))
        self.assertEqual(listing.status_code, status.HTTP_200_OK)
        self.assertEqual([t["name"] for t in listing.data], ["Engineering"])

    def test_member_without_users_manage_cannot_create_team(self):
        member = User.objects.create_user(email="team-plain@example.com", password="x")
        Membership.objects.create(user=member, organization_id=self.org_id, status=Membership.Status.ACTIVE)
        self.client.force_login(member)

        resp = self.client.post(reverse("team-list-create", args=[self.org_id]), {"name": "Sneaky"})
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)


class TeamMembershipTests(TeamTestBase):
    def setUp(self):
        super().setUp()
        team = self.client.post(reverse("team-list-create", args=[self.org_id]), {"name": "Engineering"})
        self.team_id = team.data["id"]
        self.member = User.objects.create_user(email="team-member@example.com", password="x")
        Membership.objects.create(
            user=self.member, organization_id=self.org_id, status=Membership.Status.ACTIVE
        )

    def test_add_and_remove_team_member(self):
        add = self.client.post(
            reverse("team-member-list-create", args=[self.team_id]), {"user_id": str(self.member.id)}
        )
        self.assertEqual(add.status_code, status.HTTP_201_CREATED)
        membership = Membership.objects.get(user=self.member, organization_id=self.org_id)
        self.assertEqual(str(membership.team_id), self.team_id)

        remove = self.client.delete(
            reverse("team-member-detail", args=[self.team_id, self.member.id])
        )
        self.assertEqual(remove.status_code, status.HTTP_204_NO_CONTENT)
        membership.refresh_from_db()
        self.assertIsNone(membership.team_id)

    def test_cannot_add_a_non_member_of_the_organization_to_a_team(self):
        outsider = User.objects.create_user(email="outsider@example.com", password="x")
        resp = self.client.post(
            reverse("team-member-list-create", args=[self.team_id]), {"user_id": str(outsider.id)}
        )
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)


class TeamModelTests(TeamTestBase):
    def test_team_name_unique_per_organization(self):
        self.client.post(reverse("team-list-create", args=[self.org_id]), {"name": "Engineering"})
        dup = self.client.post(reverse("team-list-create", args=[self.org_id]), {"name": "Engineering"})
        self.assertEqual(dup.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(Team.objects.filter(organization_id=self.org_id, name="Engineering").count(), 1)
