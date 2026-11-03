from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import User
from audit.models import AuditEvent
from organizations.models import Membership
from permissions.management.commands.seed_permissions import Command as SeedPermissionsCommand
from permissions.models import RoleAssignment


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

    def test_duplicate_name_gets_a_disambiguated_slug_instead_of_a_500(self):
        first = self.client.post(reverse("organization-list-create"), {"name": "Acme Corp"})
        self.assertEqual(first.status_code, status.HTTP_201_CREATED)

        other_owner = User.objects.create_user(email="other-acme@example.com", password="x")
        self.client.force_login(other_owner)
        second = self.client.post(reverse("organization-list-create"), {"name": "Acme Corp"})

        self.assertEqual(second.status_code, status.HTTP_201_CREATED)
        self.assertEqual(second.data["name"], "Acme Corp")
        self.assertNotEqual(second.data["slug"], first.data["slug"])
        self.assertTrue(second.data["slug"].startswith("acme-corp"))

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


class OrgLessUserTests(APITestCase):
    """A user is a valid, fully authenticated IntraForge identity with zero
    organization memberships — this is a normal, permanent state, not a
    transient step every user passes through on the way to owning an
    organization. See docs/architecture (onboarding) for the decision this
    covers."""

    def setUp(self):
        seed()
        self.user = User.objects.create_user(email="solo@example.com", password="x")
        self.client.force_login(self.user)

    def test_organization_list_is_empty_not_an_error(self):
        response = self.client.get(reverse("organization-list-create"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [])

    def test_a_foreign_organizations_resources_are_denied_cleanly(self):
        other_owner = User.objects.create_user(email="other-owner@example.com", password="x")
        self.client.force_login(other_owner)
        org = self.client.post(reverse("organization-list-create"), {"name": "Someone Else's Org"})
        org_id = org.data["id"]

        self.client.force_login(self.user)
        detail = self.client.get(reverse("organization-detail", args=[org_id]))
        self.assertIn(detail.status_code, (status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND))

        members = self.client.get(reverse("membership-list-create", args=[org_id]))
        self.assertIn(members.status_code, (status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND))

    def test_creating_an_organization_later_still_works_for_a_previously_org_less_user(self):
        response = self.client.post(reverse("organization-list-create"), {"name": "Late Org"})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        listing = self.client.get(reverse("organization-list-create"))
        self.assertEqual(len(listing.data), 1)
        self.assertEqual(listing.data[0]["name"], "Late Org")


class MemberRoleManagementTests(APITestCase):
    """The members page's role controls: list, give, take away -- capability-checked, audited, and
    confined to the caller's own organization."""

    def setUp(self):
        seed()
        self.admin = User.objects.create_user(email="owner@shop.test", password="x")
        self.client.force_login(self.admin)
        self.org_id = self.client.post(reverse("organization-list-create"), {"name": "Shop"}).data["id"]
        self.admin_membership = Membership.objects.get(user=self.admin, organization_id=self.org_id)
        self.staff = User.objects.create_user(email="sara@shop.test", password="x")
        self.membership = Membership.objects.create(
            user=self.staff, organization_id=self.org_id, status=Membership.Status.ACTIVE
        )

    def give(self, client, role, org_id=None, membership_id=None):
        return client.post(
            reverse(
                "membership-role-assign", args=[org_id or self.org_id, membership_id or self.membership.id]
            ),
            {"role_slug": role},
        )

    def take(self, client, role, org_id=None, membership_id=None):
        return client.delete(
            reverse(
                "membership-role-remove",
                args=[org_id or self.org_id, membership_id or self.membership.id, role],
            )
        )

    def test_roles_list_offers_organization_roles_with_summaries_and_shows_who_has_what(self):
        self.give(self.client, "spare-parts-sales")
        resp = self.client.get(reverse("organization-roles", args=[self.org_id]))
        self.assertEqual(resp.status_code, 200)
        slugs = [r["slug"] for r in resp.data["roles"]]
        self.assertIn("spare-parts-sales", slugs)
        self.assertNotIn("super-administrator", slugs)
        self.assertNotIn("service-account", slugs)
        admin_role = next(r for r in resp.data["roles"] if r["slug"] == "organization-administrator")
        self.assertTrue(admin_role["administrative"])
        self.assertTrue(all(r["summary"] and r["name"] for r in resp.data["roles"]))
        self.assertIn(
            {"membership_id": str(self.membership.id), "role_slug": "spare-parts-sales"},
            resp.data["assignments"],
        )
        self.assertIn(
            {"membership_id": str(self.admin_membership.id), "role_slug": "organization-administrator"},
            resp.data["assignments"],
        )

    def test_give_is_idempotent_and_audited_once(self):
        self.assertEqual(self.give(self.client, "spare-parts-sales").status_code, 201)
        self.assertEqual(self.give(self.client, "spare-parts-sales").status_code, 200)
        self.assertEqual(
            RoleAssignment.objects.filter(user=self.staff, organization_id=self.org_id).count(), 1
        )
        self.assertEqual(
            AuditEvent.objects.filter(
                action="permissions.role.assign", resource_id=str(self.staff.id)
            ).count(),
            1,
        )

    def _application_membership(self):
        from applications.services import register_application
        from organizations.models import Organization

        application = register_application(
            organization=Organization.objects.get(id=self.org_id),
            name="pay intraforge",
            description="",
            owner=self.admin,
        )
        identity = application.service_account.identity_user
        return Membership.objects.get(user=identity, organization_id=self.org_id), identity

    def test_an_applications_service_account_cannot_be_given_an_organization_role(self):
        membership, identity = self._application_membership()
        for role in ("organization-administrator", "spare-parts-sales", "viewer"):
            resp = self.give(self.client, role, membership_id=membership.id)
            self.assertEqual(resp.status_code, 400)
            self.assertIn("pay intraforge", resp.data["detail"])
        self.assertFalse(RoleAssignment.objects.filter(user=identity).exists())
        self.assertFalse(
            AuditEvent.objects.filter(action="permissions.role.assign", resource_id=str(identity.id)).exists()
        )

    def test_members_list_names_the_application_behind_a_service_account(self):
        membership, _ = self._application_membership()
        resp = self.client.get(reverse("membership-list-create", args=[self.org_id]))
        self.assertEqual(resp.status_code, 200)
        rows = {row["id"]: row for row in resp.data}
        self.assertEqual(rows[str(membership.id)]["application"]["name"], "pay intraforge")
        self.assertIsNone(rows[str(self.membership.id)]["application"])

    def test_platform_and_application_roles_cannot_be_given_here(self):
        for role in ("super-administrator", "service-account", "no-such-role"):
            self.assertEqual(self.give(self.client, role).status_code, 400)
        self.assertFalse(RoleAssignment.objects.filter(user=self.staff).exists())

    def test_take_away_removes_and_audits(self):
        self.give(self.client, "spare-parts-sales")
        self.assertEqual(self.take(self.client, "spare-parts-sales").status_code, 204)
        self.assertFalse(RoleAssignment.objects.filter(user=self.staff, organization_id=self.org_id).exists())
        event = AuditEvent.objects.get(action="permissions.role.remove")
        self.assertEqual(event.context, {"role": "spare-parts-sales"})
        self.assertEqual(event.actor, self.admin)
        self.assertEqual(self.take(self.client, "spare-parts-sales").status_code, 404)

    def test_the_last_organization_administrator_cannot_be_removed(self):
        resp = self.take(self.client, "organization-administrator", membership_id=self.admin_membership.id)
        self.assertEqual(resp.status_code, 409)
        self.assertIn("last Organization Administrator", resp.data["detail"])
        self.give(self.client, "organization-administrator")
        resp = self.take(self.client, "organization-administrator", membership_id=self.admin_membership.id)
        self.assertEqual(resp.status_code, 204)

    def test_a_suspended_administrator_does_not_count_as_the_remaining_one(self):
        self.give(self.client, "organization-administrator")
        Membership.objects.filter(pk=self.membership.pk).update(status=Membership.Status.SUSPENDED)
        resp = self.take(self.client, "organization-administrator", membership_id=self.admin_membership.id)
        self.assertEqual(resp.status_code, 409)

    def test_members_without_permissions_manage_can_neither_see_nor_change_roles(self):
        self.give(self.client, "spare-parts-manager")
        staff_client = self.client_class()
        staff_client.force_login(self.staff)
        self.assertEqual(staff_client.get(reverse("organization-roles", args=[self.org_id])).status_code, 403)
        self.assertEqual(self.give(staff_client, "organization-administrator").status_code, 403)
        resp = self.take(staff_client, "organization-administrator", membership_id=self.admin_membership.id)
        self.assertEqual(resp.status_code, 403)
        self.assertFalse(
            RoleAssignment.objects.filter(user=self.staff, role__slug="organization-administrator").exists()
        )

    def test_another_organization_cannot_be_reached_by_id_substitution(self):
        other_admin = User.objects.create_user(email="other@shop2.test", password="x")
        other = self.client_class()
        other.force_login(other_admin)
        other_org = other.post(reverse("organization-list-create"), {"name": "Shop Two"}).data["id"]
        other_membership = Membership.objects.get(user=other_admin, organization_id=other_org)

        # The other organization's administrator, naming this organization: not a member -> 404.
        self.assertEqual(other.get(reverse("organization-roles", args=[self.org_id])).status_code, 404)
        self.assertEqual(self.give(other, "organization-administrator").status_code, 404)
        self.assertEqual(self.take(other, "spare-parts-sales").status_code, 404)
        # This administrator, naming the other organization's membership under this organization: 404.
        self.assertEqual(self.give(self.client, "viewer", membership_id=other_membership.id).status_code, 404)
        resp = self.take(self.client, "organization-administrator", membership_id=other_membership.id)
        self.assertEqual(resp.status_code, 404)
        # ...and under the other organization, where this administrator is not a member: 404.
        resp = self.give(self.client, "viewer", org_id=other_org, membership_id=other_membership.id)
        self.assertEqual(resp.status_code, 404)
        self.assertTrue(
            RoleAssignment.objects.filter(user=other_admin, role__slug="organization-administrator").exists()
        )
        self.assertFalse(RoleAssignment.objects.filter(user=other_admin, role__slug="viewer").exists())

    @override_settings(FEATURE_INTERNET_GATEWAY_ENABLED=True)
    def test_gateway_mode_refuses_an_administrative_role_without_mfa_with_a_clear_message(self):
        resp = self.give(self.client, "organization-administrator")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("MFA", resp.data["detail"])
        self.assertEqual(self.give(self.client, "spare-parts-sales").status_code, 201)
