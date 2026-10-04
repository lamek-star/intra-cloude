"""Phase 10 -- environment-bound service accounts and reliable webhooks
(docs/implementation/APP_PLATFORM_ROADMAP.md,
docs/implementation/APP_PLATFORM_PHASE10.md). Two real, previously-open
gaps, covered against a real provisioned instance and real HTTP:

1. **Environment-bound service accounts.** Before this phase,
   app_platform's bearer-token-reachable record/attachment endpoints had
   no `environments.check_environment_scope` check at all -- the one
   place in this codebase's bearer-token surface that gap existed.
   `EnvironmentScopeTests` proves a Development-scoped credential cannot
   reach a Production-bound instance's records (and vice versa), mirrors
   `environments/tests/test_environments.py::
   EnvironmentCredentialAndIsolationTests`'s own scenario and structure.
2. **Reliable webhooks.** `app_platform/webhooks.py` dispatches record/
   workflow events to `environments.EnvironmentWebhook` subscribers.
   `DispatchTests`/`WorkflowWebhookTests` prove subscription filtering
   (event_types, enabled, environment binding) and a real, HMAC-signed
   HTTP POST reaching a real local server -- the same
   `http.server.HTTPServer`-in-a-thread pattern test_workflow_transitions.
   py's own `NotificationDeliveryTests` already established for the
   older, unsigned `notify_url` mechanism."""

import hashlib
import hmac
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

from django.core.management import call_command
from django.db import connections
from django.test import TransactionTestCase
from psycopg import sql
from rest_framework.test import APIClient

import applications.services as application_services
import environments.services as environment_services
from accounts.models import User
from app_platform import instances, provisioning, templates, workflows
from app_platform.models import WebhookDelivery
from app_platform.runtime_plan import plan_runtime
from app_platform.tests.test_foundation import project_for, sample
from app_platform.tests.test_workflows import workflow_sample
from organizations.services import create_organization
from permissions.services import grant_resource_permission


def _free_port_server(handler):
    server = HTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread


def _capturing_handler(received):
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):  # noqa: N802 - BaseHTTPRequestHandler's own naming convention
            length = int(self.headers["Content-Length"])
            body = self.rfile.read(length)
            # self.headers (email.message.Message) does case-insensitive
            # lookup by design -- extract what the test needs here rather
            # than `dict(self.headers)`, whose keys keep whatever exact
            # case the sender used (urllib.request.Request's own
            # str.capitalize() header-name normalization) and would make
            # an assertion's own key casing fragile for no reason.
            received.append({
                "signature": self.headers.get("X-IntraForge-Signature"),
                "event": self.headers.get("X-IntraForge-Event"),
                "body": body,
            })
            self.send_response(200)
            self.end_headers()

        def log_message(self, *args):
            pass  # Quiet -- the test's own assertions are the signal.

    return Handler


class WebhookTestBase(TransactionTestCase):
    databases = {"default", "tenant"}

    def setUp(self):
        call_command("seed_permissions", verbosity=0)
        self.actor = User.objects.create_user(email="webhook-owner@example.com")
        self.org = create_organization(name="Webhook Org", created_by=self.actor)
        self.project = project_for(self.actor, self.org)
        self.application = application_services.register_application(
            organization=self.org, name="Integration", description="", owner=self.actor
        )
        self.environment = environment_services.create_environment(
            application=self.application, name="Development", environment_type="development",
            actor=self.actor,
        )

        template = templates.create_template(self.actor, self.org, {"label": "App", "draft": sample()})
        version = templates.publish_template(self.actor, template)
        self.instance = instances.install(
            self.actor, self.project, {"label": "Runtime", "template_version": str(version.id)}
        )
        self.item = self.instance.models.get(key="item")
        self.name_field = self.item.fields.get(key="name")

        self.plan = plan_runtime(self.actor, self.instance)
        provisioning.reserve(self.actor, self.instance, self.plan["fingerprint"])
        self.receipt = provisioning.execute(self.instance.id, self.actor)
        environment_services.bind_database(
            environment=self.environment, tenant_database=self.receipt.database, actor=self.actor
        )

        self.client = APIClient()
        self.client.force_authenticate(self.actor)

    def tearDown(self):
        with connections["tenant"].cursor() as cursor:
            cursor.execute(
                sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE").format(sql.Identifier(self.plan["schema_name"]))
            )
        super().tearDown()

    def _create_item(self, name="Widget"):
        response = self.client.post(
            f"/api/v1/app-models/{self.item.id}/records/", {str(self.name_field.id): name}, format="json"
        )
        self.assertEqual(response.status_code, 201, response.data)
        return response.data

    def _create_webhook(self, url, event_types=None, enabled=True):
        webhook, signing_secret = environment_services.create_webhook(
            environment=self.environment, url=url, event_types=event_types or [],
            actor=self.actor, enabled=enabled,
        )
        return webhook, signing_secret

    def _start_receiver(self):
        """A real, always-200 local server -- used wherever a test wants
        a delivery to genuinely succeed (not merely be *attempted*
        against nothing listening). CELERY_TASK_ALWAYS_EAGER runs the
        delivery task synchronously inside the same request that
        dispatches it, so a target that actively refuses the connection
        (e.g. a dead port) makes Celery's own retry/propagate machinery
        surface as a 500 from that request in tests -- a real
        interaction the production async-worker path never has (the
        dispatching HTTP request already returned before a worker ever
        dials out for real), not a bug in the dispatch code itself."""
        received = []
        server, thread = _free_port_server(_capturing_handler(received))
        self.addCleanup(thread.join, timeout=5)
        self.addCleanup(server.shutdown)
        return f"http://127.0.0.1:{server.server_address[1]}/hook", received


class DispatchTests(WebhookTestBase):
    def test_a_subscribed_event_type_creates_a_delivery(self):
        url, _received = self._start_receiver()
        self._create_webhook(url, event_types=["app_instance.record.create"])
        self._create_item()
        self.assertEqual(WebhookDelivery.objects.filter(event_type="app_instance.record.create").count(), 1)

    def test_an_unsubscribed_event_type_creates_no_delivery(self):
        self._create_webhook("http://127.0.0.1:1/hook", event_types=["app_instance.record.delete"])
        self._create_item()
        self.assertEqual(WebhookDelivery.objects.count(), 0)

    def test_empty_event_types_subscribes_to_everything(self):
        url, _received = self._start_receiver()
        self._create_webhook(url, event_types=[])
        record = self._create_item()
        self.client.patch(
            f"/api/v1/app-models/{self.item.id}/records/{record['id']}/",
            {str(self.name_field.id): "Renamed"}, format="json",
        )
        self.client.delete(f"/api/v1/app-models/{self.item.id}/records/{record['id']}/")
        event_types = set(WebhookDelivery.objects.values_list("event_type", flat=True))
        self.assertEqual(
            event_types,
            {"app_instance.record.create", "app_instance.record.update", "app_instance.record.delete"},
        )

    def test_a_disabled_webhook_receives_nothing(self):
        self._create_webhook("http://127.0.0.1:1/hook", enabled=False)
        self._create_item()
        self.assertEqual(WebhookDelivery.objects.count(), 0)

    def test_an_instance_with_no_environment_binding_dispatches_nothing(self):
        environment_services.unbind_database(environment=self.environment, actor=self.actor)
        self._create_webhook("http://127.0.0.1:1/hook")
        self._create_item()
        self.assertEqual(WebhookDelivery.objects.count(), 0)

    def test_a_webhook_on_a_different_environment_receives_nothing(self):
        other_env = environment_services.create_environment(
            application=self.application, name="Staging", environment_type="staging", actor=self.actor
        )
        environment_services.create_webhook(
            environment=other_env, url="http://127.0.0.1:1/hook", event_types=[], actor=self.actor
        )
        self._create_item()
        self.assertEqual(WebhookDelivery.objects.count(), 0)

    def test_delivery_is_genuinely_hmac_signed_and_reaches_a_real_http_server(self):
        received = []
        server, thread = _free_port_server(_capturing_handler(received))
        try:
            port = server.server_address[1]
            webhook, signing_secret = self._create_webhook(f"http://127.0.0.1:{port}/hook", event_types=[])
            record = self._create_item(name="Signed Widget")

            self.assertEqual(len(received), 1)
            body = received[0]["body"]
            expected_signature = "sha256=" + hmac.new(
                signing_secret.encode(), body, hashlib.sha256
            ).hexdigest()
            self.assertEqual(received[0]["signature"], expected_signature)
            self.assertEqual(received[0]["event"], "app_instance.record.create")

            payload = json.loads(body)
            self.assertEqual(payload["event_type"], "app_instance.record.create")
            self.assertEqual(payload["instance_id"], str(self.instance.id))
            self.assertEqual(payload["record_id"], str(record["id"]))
            self.assertNotIn(str(self.name_field.id), payload)  # thin payload -- no field values

            delivery = WebhookDelivery.objects.get(webhook=webhook)
            self.assertIsNotNone(delivery.delivered_at)
        finally:
            server.shutdown()
            thread.join(timeout=5)

    def test_disabling_a_webhook_between_dispatch_and_delivery_is_not_sent(self):
        # Delivery happens synchronously (in-process, Celery-eager) in
        # this test env, so this proves the task's own re-check, not a
        # timing race: dispatch first with a real receiver listening,
        # then the eager task runs against the *current* row state.
        received = []
        server, thread = _free_port_server(_capturing_handler(received))
        try:
            port = server.server_address[1]
            webhook, _secret = self._create_webhook(f"http://127.0.0.1:{port}/hook", event_types=[])
            environment_services.update_webhook(webhook=webhook, actor=self.actor, enabled=False)
            self._create_item()
            self.assertEqual(len(received), 0)
        finally:
            server.shutdown()
            thread.join(timeout=5)


class WorkflowWebhookTests(TransactionTestCase):
    databases = {"default", "tenant"}

    def setUp(self):
        call_command("seed_permissions", verbosity=0)
        self.actor = User.objects.create_user(email="webhook-wf-owner@example.com")
        self.org = create_organization(name="Webhook WF Org", created_by=self.actor)
        self.project = project_for(self.actor, self.org)
        self.application = application_services.register_application(
            organization=self.org, name="Integration", description="", owner=self.actor
        )
        self.environment = environment_services.create_environment(
            application=self.application, name="Development", environment_type="development",
            actor=self.actor,
        )
        template = templates.create_template(
            self.actor, self.org, {"label": "App", "draft": workflow_sample()}
        )
        version = templates.publish_template(self.actor, template)
        self.instance = instances.install(
            self.actor, self.project, {"label": "Runtime", "template_version": str(version.id)}
        )
        self.ticket = self.instance.models.get(key="ticket")
        self.status_field = self.ticket.fields.get(key="status")
        self.workflow = self.ticket.workflows.get(key="lifecycle")
        self.submit = self.workflow.transitions.get(key="submit")

        self.plan = plan_runtime(self.actor, self.instance)
        provisioning.reserve(self.actor, self.instance, self.plan["fingerprint"])
        self.receipt = provisioning.execute(self.instance.id, self.actor)
        environment_services.bind_database(
            environment=self.environment, tenant_database=self.receipt.database, actor=self.actor
        )

        self.client = APIClient()
        self.client.force_authenticate(self.actor)
        created = self.client.post(
            f"/api/v1/app-models/{self.ticket.id}/records/",
            {str(self.status_field.id): "draft"}, format="json",
        )
        self.record_id = created.data["id"]

    def tearDown(self):
        with connections["tenant"].cursor() as cursor:
            cursor.execute(
                sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE").format(sql.Identifier(self.plan["schema_name"]))
            )
        super().tearDown()

    def test_a_transition_dispatches_a_webhook_event_independent_of_notify_url(self):
        received = []
        server, thread = _free_port_server(_capturing_handler(received))
        try:
            port = server.server_address[1]
            environment_services.create_webhook(
                environment=self.environment, url=f"http://127.0.0.1:{port}/hook",
                event_types=["app_instance.workflow.transition"], actor=self.actor,
            )
            # self.submit has no notify_url at all -- proves the two
            # mechanisms are independent, not one gated by the other.
            self.assertEqual(self.submit.notify_url, "")
            workflows.apply_transition(self.actor, self.submit, self.record_id)

            self.assertEqual(len(received), 1)
            payload = json.loads(received[0]["body"])
            self.assertEqual(payload["event_type"], "app_instance.workflow.transition")
            self.assertEqual(payload["record_id"], str(self.record_id))
            self.assertEqual(payload["to_state"], "open")
        finally:
            server.shutdown()
            thread.join(timeout=5)


class EnvironmentScopeTests(TransactionTestCase):
    """Real bearer-token requests as two different ApplicationCredentials,
    never calling records.py directly -- the same bar test_upgrades.py/
    the Phase 8 template suites already hold themselves to."""

    databases = {"default", "tenant"}

    def setUp(self):
        call_command("seed_permissions", verbosity=0)
        self.actor = User.objects.create_user(email="scope-owner@example.com")
        self.org = create_organization(name="Scope Org", created_by=self.actor)
        self.project = project_for(self.actor, self.org)
        self.application = application_services.register_application(
            organization=self.org, name="Integration", description="", owner=self.actor
        )
        self.dev_env = environment_services.create_environment(
            application=self.application, name="Development", environment_type="development",
            actor=self.actor,
        )
        self.prod_env = environment_services.create_environment(
            application=self.application, name="Production", environment_type="production",
            actor=self.actor,
        )

        template = templates.create_template(self.actor, self.org, {"label": "App", "draft": sample()})
        version = templates.publish_template(self.actor, template)

        def _provision(label):
            instance = instances.install(
                self.actor, self.project, {"label": label, "template_version": str(version.id)}
            )
            plan = plan_runtime(self.actor, instance)
            provisioning.reserve(self.actor, instance, plan["fingerprint"])
            receipt = provisioning.execute(instance.id, self.actor)
            return instance, plan, receipt

        self.dev_instance, self.dev_plan, self.dev_receipt = _provision("Dev Runtime")
        self.prod_instance, self.prod_plan, self.prod_receipt = _provision("Prod Runtime")
        environment_services.bind_database(
            environment=self.dev_env, tenant_database=self.dev_receipt.database, actor=self.actor
        )
        environment_services.bind_database(
            environment=self.prod_env, tenant_database=self.prod_receipt.database, actor=self.actor
        )

        service_account = self.application.service_account
        identity_user = service_account.identity_user
        for receipt in (self.dev_receipt, self.prod_receipt):
            for perm in ("database.read", "database.write"):
                grant_resource_permission(
                    user=identity_user, permission_code=perm, organization_id=self.org.id,
                    resource_type="databases.tenant_database", resource_id=receipt.database_id,
                    granted_by=self.actor,
                )

        self.dev_credential, self.dev_token = application_services.issue_credential(
            service_account=service_account, actor=self.actor, environment=self.dev_env
        )
        self.prod_credential, self.prod_token = application_services.issue_credential(
            service_account=service_account, actor=self.actor, environment=self.prod_env
        )
        self.unscoped_credential, self.unscoped_token = application_services.issue_credential(
            service_account=service_account, actor=self.actor
        )

    def tearDown(self):
        with connections["tenant"].cursor() as cursor:
            for plan in (self.dev_plan, self.prod_plan):
                cursor.execute(
                    sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE").format(sql.Identifier(plan["schema_name"]))
                )
        super().tearDown()

    def _auth(self, token):
        return {"HTTP_AUTHORIZATION": f"Bearer {token}"}

    def _records_url(self, instance):
        model = instance.models.get(key="item")
        return f"/api/v1/app-models/{model.id}/records/"

    def test_development_credential_can_access_development_instance(self):
        client = APIClient()
        resp = client.get(self._records_url(self.dev_instance), **self._auth(self.dev_token))
        self.assertEqual(resp.status_code, 200, resp.data)

    def test_development_credential_cannot_access_production_instance(self):
        client = APIClient()
        resp = client.get(self._records_url(self.prod_instance), **self._auth(self.dev_token))
        self.assertEqual(resp.status_code, 403)
        write_resp = client.post(
            self._records_url(self.prod_instance), {}, format="json", **self._auth(self.dev_token)
        )
        self.assertEqual(write_resp.status_code, 403)

    def test_production_credential_cannot_access_development_instance(self):
        client = APIClient()
        resp = client.get(self._records_url(self.dev_instance), **self._auth(self.prod_token))
        self.assertEqual(resp.status_code, 403)

    def test_unscoped_credential_reaches_both(self):
        client = APIClient()
        dev_resp = client.get(self._records_url(self.dev_instance), **self._auth(self.unscoped_token))
        prod_resp = client.get(self._records_url(self.prod_instance), **self._auth(self.unscoped_token))
        self.assertEqual(dev_resp.status_code, 200, dev_resp.data)
        self.assertEqual(prod_resp.status_code, 200, prod_resp.data)

    def test_environment_scoped_credential_cannot_reach_an_unbound_instance(self):
        third = instances.install(
            self.actor, self.project,
            {"label": "Unbound Runtime", "template_version": str(self.dev_instance.source_version_id)},
        )
        plan = plan_runtime(self.actor, third)
        provisioning.reserve(self.actor, third, plan["fingerprint"])
        receipt = provisioning.execute(third.id, self.actor)
        grant_resource_permission(
            user=self.application.service_account.identity_user, permission_code="database.read",
            organization_id=self.org.id, resource_type="databases.tenant_database",
            resource_id=receipt.database_id, granted_by=self.actor,
        )
        try:
            client = APIClient()
            resp = client.get(self._records_url(third), **self._auth(self.dev_token))
            self.assertEqual(resp.status_code, 403)
        finally:
            with connections["tenant"].cursor() as cursor:
                cursor.execute(
                    sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE").format(sql.Identifier(plan["schema_name"]))
                )
