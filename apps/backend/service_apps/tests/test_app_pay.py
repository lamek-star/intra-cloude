"""IntraForge Pay for applications (app_pay.py, ADR-0020): an Application credential reaches its own
organization's Pay through the Pay bridge, only once the owner granted it ifpay.checkout on that Pay; never
another shop's Pay, never with a browser session, and status only for its own requests."""

import uuid

from rest_framework.test import APIClient

from applications.models import Application
from applications.services import issue_credential, register_application
from audit.models import AuditEvent
from permissions.services import grant_resource_permission
from service_apps.tests.test_pay_bridge import PAY1_TOKEN, FakePay, PayBridgeBase, pay_answer

URL = "/api/v1/pay/payment-requests/"


class AppPayTests(PayBridgeBase):
    def app_client(self, org_id, name="Website: Shop"):
        from organizations.models import Organization

        application = register_application(
            organization=Organization.objects.get(pk=org_id), name=name, description="", owner=self.owner
        )
        _, token = issue_credential(service_account=application.service_account, actor=self.owner)
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        return application, client

    def allow_checkout(self, application: Application, pay_id):
        grant_resource_permission(
            user=application.service_account.identity_user,
            permission_code="ifpay.checkout",
            organization_id=application.organization_id,
            resource_type="service_app",
            resource_id=pay_id,
            granted_by=self.owner,
        )

    def charge(self, client, amount=2500):
        return client.post(
            URL, {"amountMinor": amount, "reference": "Web order 42", "externalId": "order-42"}, format="json"
        )

    def test_an_app_with_checkout_on_its_shops_pay_gets_a_qr(self):
        pay = self.install(self.client_a, "pay-1", self.org_a, "Pilot Shop")
        application, client = self.app_client(self.org_a)
        self.allow_checkout(application, pay)
        resp = self.charge(client)
        self.assertEqual(resp.status_code, 201, resp.data)
        self.assertEqual(resp.data["code"], "IFPAY1.abc.def")
        self.assertNotIn(PAY1_TOKEN, str(resp.data))
        [call] = FakePay.received
        self.assertEqual(call["token"], PAY1_TOKEN)
        self.assertEqual(call["body"]["source"]["app_id"], str(application.id))
        self.assertEqual(call["body"]["source"]["app_name"], "Website: Shop")
        self.assertEqual(call["body"]["actor"]["id"], str(application.service_account.identity_user.pk))
        event = AuditEvent.objects.get(action="application.pay_request")
        self.assertEqual(str(event.organization_id), self.org_a)
        self.assertEqual(event.context["requested_by"]["id"], str(application.id))

    def test_without_the_grant_the_app_is_refused(self):
        self.install(self.client_a, "pay-1", self.org_a, "Pilot Shop")
        _, client = self.app_client(self.org_a)
        resp = self.charge(client)
        self.assertEqual(resp.status_code, 403)
        self.assertIn("allow IntraForge Pay", str(resp.data))
        self.assertEqual(FakePay.received, [])

    def test_a_grant_on_another_shops_pay_gives_nothing(self):
        pay_a = self.install(self.client_a, "pay-1", self.org_a, "Pilot Shop")
        application_b, client_b = self.app_client(self.org_b, "Website: Other")
        # Granting org B's app checkout on org A's Pay: the grant is recorded under org B, Pay belongs to A.
        self.allow_checkout(application_b, pay_a)
        resp = self.charge(client_b)
        self.assertEqual(resp.status_code, 404)  # org B has no Pay of its own
        self.assertEqual(FakePay.received, [])

    def test_a_browser_session_cannot_use_it(self):
        self.install(self.client_a, "pay-1", self.org_a, "Pilot Shop")
        resp = self.charge(self.client_a)
        self.assertEqual(resp.status_code, 403)
        self.assertIn("application's own credential", str(resp.data))

    def test_status_is_asked_for_the_apps_own_requests(self):
        pay = self.install(self.client_a, "pay-1", self.org_a, "Pilot Shop")
        application, client = self.app_client(self.org_a)
        self.allow_checkout(application, pay)
        request_id = uuid.uuid4()
        FakePay.answer = (200, pay_answer(id=str(request_id), status="paid"))
        resp = client.get(f"{URL}{request_id}/")
        self.assertEqual(resp.status_code, 200, resp.data)
        self.assertEqual(resp.data["status"], "paid")
        self.assertNotIn("code", resp.data)
        self.assertIn(f"source_app_id={application.id}", FakePay.received[-1]["path"])

    def test_revoking_the_grant_takes_pay_away_and_only_the_owner_can(self):
        pay = self.install(self.client_a, "pay-1", self.org_a, "Pilot Shop")
        application, client = self.app_client(self.org_a)
        self.allow_checkout(application, pay)
        grant = application.service_account.identity_user.resource_grants.get()
        url = f"/api/v1/applications/{application.id}/resource-grants/{grant.id}/"
        # Another organization's administrator cannot even see the application.
        self.assertEqual(self.client_b.delete(url).status_code, 404)
        self.assertEqual(self.client_a.delete(url).status_code, 204)
        self.assertEqual(self.charge(client).status_code, 403)
        self.assertTrue(AuditEvent.objects.filter(action="permissions.resource_grant.revoke").exists())
