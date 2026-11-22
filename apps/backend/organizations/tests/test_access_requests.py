"""Access requests from each app, approved by an administrator, confirmed by a single-use link (ADR-0026)."""

import uuid
from datetime import timedelta
from io import StringIO

from django.core.cache import cache
from django.core.management import call_command
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from accounts import links
from accounts.models import AccountLink, User
from audit.models import AuditEvent
from organizations.models import AccessRequest, Membership
from permissions.models import RoleAssignment
from service_apps.tests.test_service_apps import INTERNAL, ServiceAppTestBase
from system import features

NEW_PERSON = {
    "email": "hana@example.test",
    "password": "Hana-strong-pass-2026",
    "first_name": "Hana",
    "last_name": "Tesfay",
    "phone": "+971 50 111 2222",
    "requested_role": "spare-parts-sales",
    "message": "I will work at the counter.",
}
INSPECT = "/api/v1/auth/links/inspect/"
CONFIRM = "/api/v1/auth/links/confirm/"


def token_of(link: str) -> str:
    return link.split("#t=")[1]


@override_settings(EMAIL_HOST="")
class AccessRequestTests(ServiceAppTestBase):
    def setUp(self):
        super().setUp()
        cache.clear()  # the "auth" throttle (10/min) is shared by every test in this class
        self.app_id = self.install().data["id"]
        self.anon = APIClient()

    def ask(self, **changes):
        return self.anon.post(f"/api/v1/access/apps/{self.app_id}/", {**NEW_PERSON, **changes}, format="json")

    def requests_url(self, org_id=None):
        return f"/api/v1/organizations/{org_id or self.org_id}/access-requests/"

    def decide(self, request_id, decision, client=None, org_id=None, **body):
        url = f"{self.requests_url(org_id)}{request_id}/{decision}/"
        return (client or self.client).post(url, body, format="json")

    def link_post(self, url, token, **body):
        return self.anon.post(url, {"token": token, **body}, format="json")

    # ------------------------------------------------------------------ asking
    def test_the_page_offers_only_this_apps_jobs(self):
        resp = self.anon.get(f"/api/v1/access/apps/{self.app_id}/")
        self.assertEqual(resp.status_code, 200)
        slugs = [r["slug"] for r in resp.data["roles"]]
        self.assertTrue(slugs and all(s.startswith("spare-parts-") for s in slugs))
        self.assertTrue(resp.data["accepts_requests"])

    def test_a_new_person_gets_an_inactive_account_and_a_pending_request(self):
        resp = self.ask()
        self.assertEqual(resp.status_code, 202)
        user = User.objects.get(email="hana@example.test")
        self.assertFalse(user.is_active)
        self.assertEqual(user.phone, "+971 50 111 2222")
        request = AccessRequest.objects.get(user=user)
        self.assertEqual(request.status, "pending")
        self.assertEqual(request.requested_role, "spare-parts-sales")
        self.assertTrue(request.new_account)
        self.assertFalse(Membership.objects.filter(user=user).exists())
        # An inactive account cannot sign in.
        login = self.anon.post("/api/v1/auth/login/", {"email": user.email, "password": NEW_PERSON["password"]})
        self.assertNotEqual(login.status_code, 200)

    def test_an_existing_email_gets_the_same_answer_and_nothing_is_made(self):
        first = self.ask(email="owner@example.test")
        self.assertEqual(first.status_code, 202)
        self.assertEqual(first.data["detail"], self.ask(email="someone-new@example.test").data["detail"])
        self.assertFalse(AccessRequest.objects.filter(user=self.owner).exists())
        self.assertEqual(User.objects.filter(email__iexact="owner@example.test").count(), 1)

    def test_a_job_of_another_app_or_a_weak_password_is_refused(self):
        self.assertEqual(self.ask(requested_role="organization-administrator").status_code, 400)
        self.assertEqual(self.ask(requested_role="pay-supervisor").status_code, 400)
        self.assertEqual(self.ask(password="short").status_code, 400)
        self.assertFalse(User.objects.filter(email="hana@example.test").exists())

    def test_a_signed_in_person_asks_without_a_second_account(self):
        person = User.objects.create_user(email="kidane@example.test", password="Kidane-pass-12345")
        client = APIClient()
        client.force_login(person)
        url = f"/api/v1/access/apps/{self.app_id}/"
        first = client.post(url, {"requested_role": "spare-parts-inventory"}, format="json")
        self.assertEqual(first.status_code, 202)
        again = client.post(url, {"requested_role": "spare-parts-inventory"}, format="json")
        self.assertEqual(first.data["request"]["id"], again.data["request"]["id"])
        self.assertEqual(AccessRequest.objects.filter(user=person).count(), 1)
        self.assertFalse(AccessRequest.objects.get(user=person).new_account)

    # ------------------------------------------------------------------ registration policy
    def test_closed_registration_refuses_requests(self):
        features.set_registration(self.owner, features.REGISTRATION_CLOSED)
        self.assertEqual(self.ask().status_code, 403)
        self.assertFalse(User.objects.filter(email="hana@example.test").exists())

    def test_plain_sign_up_needs_open_registration_once_an_organization_exists(self):
        body = {"email": "walkin@example.test", "password": "Walkin-pass-12345", "first_name": "W"}
        refused = self.anon.post("/api/v1/auth/register/", body)
        self.assertEqual(refused.status_code, 403)
        self.assertEqual(refused.data["code"], "registration_closed")
        features.set_registration(self.owner, features.REGISTRATION_OPEN)
        self.assertEqual(APIClient().post("/api/v1/auth/register/", body).status_code, 201)
        self.assertTrue(
            AuditEvent.objects.filter(action="system.registration.update", context__after="open").exists()
        )

    # ------------------------------------------------------------------ deciding
    def test_the_administrator_chooses_the_role_and_a_link_activates_the_account(self):
        self.ask()
        request = AccessRequest.objects.get()
        listed = self.client.get(self.requests_url())
        self.assertEqual(listed.status_code, 200)
        self.assertEqual([r["id"] for r in listed.data["results"]], [str(request.id)])
        self.assertFalse(listed.data["email_enabled"])

        resp = self.decide(request.id, "approve", role_slug="spare-parts-viewer", note="Viewer first")
        self.assertEqual(resp.status_code, 200)
        user = request.user
        self.assertTrue(Membership.objects.filter(user=user, organization_id=self.org_id).exists())
        roles = set(RoleAssignment.objects.filter(user=user).values_list("role__slug", flat=True))
        self.assertEqual(roles, {"spare-parts-viewer"})  # the administrator's choice, not the requested one
        self.assertFalse(resp.data["emailed"])
        self.assertIn("/confirm#t=", resp.data["link"])
        token = token_of(resp.data["link"])
        self.assertFalse(AccountLink.objects.filter(token_hash=token).exists())  # only the hash is kept

        inspected = self.link_post(INSPECT, token)
        self.assertEqual(inspected.data["email"], "hana@example.test")
        self.assertFalse(inspected.data["needs_sign_in_method"])
        self.assertEqual(self.link_post(CONFIRM, token).status_code, 200)
        user.refresh_from_db()
        self.assertTrue(user.is_active)
        self.assertIsNotNone(user.email_confirmed_at)
        login = APIClient().post("/api/v1/auth/login/", {"email": user.email, "password": NEW_PERSON["password"]})
        self.assertEqual(login.status_code, 200)
        self.assertEqual(self.link_post(CONFIRM, token).status_code, 400)  # single use
        for action in ("organization.access_request.approve", "account.link.create", "account.link.use"):
            self.assertTrue(AuditEvent.objects.filter(action=action).exists(), action)

    def test_a_new_link_ends_the_old_one_and_an_expired_link_does_nothing(self):
        self.ask()
        request = AccessRequest.objects.get()
        old = token_of(self.decide(request.id, "approve", role_slug="spare-parts-sales").data["link"])
        new = token_of(self.decide(request.id, "link").data["link"])
        self.assertEqual(self.link_post(INSPECT, old).status_code, 400)
        AccountLink.objects.filter(revoked_at__isnull=True).update(expires_at=timezone.now() - timedelta(minutes=1))
        self.assertEqual(self.link_post(CONFIRM, new).status_code, 400)
        self.assertFalse(User.objects.get(email="hana@example.test").is_active)
        self.assertTrue(AuditEvent.objects.filter(action="account.link.expired").exists())

    def test_reject_and_no_second_decision(self):
        self.ask()
        request = AccessRequest.objects.get()
        self.assertEqual(self.decide(request.id, "reject", note="Not hiring").status_code, 200)
        request.refresh_from_db()
        self.assertEqual(request.status, "rejected")
        self.assertEqual(self.decide(request.id, "approve", role_slug="spare-parts-sales").status_code, 409)
        self.assertFalse(Membership.objects.filter(user=request.user).exists())

    def test_only_someone_who_may_give_roles_sees_or_decides(self):
        self.ask()
        request = AccessRequest.objects.get()
        clerk = self.member("clerk@example.test", "spare-parts-manager")
        client = APIClient()
        client.force_login(clerk)
        self.assertEqual(client.get(self.requests_url()).status_code, 403)
        refused = self.decide(request.id, "approve", client=client, role_slug="spare-parts-sales")
        self.assertEqual(refused.status_code, 403)

    def test_another_organizations_administrator_cannot_reach_the_request(self):
        self.ask()
        request = AccessRequest.objects.get()
        other = User.objects.create_user(email="rival@example.test", password="Rival-pass-12345")
        client = APIClient()
        client.force_login(other)
        other_org = client.post("/api/v1/organizations/", {"name": "Rival Parts"}).data["id"]
        # Through their own organization's URL: no such request there.
        resp = self.decide(request.id, "approve", client=client, org_id=other_org, role_slug="spare-parts-sales")
        self.assertEqual(resp.status_code, 404)
        self.assertEqual(client.get(self.requests_url(other_org)).data["results"], [])
        # Through ours: not a member, so the organization does not exist for them.
        self.assertEqual(client.get(self.requests_url()).status_code, 404)
        request.refresh_from_db()
        self.assertEqual(request.status, "pending")

    # ------------------------------------------------------------------ inside the app (internal API)
    def test_the_app_lists_and_decides_for_its_administrator_only(self):
        self.ask()
        request = AccessRequest.objects.get()
        clerk = self.member("clerk2@example.test", "spare-parts-sales")
        url = f"{INTERNAL}/access-requests/"
        self.assertEqual(self.service.get(url, {"actorId": str(clerk.id)}).status_code, 403)
        listed = self.service.get(url, {"actorId": str(self.owner.id)})
        self.assertEqual(listed.status_code, 200)
        self.assertEqual([r["id"] for r in listed.data["results"]], [str(request.id)])
        body = {
            "actorId": str(self.owner.id),
            "requestId": str(request.id),
            "decision": "approve",
            "roleSlug": "spare-parts-sales",
        }
        bad = self.service.post(url, {**body, "origin": "https://evil.example"}, format="json")
        self.assertEqual(bad.status_code, 400)
        ok = self.service.post(url, {**body, "origin": "https://localhost"}, format="json")
        self.assertEqual(ok.status_code, 200)
        self.assertTrue(ok.data["link"].startswith("https://localhost/confirm#t="))

    # ------------------------------------------------------------------ the owner's phone approver
    def test_the_phone_approver_has_no_password_and_sets_its_sign_in_by_link(self):
        out = StringIO()
        call_command(
            "approver_account",
            "create",
            email="approver@example.test",
            organization=self.org_id,
            base_url="https://localhost:8443",
            stdout=out,
        )
        link = out.getvalue().strip()
        self.assertTrue(link.startswith("https://localhost:8443/confirm#t="))
        approver = User.objects.get(email="approver@example.test")
        self.assertFalse(approver.is_active)
        self.assertFalse(approver.has_usable_password())
        self.assertTrue(RoleAssignment.objects.filter(user=approver, role__slug="pay-supervisor").exists())
        token = token_of(link)
        self.assertTrue(links.inspect(token)["needs_sign_in_method"])
        # Without a password or a passkey the link does not activate it.
        self.assertEqual(self.link_post(CONFIRM, token).status_code, 400)
        # The passkey ceremony starts from the link alone (no password asked).
        options = self.link_post("/api/v1/auth/links/passkey/options/", token)
        self.assertEqual(options.status_code, 200)
        self.assertIn("challenge", options.data)
        # A made-up answer is refused and leaves the account inactive.
        bogus = self.link_post(
            "/api/v1/auth/links/passkey/verify/", token, credential={"id": "x", "response": {}}
        )
        self.assertEqual(bogus.status_code, 400)
        approver.refresh_from_db()
        self.assertFalse(approver.is_active)
        self.assertFalse(approver.passkey_only)

    def test_the_phone_approver_goes_to_the_shops_own_organization_by_itself(self):
        # The Control Center does not name the organization: the one a person made is used (never the built-in
        # catalogue's, which IntraForge's own service identity made).
        out = StringIO()
        call_command("approver_account", "create", email="phone@example.test", base_url="https://localhost", stdout=out)
        approver = User.objects.get(email="phone@example.test")
        self.assertEqual(
            list(Membership.objects.filter(user=approver).values_list("organization_id", flat=True)),
            [uuid.UUID(self.org_id)],
        )
