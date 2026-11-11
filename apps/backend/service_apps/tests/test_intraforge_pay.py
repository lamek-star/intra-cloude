"""IntraForge Pay as a service application (ADR-0018, amended 2026-10-13): one Pay slot per shop,
Pay's own capabilities and roles, and isolation between two shops on one installation."""

import uuid

from django.test import override_settings
from rest_framework.test import APIClient, APITestCase

from accounts.models import User
from organizations.models import Membership, Organization
from permissions.catalog import ORGANIZATION_ROLE_SUMMARIES, SYSTEM_ROLES
from permissions.management.commands.seed_permissions import Command as SeedPermissionsCommand
from permissions.services import assign_role
from service_apps import provisioning
from service_apps.models import ServiceApp

PAY1_TOKEN = "p1" * 10 + uuid.uuid4().hex
PAY2_TOKEN = "p2" * 10 + uuid.uuid4().hex
SP_TOKEN = "sp" * 10 + uuid.uuid4().hex
DEPLOYMENTS = {
    "spare-parts": {
        "app_type": "spare_parts",
        "token": SP_TOKEN,
        "db_role": "svc_test_pay_sp",
        "db_password": "test-password-" + uuid.uuid4().hex,
        "internal_url": "http://127.0.0.1:9",
        "launch_path": "/apps/spare-parts/",
    },
    "pay-1": {
        "app_type": "intraforge_pay",
        "token": PAY1_TOKEN,
        "db_role": "svc_test_pay_1",
        "db_password": "test-password-" + uuid.uuid4().hex,
        "internal_url": "http://127.0.0.1:9",
        "launch_path": "/apps/pay-1/",
    },
    "pay-2": {
        "app_type": "intraforge_pay",
        "token": PAY2_TOKEN,
        "db_role": "svc_test_pay_2",
        "db_password": "test-password-" + uuid.uuid4().hex,
        "internal_url": "http://127.0.0.1:9",
        "launch_path": "/apps/pay-2/",
    },
}
INTERNAL = "/api/v1/internal/service-apps"
CASHIER = {"ifpay.view", "ifpay.checkout"}


def service(token):
    client = APIClient()
    client.credentials(HTTP_X_INTRAFORGE_SERVICE_TOKEN=token)
    return client


@override_settings(SERVICE_APP_DEPLOYMENTS=DEPLOYMENTS)
class IntraForgePayTests(APITestCase):
    databases = {"default", "tenant"}

    def setUp(self):
        SeedPermissionsCommand().handle()
        self.owner_a = User.objects.create_user(email="lamek@example.test", password="Pw-owner-12345")
        self.owner_b = User.objects.create_user(email="amina@example.test", password="Pw-owner-12345")
        self.client_a = self.signed_in(self.owner_a)
        self.client_b = self.signed_in(self.owner_b)
        self.org_a = self.client_a.post("/api/v1/organizations/", {"name": "Micheal Spare Part LLC"}).data[
            "id"
        ]
        self.org_b = self.client_b.post("/api/v1/organizations/", {"name": "Amina Mobile Shop"}).data["id"]

    def tearDown(self):
        for app in ServiceApp.objects.all():
            provisioning.drop_schema(app.schema_name)

    def signed_in(self, user):
        client = APIClient()
        client.force_login(user)
        return client

    def install(self, client, deployment, org_id, name, **extra):
        return client.post(
            "/api/v1/service-apps/",
            {"deployment": deployment, "organization": org_id, "display_name": name, **extra},
            format="json",
        )

    def member(self, email, org_id, role_slug=None):
        user = User.objects.create_user(email=email, password="Pw-member-12345")
        Membership.objects.create(user=user, organization_id=org_id, status=Membership.Status.ACTIVE)
        if role_slug:
            assign_role(user=user, role_slug=role_slug, organization=Organization.objects.get(pk=org_id))
        return user

    def launch(self, user, app_id):
        client = self.signed_in(user)
        resp = client.post(f"/api/v1/service-apps/{app_id}/launch/")
        return resp, client.cookies

    # ------------------------------------------------------------------ catalog

    def test_pay_roles_and_capabilities_exist_and_are_offered_on_the_members_page(self):
        self.assertEqual(set(SYSTEM_ROLES["pay-cashier"][1]), CASHIER)
        self.assertNotIn("ifpay.checkout", SYSTEM_ROLES["pay-supervisor"][1])
        self.assertIn("ifpay.allocations.approve", SYSTEM_ROLES["pay-supervisor"][1])
        self.assertTrue(all(c.startswith("ifpay.") for c in SYSTEM_ROLES["pay-manager"][1]))
        self.assertTrue(
            set(SYSTEM_ROLES["pay-manager"][1]) <= set(SYSTEM_ROLES["organization-administrator"][1])
        )
        for slug in ("pay-manager", "pay-supervisor", "pay-cashier"):
            self.assertIn(slug, ORGANIZATION_ROLE_SUMMARIES)
        roles = self.client_a.get(f"/api/v1/organizations/{self.org_a}/roles/")
        if roles.status_code == 200:
            self.assertTrue({"pay-cashier", "pay-supervisor"} <= {r["slug"] for r in roles.data["roles"]})

    # ------------------------------------------------------------------ install

    def test_every_free_pay_slot_is_offered_and_installs_with_only_a_shop_name(self):
        available = {a["deployment"]: a for a in self.client_a.get("/api/v1/service-apps/").data["available"]}
        self.assertEqual(available["pay-1"]["product_name"], "IntraForge Pay")
        self.assertIn("pay-2", available)
        refused = self.install(self.client_a, "pay-1", self.org_a, "Micheal Pay", config={"currency": "AED"})
        self.assertEqual(refused.status_code, 400)
        resp = self.install(self.client_a, "pay-1", self.org_a, "Micheal Spare Part LLC")
        self.assertEqual(resp.status_code, 201, resp.data)
        app = ServiceApp.objects.get(pk=resp.data["id"])
        self.assertEqual(app.app_type, "intraforge_pay")
        self.assertEqual(app.config, {"shopName": "Micheal Spare Part LLC"})
        self.assertEqual(resp.data["launch"], {"path": "/apps/pay-1/", "requires": "ifpay.view"})
        self.assertTrue(provisioning.schema_exists(app.schema_name))
        self.assertTrue(app.schema_name.startswith("svc_intrafor_"))
        # The slot is taken now; the second shop gets the next one.
        available = {a["deployment"] for a in self.client_b.get("/api/v1/service-apps/").data["available"]}
        self.assertNotIn("pay-1", available)
        self.assertIn("pay-2", available)
        self.assertEqual(self.install(self.client_b, "pay-1", self.org_b, "Amina Pay").status_code, 409)
        self.assertEqual(
            self.install(self.client_b, "pay-2", self.org_b, "Amina Mobile Shop").status_code, 201
        )

    def test_self_reports_the_pay_instance_and_its_capabilities(self):
        self.install(self.client_a, "pay-1", self.org_a, "Micheal Spare Part LLC")
        me = service(PAY1_TOKEN).get(f"{INTERNAL}/self/").data
        self.assertTrue(me["installed"])
        self.assertEqual(me["app_type"], "intraforge_pay")
        self.assertEqual(me["launch_path"], "/apps/pay-1/")
        self.assertEqual(me["app"]["organization"]["name"], "Micheal Spare Part LLC")
        self.assertEqual(me["config"], {"shopName": "Micheal Spare Part LLC"})
        self.assertTrue(set(me["capabilities"]) >= CASHIER)
        self.assertFalse(any(c.startswith("spareparts.") for c in me["capabilities"]))
        # An empty slot is "not installed", not someone else's instance.
        self.assertFalse(service(PAY2_TOKEN).get(f"{INTERNAL}/self/").data["installed"])

    # ------------------------------------------------------------------ identity

    def test_a_pay_cashier_opens_pay_with_exactly_the_cashier_capabilities(self):
        app_id = self.install(self.client_a, "pay-1", self.org_a, "Micheal Spare Part LLC").data["id"]
        sara = self.member("sara@example.test", self.org_a, "pay-cashier")
        resp, cookies = self.launch(sara, app_id)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data, {"url": "/apps/pay-1/"})
        cookie = cookies["ifapp_pay_1"]
        self.assertEqual(cookie["path"], "/apps/pay-1/")
        self.assertTrue(cookie["httponly"])
        result = service(PAY1_TOKEN).post(
            f"{INTERNAL}/sessions/introspect/", {"token": cookie.value}, format="json"
        )
        self.assertEqual(result.status_code, 200)
        self.assertEqual(set(result.data["capabilities"]), CASHIER)
        self.assertEqual(result.data["user"]["email"], "sara@example.test")
        # The organization owner holds every Pay capability through Organization Administrator.
        resp, cookies = self.launch(self.owner_a, app_id)
        caps = (
            service(PAY1_TOKEN)
            .post(f"{INTERNAL}/sessions/introspect/", {"token": cookies["ifapp_pay_1"].value}, format="json")
            .data["capabilities"]
        )
        self.assertIn("ifpay.allocations.approve", caps)

    def test_spare_parts_staff_and_members_without_a_pay_role_cannot_open_pay(self):
        app_id = self.install(self.client_a, "pay-1", self.org_a, "Micheal Spare Part LLC").data["id"]
        seller = self.member("seller@example.test", self.org_a, "spare-parts-sales")
        plain = self.member("plain@example.test", self.org_a)
        for user in (seller, plain):
            resp, _ = self.launch(user, app_id)
            self.assertIn(resp.status_code, (403, 404))

    # ------------------------------------------------------------------ isolation between shops

    def test_two_shops_on_one_installation_cannot_reach_each_others_pay(self):
        app_a = self.install(self.client_a, "pay-1", self.org_a, "Micheal Spare Part LLC").data["id"]
        app_b = self.install(self.client_b, "pay-2", self.org_b, "Amina Mobile Shop").data["id"]
        cashier_a = self.member("cashier-a@example.test", self.org_a, "pay-cashier")
        # Shop B's owner and shop A's cashier see only their own shop's Pay.
        self.assertEqual(self.signed_in(self.owner_b).get(f"/api/v1/service-apps/{app_a}/").status_code, 404)
        self.assertEqual(self.signed_in(cashier_a).get(f"/api/v1/service-apps/{app_b}/").status_code, 404)
        self.assertEqual(self.launch(cashier_a, app_b)[0].status_code, 404)
        visible = {a["id"] for a in self.signed_in(self.owner_b).get("/api/v1/service-apps/").data["results"]}
        self.assertEqual(visible, {app_b})
        # A session opened for shop A's Pay is nothing to shop B's Pay service, and the reverse.
        _, cookies = self.launch(cashier_a, app_a)
        token_a = cookies["ifapp_pay_1"].value
        self.assertEqual(
            service(PAY2_TOKEN)
            .post(f"{INTERNAL}/sessions/introspect/", {"token": token_a}, format="json")
            .status_code,
            401,
        )
        self.assertEqual(
            service(PAY1_TOKEN)
            .post(f"{INTERNAL}/sessions/introspect/", {"token": token_a}, format="json")
            .status_code,
            200,
        )
        # Each service's own view of itself names only its own organization.
        self.assertEqual(
            service(PAY2_TOKEN).get(f"{INTERNAL}/self/").data["app"]["organization"]["id"], self.org_b
        )
        # A Pay token is not the Spare Parts token: it cannot act as that deployment.
        sp = service(PAY1_TOKEN).get(f"{INTERNAL}/self/").data
        self.assertEqual(sp["deployment"], "pay-1")

    def test_a_pay_cashier_in_one_shop_holds_nothing_in_another(self):
        self.install(self.client_a, "pay-1", self.org_a, "Micheal Spare Part LLC")
        app_b = self.install(self.client_b, "pay-2", self.org_b, "Amina Mobile Shop").data["id"]
        sara = self.member("sara@example.test", self.org_a, "pay-cashier")
        # Even as a plain member of shop B, the cashier role from shop A gives nothing there.
        Membership.objects.create(user=sara, organization_id=self.org_b, status=Membership.Status.ACTIVE)
        resp, _ = self.launch(sara, app_b)
        self.assertIn(resp.status_code, (403, 404))

    def test_pay_audit_events_are_recorded_under_the_pay_prefix_in_the_right_organization(self):
        self.install(self.client_a, "pay-1", self.org_a, "Micheal Spare Part LLC")
        event_id = "pay-" + uuid.uuid4().hex[:20]
        resp = service(PAY1_TOKEN).post(
            f"{INTERNAL}/audit-events/",
            {
                "events": [
                    {
                        "id": event_id,
                        "action": "payment.complete",
                        "entityType": "receipt",
                        "entityId": "R-000001",
                        "actorId": str(self.owner_a.pk),
                        "summary": "Payment 12.00 IF Credits",
                    }
                ]
            },
            format="json",
        )
        self.assertEqual(resp.data["accepted"], [event_id])
        from audit.models import AuditEvent

        event = AuditEvent.objects.get(action="intraforgepay.payment.complete")
        self.assertEqual(str(event.organization_id), self.org_a)

    def test_a_relayed_refusal_is_recorded_as_denied_and_an_unknown_result_is_refused(self):
        self.install(self.client_a, "pay-1", self.org_a, "Micheal Spare Part LLC")
        from audit.models import AuditEvent

        def relay(result):
            event = {
                "id": "pay-" + uuid.uuid4().hex[:20],
                "action": "access.denied",
                "entityType": "endpoint",
            }
            if result is not None:
                event["result"] = result
            return service(PAY1_TOKEN).post(f"{INTERNAL}/audit-events/", {"events": [event]}, format="json")

        self.assertEqual(relay("denied").status_code, 200)
        self.assertEqual(relay("error").status_code, 200)
        # A service that predates the field is unchanged: no result means success.
        self.assertEqual(relay(None).status_code, 200)
        results = sorted(
            AuditEvent.objects.filter(action="intraforgepay.access.denied").values_list("result", flat=True)
        )
        self.assertEqual(results, ["denied", "error", "success"])
        self.assertEqual(relay("ok").status_code, 400)
        self.assertEqual(AuditEvent.objects.filter(action="intraforgepay.access.denied").count(), 3)
