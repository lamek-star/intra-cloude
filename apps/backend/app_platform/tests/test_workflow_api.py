"""Phase 5 -- workflow HTTP API (docs/implementation/APP_PLATFORM_PHASE5.md):
the actual endpoints (views.py/urls.py) wrapping instances.add_workflow/
add_state/add_transition and workflows.apply_transition -- URL routing,
serialization, the Idempotency-Key header, HTTP status codes (409 on
conflict, 403 on a missing approval capability), cross-org isolation
(IDOR/BOLA, per CLAUDE.md's rule for every new resource type), and the
service-account reachability boundary (authoring stays human-only;
applying a transition is open to a properly scoped bearer token, since
it's fundamentally a record write)."""

from django.core.management import call_command
from django.db import connections
from django.test import TransactionTestCase
from psycopg import sql
from rest_framework.test import APIClient

from accounts.models import User
from app_platform import instances, provisioning, templates
from app_platform.runtime_plan import plan_runtime
from app_platform.tests.test_foundation import project_for
from app_platform.tests.test_workflows import workflow_sample
from applications import services as app_services
from organizations.models import Membership
from organizations.services import create_organization
from permissions.services import grant_resource_permission


class WorkflowApiTestBase(TransactionTestCase):
    databases = {"default", "tenant"}

    def setUp(self):
        call_command("seed_permissions", verbosity=0)
        self.owner = User.objects.create_user(email="wf-api@example.com")
        self.org = create_organization(name="Workflow API Org", created_by=self.owner)
        self.project = project_for(self.owner, self.org)
        template = templates.create_template(
            self.owner, self.org, {"label": "App", "draft": workflow_sample()}
        )
        version = templates.publish_template(self.owner, template)
        self.instance = instances.install(
            self.owner, self.project, {"label": "Runtime", "template_version": str(version.id)}
        )
        self.ticket = self.instance.models.get(key="ticket")
        self.status_field = self.ticket.fields.get(key="status")
        self.workflow = self.ticket.workflows.get(key="lifecycle")
        self.submit = self.workflow.transitions.get(key="submit")
        self.close = self.workflow.transitions.get(key="close")

        plan = plan_runtime(self.owner, self.instance)
        self.schema_name = plan["schema_name"]
        provisioning.reserve(self.owner, self.instance, plan["fingerprint"])
        self.receipt = provisioning.execute(self.instance.id, self.owner)

        self.client = APIClient()
        self.client.force_authenticate(self.owner)
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

    def _apply_url(self, transition_id):
        return (
            f"/api/v1/app-models/{self.ticket.id}/records/{self.record_id}"
            f"/transitions/{transition_id}/apply/"
        )


class AuthoringApiTests(WorkflowApiTestBase):
    def test_create_workflow_state_and_transition_through_the_api(self):
        wf = self.client.post(
            f"/api/v1/app-models/{self.ticket.id}/workflows/",
            {"key": "second", "label": "Second", "state_field": str(self.status_field.id)},
            format="json",
        )
        self.assertEqual(wf.status_code, 201, wf.data)

        state = self.client.post(
            f"/api/v1/app-workflows/{wf.data['id']}/states/",
            {"key": "a", "label": "A"},
            format="json",
        )
        self.assertEqual(state.status_code, 201, state.data)

        transition = self.client.post(
            f"/api/v1/app-workflows/{wf.data['id']}/transitions/",
            {"key": "go", "label": "Go", "to_state": state.data["id"]},
            format="json",
        )
        self.assertEqual(transition.status_code, 201, transition.data)
        self.assertIsNone(transition.data["from_state"])

    def test_list_workflows_and_transitions(self):
        listing = self.client.get(f"/api/v1/app-models/{self.ticket.id}/workflows/")
        self.assertEqual(listing.status_code, 200)
        self.assertEqual(listing.data["count"], 1)

        transitions = self.client.get(f"/api/v1/app-workflows/{self.workflow.id}/transitions/")
        self.assertEqual(transitions.status_code, 200)
        self.assertEqual(transitions.data["count"], 2)

    def test_rename_a_transition_does_not_require_schema_manage(self):
        renamed = self.client.patch(
            f"/api/v1/app-transitions/{self.submit.id}/", {"label": "Renamed"}, format="json"
        )
        self.assertEqual(renamed.status_code, 200, renamed.data)
        self.assertEqual(renamed.data["label"], "Renamed")


class ApplyTransitionApiTests(WorkflowApiTestBase):
    def test_apply_succeeds_and_returns_an_attempt(self):
        resp = self.client.post(self._apply_url(self.submit.id), {}, format="json")
        self.assertEqual(resp.status_code, 200, resp.data)
        self.assertEqual(resp.data["state_after"], "open")

    def test_apply_with_wrong_from_state_is_a_409(self):
        resp = self.client.post(self._apply_url(self.close.id), {}, format="json")
        self.assertEqual(resp.status_code, 409, resp.data)

    def test_apply_requiring_approval_is_a_403_without_the_capability(self):
        self.client.post(self._apply_url(self.submit.id), {}, format="json")
        outsider = User.objects.create_user(email="wf-api-outsider@example.com")
        Membership.objects.create(user=outsider, organization=self.org, status=Membership.Status.ACTIVE)
        grant_resource_permission(
            user=outsider,
            permission_code="database.write",
            organization_id=self.org.id,
            resource_type="databases.tenant_database",
            resource_id=self.receipt.database_id,
        )
        outsider_client = APIClient()
        outsider_client.force_authenticate(outsider)
        resp = outsider_client.post(self._apply_url(self.close.id), {}, format="json")
        self.assertEqual(resp.status_code, 403, resp.data)

    def test_idempotency_key_header_replays_the_same_attempt(self):
        key = "11111111-1111-1111-1111-111111111111"
        first = self.client.post(
            self._apply_url(self.submit.id), {}, format="json", HTTP_IDEMPOTENCY_KEY=key
        )
        second = self.client.post(
            self._apply_url(self.submit.id), {}, format="json", HTTP_IDEMPOTENCY_KEY=key
        )
        self.assertEqual(first.status_code, 200, first.data)
        self.assertEqual(second.status_code, 200, second.data)
        self.assertEqual(first.data["id"], second.data["id"])

    def test_a_transition_id_that_does_not_belong_to_this_model_is_a_404(self):
        other_template = templates.create_template(
            self.owner, self.org, {"label": "Other", "draft": workflow_sample()}
        )
        other_version = templates.publish_template(self.owner, other_template)
        other_instance = instances.install(
            self.owner, self.project, {"label": "Other Runtime", "template_version": str(other_version.id)}
        )
        other_ticket = other_instance.models.get(key="ticket")
        other_submit = other_ticket.workflows.get(key="lifecycle").transitions.get(key="submit")

        # Same record/model as this test's own ticket, but a transition id
        # that belongs to a completely different model -- must not be
        # reachable by ID substitution.
        resp = self.client.post(self._apply_url(other_submit.id), {}, format="json")
        self.assertEqual(resp.status_code, 404)


class CrossOrgIsolationTests(WorkflowApiTestBase):
    def test_a_non_member_cannot_read_a_workflow_by_id_substitution(self):
        outsider = User.objects.create_user(email="wf-api-nonmember@example.com")
        create_organization(name="Workflow API Outsider Org", created_by=outsider)
        outsider_client = APIClient()
        outsider_client.force_authenticate(outsider)

        for url in (
            f"/api/v1/app-workflows/{self.workflow.id}/",
            f"/api/v1/app-workflow-states/{self.workflow.states.first().id}/",
            f"/api/v1/app-transitions/{self.submit.id}/",
        ):
            resp = outsider_client.get(url)
            self.assertEqual(resp.status_code, 404, url)

    def test_a_non_member_cannot_apply_a_transition_by_id_substitution(self):
        outsider = User.objects.create_user(email="wf-api-nonmember2@example.com")
        create_organization(name="Workflow API Outsider Org 2", created_by=outsider)
        outsider_client = APIClient()
        outsider_client.force_authenticate(outsider)
        resp = outsider_client.post(self._apply_url(self.submit.id), {}, format="json")
        self.assertEqual(resp.status_code, 404)


class ServiceAccountBoundaryTests(WorkflowApiTestBase):
    def setUp(self):
        super().setUp()
        self.application = app_services.register_application(
            organization=self.org, name="Workflow Bot", description="", owner=self.owner
        )
        self.credential, self.token = app_services.issue_credential(
            service_account=self.application.service_account, actor=self.owner
        )
        self.bearer_client = APIClient()

    def _auth(self):
        return {"HTTP_AUTHORIZATION": f"Bearer {self.token}"}

    def test_a_bearer_token_cannot_author_a_workflow(self):
        resp = self.bearer_client.post(
            f"/api/v1/app-models/{self.ticket.id}/workflows/",
            {"key": "x", "label": "X", "state_field": str(self.status_field.id)},
            format="json",
            **self._auth(),
        )
        self.assertEqual(resp.status_code, 403, resp.data)

    def test_a_properly_scoped_bearer_token_can_apply_a_transition(self):
        for code in ("database.read", "database.write"):
            grant_resource_permission(
                user=self.application.service_account.identity_user,
                permission_code=code,
                organization_id=self.org.id,
                resource_type="databases.tenant_database",
                resource_id=self.receipt.database_id,
                granted_by=self.owner,
            )
        resp = self.bearer_client.post(self._apply_url(self.submit.id), {}, format="json", **self._auth())
        self.assertEqual(resp.status_code, 200, resp.data)
