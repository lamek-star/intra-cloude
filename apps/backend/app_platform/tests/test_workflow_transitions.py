"""Phase 5 -- workflow transition application
(docs/implementation/APP_PLATFORM_PHASE5.md). Covers workflows.py::
apply_transition against a real, provisioned Postgres runtime: successful
application (state + field actions in one write), a from_state mismatch
rejected as a clean conflict rather than a corrupted write, a
requires_approval gate, idempotency-key replay, and -- the requirement
that matters most -- two different, mutually-exclusive transitions racing
concurrently on the same record resolve to exactly one winner via a real
database.

Reuses composite_sample()'s pre-generated-id pattern (via
test_workflows.py's own workflow_sample()) and test_composite_constraints.
py's ThreadPoolExecutor concurrency-test structure."""

import json
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler, HTTPServer

from django.core.management import call_command
from django.db import close_old_connections, connections
from django.test import TransactionTestCase
from psycopg import sql
from rest_framework.exceptions import PermissionDenied, ValidationError

from accounts.models import User
from app_platform import instances, provisioning, templates, workflows
from app_platform.models import WorkflowNotificationDelivery
from app_platform.runtime_plan import plan_runtime
from app_platform.tests.test_foundation import project_for
from app_platform.tests.test_workflows import workflow_sample
from app_platform.workflows import TransitionConflict
from organizations.models import Membership
from organizations.services import create_organization
from permissions.services import assign_role, grant_resource_permission


class WorkflowTransitionTestBase(TransactionTestCase):
    databases = {"default", "tenant"}

    def setUp(self):
        call_command("seed_permissions", verbosity=0)
        self.actor = User.objects.create_user(email="wf-apply@example.com")
        self.org = create_organization(name="Workflow Apply Org", created_by=self.actor)
        self.project = project_for(self.actor, self.org)
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
        self.close = self.workflow.transitions.get(key="close")

        plan = plan_runtime(self.actor, self.instance)
        self.schema_name = plan["schema_name"]
        provisioning.reserve(self.actor, self.instance, plan["fingerprint"])
        self.receipt = provisioning.execute(self.instance.id, self.actor)

        from rest_framework.test import APIClient

        self.client = APIClient()
        self.client.force_authenticate(self.actor)
        created = self.client.post(
            f"/api/v1/app-models/{self.ticket.id}/records/",
            {str(self.status_field.id): "draft"},
            format="json",
        )
        assert created.status_code == 201, created.data
        self.record_id = created.data["id"]

    def tearDown(self):
        with connections["tenant"].cursor() as cursor:
            cursor.execute(
                sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE").format(sql.Identifier(self.schema_name))
            )
        super().tearDown()

    def _current_status(self):
        detail = self.client.get(f"/api/v1/app-models/{self.ticket.id}/records/{self.record_id}/")
        return detail.data[str(self.status_field.id)]


class ApplyTransitionTests(WorkflowTransitionTestBase):
    def test_applying_a_valid_transition_writes_the_new_state(self):
        workflows.apply_transition(self.actor, self.submit, self.record_id)
        self.assertEqual(self._current_status(), "open")

    def test_field_actions_are_applied_in_the_same_write(self):
        transition = instances.add_transition(
            self.actor,
            self.workflow,
            {
                "key": "auto_close",
                "label": "Auto Close",
                "from_state": str(self.workflow.states.get(key="draft").id),
                "to_state": str(self.workflow.states.get(key="closed").id),
                "field_actions": [{"field_id": str(self.status_field.id), "value": "closed"}],
            },
        )
        workflows.apply_transition(self.actor, transition, self.record_id)
        self.assertEqual(self._current_status(), "closed")

    def test_from_state_mismatch_is_a_clean_conflict_not_a_corrupted_write(self):
        with self.assertRaises(TransitionConflict):
            workflows.apply_transition(self.actor, self.close, self.record_id)
        # Untouched -- still "draft", not silently moved to "closed".
        self.assertEqual(self._current_status(), "draft")

    def test_requires_approval_denies_an_actor_without_the_capability(self):
        workflows.apply_transition(self.actor, self.submit, self.record_id)
        outsider = User.objects.create_user(email="wf-outsider@example.com")
        Membership.objects.create(user=outsider, organization=self.org, status=Membership.Status.ACTIVE)
        grant_resource_permission(
            user=outsider,
            permission_code="database.write",
            organization_id=self.org.id,
            resource_type="databases.tenant_database",
            resource_id=self.receipt.database_id,
        )
        with self.assertRaises(PermissionDenied):
            workflows.apply_transition(outsider, self.close, self.record_id)
        self.assertEqual(self._current_status(), "open")

    def test_requires_approval_succeeds_once_the_capability_is_granted(self):
        workflows.apply_transition(self.actor, self.submit, self.record_id)
        approver = User.objects.create_user(email="wf-approver@example.com")
        Membership.objects.create(user=approver, organization=self.org, status=Membership.Status.ACTIVE)
        grant_resource_permission(
            user=approver,
            permission_code="database.write",
            organization_id=self.org.id,
            resource_type="databases.tenant_database",
            resource_id=self.receipt.database_id,
        )
        assign_role(user=approver, role_slug="organization-administrator", organization=self.org)
        workflows.apply_transition(approver, self.close, self.record_id)
        self.assertEqual(self._current_status(), "closed")

    def test_a_condition_that_is_not_met_is_rejected(self):
        transition = instances.add_transition(
            self.actor,
            self.workflow,
            {
                "key": "guarded",
                "label": "Guarded",
                "from_state": str(self.workflow.states.get(key="draft").id),
                "to_state": str(self.workflow.states.get(key="open").id),
                "conditions": [
                    {"field_id": str(self.status_field.id), "operator": "eq", "value": "not-the-real-value"}
                ],
            },
        )
        with self.assertRaises(ValidationError):
            workflows.apply_transition(self.actor, transition, self.record_id)
        self.assertEqual(self._current_status(), "draft")


class IdempotencyTests(WorkflowTransitionTestBase):
    def test_a_replayed_request_with_the_same_key_short_circuits(self):
        key = uuid.uuid4()
        first = workflows.apply_transition(self.actor, self.submit, self.record_id, idempotency_key=key)
        second = workflows.apply_transition(self.actor, self.submit, self.record_id, idempotency_key=key)
        self.assertEqual(first.id, second.id)
        self.assertEqual(self._current_status(), "open")

    def test_the_same_key_for_a_different_transition_is_a_conflict(self):
        key = uuid.uuid4()
        workflows.apply_transition(self.actor, self.submit, self.record_id, idempotency_key=key)
        with self.assertRaises(TransitionConflict):
            workflows.apply_transition(self.actor, self.close, self.record_id, idempotency_key=key)

    def test_without_a_key_every_call_gets_its_own_attempt_row(self):
        from app_platform.models import WorkflowTransitionAttempt

        workflows.apply_transition(self.actor, self.submit, self.record_id)
        with self.assertRaises(TransitionConflict):
            workflows.apply_transition(self.actor, self.submit, self.record_id)
        attempts = WorkflowTransitionAttempt.objects.filter(transition=self.submit, record_id=self.record_id)
        self.assertEqual(attempts.count(), 2)


class ConcurrencyTests(WorkflowTransitionTestBase):
    def test_two_different_mutually_exclusive_transitions_exactly_one_wins(self):
        """The scenario this whole subsystem exists for: two different
        transitions (close, reject) racing on the same record from the
        same starting state -- exactly one may win."""
        reject = instances.add_transition(
            self.actor,
            self.workflow,
            {
                "key": "reject",
                "label": "Reject",
                "from_state": str(self.workflow.states.get(key="open").id),
                "to_state": str(self.workflow.states.get(key="draft").id),
            },
        )
        # self.actor already holds every capability (organization creator
        # -> organization-administrator), including app_instance.workflow.
        # approve, so the race below tests the compare-and-swap itself,
        # not the approval gate (already covered by ApplyTransitionTests).
        workflows.apply_transition(self.actor, self.submit, self.record_id)  # draft -> open

        def attempt(transition):
            close_old_connections()
            try:
                workflows.apply_transition(self.actor, transition, self.record_id)
                return "won"
            except TransitionConflict:
                return None
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(attempt, [self.close, reject]))

        winners = [r for r in results if r is not None]
        self.assertEqual(len(winners), 1)
        self.assertIn(self._current_status(), ("closed", "draft"))


def _free_port_server(handler):
    server = HTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread


class NotificationDeliveryTests(WorkflowTransitionTestBase):
    def test_a_transition_with_a_notify_url_delivers_a_real_http_post(self):
        received = []

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):  # noqa: N802 - BaseHTTPRequestHandler's own naming convention
                length = int(self.headers["Content-Length"])
                received.append(json.loads(self.rfile.read(length)))
                self.send_response(200)
                self.end_headers()

            def log_message(self, *args):
                pass  # Quiet -- the test's own assertions are the signal.

        server, thread = _free_port_server(Handler)
        try:
            port = server.server_address[1]
            transition = instances.add_transition(
                self.actor,
                self.workflow,
                {
                    "key": "notify_submit",
                    "label": "Notify Submit",
                    "from_state": str(self.workflow.states.get(key="draft").id),
                    "to_state": str(self.workflow.states.get(key="open").id),
                    "notify_url": f"http://127.0.0.1:{port}/hook",
                },
            )
            attempt = workflows.apply_transition(self.actor, transition, self.record_id)

            self.assertEqual(len(received), 1)
            self.assertEqual(received[0]["record_id"], str(self.record_id))
            self.assertEqual(received[0]["to_state"], "open")

            delivery = WorkflowNotificationDelivery.objects.get(attempt=attempt)
            self.assertIsNotNone(delivery.delivered_at)
        finally:
            server.shutdown()
            thread.join(timeout=5)

    def test_a_transition_without_a_notify_url_creates_no_delivery_row(self):
        workflows.apply_transition(self.actor, self.submit, self.record_id)
        self.assertEqual(WorkflowNotificationDelivery.objects.count(), 0)
