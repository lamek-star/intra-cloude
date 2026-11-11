"""IntraForge brokering an IntraForge Pay payment for another application (pay_bridge.py): only the
Pay of the caller's own organization, only for a person holding ifpay.checkout there, forwarded with
Pay's own service token, and status answered only for the caller's own requests. A small HTTP server
on 127.0.0.1 stands in for the Pay container and records exactly what IntraForge sent it."""

import json
import threading
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from django.test import override_settings
from rest_framework.test import APIClient, APITestCase

from accounts.models import User
from audit.models import AuditEvent
from organizations.models import Membership, Organization
from permissions.management.commands.seed_permissions import Command as SeedPermissionsCommand
from permissions.services import assign_role
from service_apps import provisioning
from service_apps.models import ServiceApp

INTERNAL = "/api/v1/internal/service-apps"
PAY1_TOKEN = "p1" * 10 + uuid.uuid4().hex
SP_TOKEN = "sp" * 10 + uuid.uuid4().hex


class FakePay(BaseHTTPRequestHandler):
    received: list = []
    answer: tuple = (201, {})

    def _reply(self):
        length = int(self.headers.get("Content-Length") or 0)
        body = json.loads(self.rfile.read(length) or b"null") if length else None
        if "/internal/" not in self.path:  # the Apps page's health probe, not the bridge
            self._send(503, {"data": {"status": "starting"}})
            return
        FakePay.received.append(
            {
                "method": self.command,
                "path": self.path,
                "token": self.headers.get("X-IntraForge-Service-Token"),
                "body": body,
            }
        )
        self._send(*FakePay.answer)

    def _send(self, code, payload):
        data = json.dumps(payload).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    do_GET = do_POST = _reply

    def log_message(self, *args):
        pass


def pay_answer(**extra):
    return {
        "id": str(uuid.uuid4()),
        "status": "pending",
        "amount": "682.50",
        "amount_minor": 68250,
        "reference": "Invoice INV-2026-000001",
        "receipt_number": None,
        "paid_at": None,
        "expires_at": "2026-10-24T10:02:00+00:00",
        "created_at": "2026-10-24T10:00:00+00:00",
        "merchant": {"id": str(uuid.uuid4()), "name": "Pilot Shop", "verified": True},
        "notice": "SIMULATED VALUE — NO CASH VALUE",
        "code": "IFPAY1.abc.def",
        "qr_svg": "data:image/svg+xml;base64,AAAA",
        **extra,
    }


def service(token):
    client = APIClient()
    client.credentials(HTTP_X_INTRAFORGE_SERVICE_TOKEN=token)
    return client


class PayBridgeBase(APITestCase):
    """Pay installations, shops, people and the fake Pay; the tests are in PayBridgeTests."""

    databases = {"default", "tenant"}

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), FakePay)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        url = f"http://127.0.0.1:{cls.server.server_address[1]}"
        cls.deployments = {
            "spare-parts": {
                "app_type": "spare_parts",
                "token": SP_TOKEN,
                "db_role": "svc_test_bridge_sp",
                "db_password": "test-password-" + uuid.uuid4().hex,
                "internal_url": "http://127.0.0.1:9",
                "launch_path": "/apps/spare-parts/",
            },
            "pay-1": {
                "app_type": "intraforge_pay",
                "token": PAY1_TOKEN,
                "db_role": "svc_test_bridge_pay",
                "db_password": "test-password-" + uuid.uuid4().hex,
                "internal_url": url,
                "launch_path": "/apps/pay-1/",
            },
        }
        cls.override = override_settings(SERVICE_APP_DEPLOYMENTS=cls.deployments)
        cls.override.enable()

    @classmethod
    def tearDownClass(cls):
        cls.override.disable()
        cls.server.shutdown()
        super().tearDownClass()

    def setUp(self):
        SeedPermissionsCommand().handle()
        FakePay.received = []
        FakePay.answer = (201, pay_answer())
        self.owner = User.objects.create_user(email="owner@example.test", password="Pw-owner-12345")
        self.other_owner = User.objects.create_user(email="other@example.test", password="Pw-owner-12345")
        self.client_a = self.signed_in(self.owner)
        self.client_b = self.signed_in(self.other_owner)
        self.org_a = self.client_a.post("/api/v1/organizations/", {"name": "Pilot Shop LLC"}).data["id"]
        self.org_b = self.client_b.post("/api/v1/organizations/", {"name": "Other Shop"}).data["id"]
        self.cashier = self.member("sara@example.test", self.org_a, "pay-cashier")
        self.supervisor = self.member("pat@example.test", self.org_a, "pay-supervisor")

    def tearDown(self):
        for app in ServiceApp.objects.all():
            provisioning.drop_schema(app.schema_name)

    def signed_in(self, user):
        client = APIClient()
        client.force_login(user)
        return client

    def member(self, email, org_id, role_slug=None):
        user = User.objects.create_user(email=email, password="Pw-member-12345")
        Membership.objects.create(user=user, organization_id=org_id, status=Membership.Status.ACTIVE)
        if role_slug:
            assign_role(user=user, role_slug=role_slug, organization=Organization.objects.get(pk=org_id))
        return user

    def install(self, client, deployment, org_id, name):
        resp = client.post(
            "/api/v1/service-apps/",
            {"deployment": deployment, "organization": org_id, "display_name": name},
            format="json",
        )
        self.assertEqual(resp.status_code, 201, resp.data)
        return resp.data["id"]

    def ask(self, actor, amount=68250, token=SP_TOKEN):
        return service(token).post(
            f"{INTERNAL}/pay/payment-requests/",
            {
                "actorId": str(actor.pk),
                "amountMinor": amount,
                "reference": "Invoice INV-2026-000001",
                "externalId": "inv-0001",
            },
            format="json",
        )


class PayBridgeTests(PayBridgeBase):
    # ------------------------------------------------------------------ the happy path

    def test_a_charge_reaches_this_shops_pay_with_pays_own_token_and_is_audited(self):
        sp = self.install(self.client_a, "spare-parts", self.org_a, "Pilot Shop")
        pay = self.install(self.client_a, "pay-1", self.org_a, "Pilot Shop")
        resp = self.ask(self.cashier)
        self.assertEqual(resp.status_code, 201, resp.data)
        self.assertEqual(resp.data["code"], "IFPAY1.abc.def")
        self.assertEqual(resp.data["pay"]["id"], pay)
        self.assertNotIn(PAY1_TOKEN, json.dumps(resp.data))
        [call] = FakePay.received
        self.assertEqual((call["method"], call["path"]), ("POST", "/apps/pay-1/internal/payment-requests"))
        self.assertEqual(call["token"], PAY1_TOKEN)
        self.assertEqual(call["body"]["source"]["app_id"], sp)
        self.assertEqual(call["body"]["actor"]["id"], str(self.cashier.pk))
        self.assertIn("ifpay.checkout", call["body"]["actor"]["capabilities"])
        self.assertEqual(call["body"]["amount_minor"], 68250)
        self.assertEqual(call["body"]["source"]["app_name"], "Spare Parts")
        event = AuditEvent.objects.get(action="service_app.pay_request")
        self.assertEqual(str(event.organization_id), self.org_a)
        self.assertEqual(event.actor_id, self.cashier.pk)
        self.assertEqual(event.context["requested_by"]["id"], sp)

    def test_status_is_asked_for_the_callers_own_requests_only(self):
        sp = self.install(self.client_a, "spare-parts", self.org_a, "Pilot Shop")
        self.install(self.client_a, "pay-1", self.org_a, "Pilot Shop")
        request_id = uuid.uuid4()
        FakePay.answer = (
            200,
            pay_answer(id=str(request_id), status="paid", receipt_number="IFP-20261024-000001"),
        )
        resp = service(SP_TOKEN).get(f"{INTERNAL}/pay/payment-requests/{request_id}/")
        self.assertEqual(resp.status_code, 200, resp.data)
        self.assertEqual((resp.data["status"], resp.data["receipt_number"]), ("paid", "IFP-20261024-000001"))
        self.assertNotIn("code", resp.data)
        [call] = FakePay.received
        self.assertEqual(
            call["path"], f"/apps/pay-1/internal/payment-requests/{request_id}?source_app_id={sp}"
        )
        FakePay.answer = (404, {"code": "not_found", "message": "No such payment request."})
        self.assertEqual(
            service(SP_TOKEN).get(f"{INTERNAL}/pay/payment-requests/{uuid.uuid4()}/").status_code, 404
        )

    # ------------------------------------------------------------------ refusals (nothing reaches Pay)

    def test_another_shops_pay_is_never_used(self):
        self.install(self.client_a, "spare-parts", self.org_a, "Pilot Shop")
        self.install(self.client_b, "pay-1", self.org_b, "Other Shop")
        resp = self.ask(self.cashier)
        self.assertEqual(resp.status_code, 404)
        self.assertEqual(FakePay.received, [])
        self.assertEqual(
            service(SP_TOKEN).get(f"{INTERNAL}/pay/payment-requests/{uuid.uuid4()}/").status_code, 404
        )
        self.assertEqual(FakePay.received, [])

    def test_a_person_without_the_cashier_capability_is_refused(self):
        self.install(self.client_a, "spare-parts", self.org_a, "Pilot Shop")
        self.install(self.client_a, "pay-1", self.org_a, "Pilot Shop")
        self.assertEqual(self.ask(self.supervisor).status_code, 403)
        outsider = self.member("x@example.test", self.org_b, "pay-cashier")
        self.assertEqual(self.ask(outsider).status_code, 403)
        Membership.objects.filter(user=self.cashier).update(status=Membership.Status.SUSPENDED)
        self.assertEqual(self.ask(self.cashier).status_code, 403)
        self.assertEqual(FakePay.received, [])
        self.assertFalse(AuditEvent.objects.filter(action="service_app.pay_request").exists())

    def test_pay_switched_off_takes_no_new_charges_but_still_answers_status(self):
        self.install(self.client_a, "spare-parts", self.org_a, "Pilot Shop")
        pay = self.install(self.client_a, "pay-1", self.org_a, "Pilot Shop")
        ServiceApp.objects.filter(pk=pay).update(enabled=False)
        self.assertEqual(self.ask(self.cashier).status_code, 409)
        self.assertEqual(FakePay.received, [])
        FakePay.answer = (200, pay_answer(status="paid"))
        self.assertEqual(
            service(SP_TOKEN).get(f"{INTERNAL}/pay/payment-requests/{uuid.uuid4()}/").status_code, 200
        )

    def test_pay_cannot_charge_through_itself_and_a_bad_token_is_refused(self):
        self.install(self.client_a, "pay-1", self.org_a, "Pilot Shop")
        self.assertEqual(self.ask(self.cashier, token=PAY1_TOKEN).status_code, 403)
        self.assertIn(self.ask(self.cashier, token="x" * 64).status_code, (401, 403))
        self.assertEqual(FakePay.received, [])

    def test_bad_input_is_refused_before_pay_is_called(self):
        self.install(self.client_a, "spare-parts", self.org_a, "Pilot Shop")
        self.install(self.client_a, "pay-1", self.org_a, "Pilot Shop")
        for amount in (0, -5, "100", True, None):
            self.assertEqual(self.ask(self.cashier, amount=amount).status_code, 400, amount)
        self.assertEqual(FakePay.received, [])

    def test_pay_not_answering_is_a_clear_503(self):
        self.install(self.client_a, "spare-parts", self.org_a, "Pilot Shop")
        self.install(self.client_a, "pay-1", self.org_a, "Pilot Shop")
        FakePay.answer = (503, {"code": "not_ready", "message": "starting"})
        self.assertEqual(self.ask(self.cashier).status_code, 503)
