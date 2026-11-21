"""A person's contact details (their own, or changed by their administrator), and the Super Administrator command the
shop PC's Control Center runs."""

import json
from io import StringIO

from django.core.cache import cache
from django.core.management import CommandError, call_command
from django.urls import reverse
from rest_framework.test import APITestCase

from accounts.models import User
from audit.models import AuditEvent
from organizations.models import Membership
from organizations.services import create_organization
from permissions.management.commands.seed_permissions import Command as SeedPermissionsCommand
from permissions.services import assign_role, has_permission

PASSWORD = "a-strong-passw0rd!"
DETAILS = {
    "first_name": "Sami",
    "last_name": "Tesfay",
    "phone": "+971 50 123 4567",
    "job_title": "Shop manager",
    "address": "Deira, Dubai",
    "emergency_contact": "Hana, +971 55 000 1111",
}


class OwnDetailsTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(email="sami@example.com", password=PASSWORD)
        self.client.force_login(self.user)

    def test_a_person_fills_in_their_own_details_and_sees_them(self):
        resp = self.client.patch(reverse("auth-me"), DETAILS, format="json")
        self.assertEqual(resp.status_code, 200, resp.data)
        me = self.client.get(reverse("auth-me")).data
        for key, value in DETAILS.items():
            self.assertEqual(me[key], value)
        event = AuditEvent.objects.get(action="user.profile.update")
        self.assertEqual(sorted(event.context["fields"]), sorted(DETAILS))
        self.assertNotIn("+971", json.dumps(event.context), "the audit names fields, never personal values")

    def test_the_email_cannot_be_changed_here_and_a_bad_phone_is_refused(self):
        self.client.patch(reverse("auth-me"), {"email": "other@example.com"}, format="json")
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, "sami@example.com")
        for bad in ("call me", "12", "+1 <script>"):
            self.assertEqual(self.client.patch(reverse("auth-me"), {"phone": bad}, format="json").status_code, 400)
        self.assertEqual(self.client.patch(reverse("auth-me"), {"phone": ""}, format="json").status_code, 200)

    def test_nothing_changed_writes_no_audit_event(self):
        self.client.patch(reverse("auth-me"), {"job_title": ""}, format="json")
        self.assertFalse(AuditEvent.objects.filter(action="user.profile.update").exists())


class MemberDetailsTests(APITestCase):
    def setUp(self):
        cache.clear()
        SeedPermissionsCommand().handle()
        self.owner = User.objects.create_user(email="shop-owner@example.com", password=PASSWORD)
        self.org = create_organization(name="Shop A", created_by=self.owner)
        self.staff = User.objects.create_user(email="staff@example.com", password=PASSWORD)
        self.membership = Membership.objects.create(
            user=self.staff, organization=self.org, status=Membership.Status.ACTIVE
        )
        self.client.force_login(self.owner)

    def url(self, membership=None):
        return reverse("membership-profile", args=[self.org.id, (membership or self.membership).id])

    def test_the_administrator_fills_in_a_members_details_and_the_members_list_shows_them(self):
        resp = self.client.patch(self.url(), {"phone": "0501234567", "job_title": "Cashier"}, format="json")
        self.assertEqual(resp.status_code, 200, resp.data)
        members = self.client.get(reverse("membership-list-create", args=[self.org.id])).data
        rows = members["results"] if isinstance(members, dict) else members
        staff = next(m for m in rows if m["user"]["email"] == "staff@example.com")
        self.assertEqual((staff["user"]["phone"], staff["user"]["job_title"]), ("0501234567", "Cashier"))
        event = AuditEvent.objects.get(action="user.profile.update")
        self.assertEqual(str(event.organization_id), str(self.org.id))
        self.assertFalse(event.context["own"])

    def test_not_a_plain_member_not_the_super_administrator_not_someone_in_another_shop(self):
        plain = User.objects.create_user(email="plain@example.com", password=PASSWORD)
        Membership.objects.create(user=plain, organization=self.org, status=Membership.Status.ACTIVE)
        self.client.force_login(plain)
        self.assertEqual(self.client.patch(self.url(), {"phone": "0501234567"}, format="json").status_code, 403)

        self.client.force_login(self.owner)
        other_owner = User.objects.create_user(email="other-owner@example.com", password=PASSWORD)
        other = create_organization(name="Shop B", created_by=other_owner)
        Membership.objects.create(user=self.staff, organization=other, status=Membership.Status.ACTIVE)
        self.assertEqual(self.client.patch(self.url(), {"phone": "0501234567"}, format="json").status_code, 403)

        boss = User.objects.create_user(email="boss@example.com", password=PASSWORD)
        boss_membership = Membership.objects.create(user=boss, organization=self.org, status=Membership.Status.ACTIVE)
        assign_role(user=boss, role_slug="super-administrator", organization=None)
        self.assertEqual(
            self.client.patch(self.url(boss_membership), {"phone": "0501234567"}, format="json").status_code, 403
        )
        self.staff.refresh_from_db()
        self.assertEqual(self.staff.phone, "")


class SuperAdministratorCommandTests(APITestCase):
    def setUp(self):
        SeedPermissionsCommand().handle()
        self.sami = User.objects.create_user(email="sami@example.com", password=PASSWORD, first_name="Sami")
        self.hana = User.objects.create_user(email="hana@example.com", password=PASSWORD)

    def run_command(self, *args):
        out = StringIO()
        call_command("super_administrators", *args, stdout=out)
        return out.getvalue()

    def is_super(self, user):
        return has_permission(user, "system.admin", organization_id=None)

    def test_grant_list_and_revoke_with_an_audit_trail(self):
        self.assertIn("is now a Super Administrator", self.run_command("grant", "SAMI@example.com"))
        self.assertTrue(self.is_super(self.sami))
        people = json.loads(self.run_command("list", "--json"))
        self.assertEqual(
            [(p["email"], p["super_administrator"]) for p in people],
            [("hana@example.com", False), ("sami@example.com", True)],
        )
        self.assertIn("already", self.run_command("grant", "sami@example.com"))
        self.run_command("grant", "hana@example.com")
        self.assertIn("no longer", self.run_command("revoke", "sami@example.com"))
        self.assertFalse(self.is_super(self.sami))
        actions = sorted(
            AuditEvent.objects.filter(action__startswith="system.super_administrator").values_list("action", flat=True)
        )
        expected = ["system.super_administrator.grant"] * 2 + ["system.super_administrator.revoke"]
        self.assertEqual(actions, sorted(expected))

    def test_the_last_one_stays_and_only_active_people_can_be_made_one(self):
        self.run_command("grant", "sami@example.com")
        with self.assertRaisesMessage(CommandError, "only Super Administrator"):
            self.run_command("revoke", "sami@example.com")
        self.assertTrue(self.is_super(self.sami))
        with self.assertRaisesMessage(CommandError, "No account"):
            self.run_command("grant", "nobody@example.com")
        self.hana.is_active = False
        self.hana.save()
        with self.assertRaisesMessage(CommandError, "switched off"):
            self.run_command("grant", "hana@example.com")
