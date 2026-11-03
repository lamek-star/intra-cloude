from django.urls import reverse
from rest_framework.test import APITestCase

from accounts.models import User
from applications import services as app_services
from audit import services as audit
from organizations.models import Membership
from permissions.management.commands.seed_permissions import Command as SeedPermissionsCommand


class AuditActorDisplayTests(APITestCase):
    """H15: the audit list says who did each action -- a member's email, an application's
    name -- and never names an account from outside the organization."""

    def setUp(self):
        SeedPermissionsCommand().handle()
        self.admin = User.objects.create_user(email="audit-admin@example.com", password="x")
        self.client.force_login(self.admin)
        self.org_id = self.client.post(reverse("organization-list-create"), {"name": "Acme"}).data["id"]
        self.url = reverse("audit-event-list", args=[self.org_id])

    def _display_for(self, action):
        events = self.client.get(self.url, {"action": action}).data["results"]
        self.assertEqual(len(events), 1)
        return events[0]["actor_display"]

    def test_a_member_is_shown_by_email(self):
        member = User.objects.create_user(email="clerk@example.com", password="x")
        Membership.objects.create(user=member, organization_id=self.org_id, status=Membership.Status.ACTIVE)
        audit.record(actor=member, organization_id=self.org_id, action="test.member")
        self.assertEqual(self._display_for("test.member"), "clerk@example.com")

    def test_an_application_is_shown_by_its_name(self):
        from organizations.models import Organization

        application = app_services.register_application(
            organization=Organization.objects.get(id=self.org_id),
            name="School Website",
            description="",
            owner=self.admin,
        )
        audit.record(
            actor=application.service_account.identity_user, organization_id=self.org_id, action="test.app"
        )
        self.assertEqual(self._display_for("test.app"), "School Website (application)")

    def test_an_outside_account_is_not_named_and_no_actor_is_system(self):
        outsider = User.objects.create_user(email="outsider@example.com", password="x")
        audit.record(actor=outsider, organization_id=self.org_id, action="test.outsider")
        audit.record(actor=None, organization_id=self.org_id, action="test.system")
        self.assertEqual(self._display_for("test.outsider"), "An account outside this organization")
        self.assertEqual(self._display_for("test.system"), "System")
