"""Phase 5 -- Workflow engine (docs/implementation/APP_PLATFORM_PHASE5.md).
This file covers the declarative layer -- draft/template validation,
install-time metadata creation, and live add-to-an-installed-instance
functions -- mirroring test_composite_constraints.py's own structure.
Transition *application* (workflows.py::apply_transition, the
compare-and-swap/idempotency engine) is covered separately in
test_workflow_transitions.py, since it needs real provisioning."""

import uuid

from django.core.management import call_command
from django.test import TestCase
from rest_framework.exceptions import ValidationError

from accounts.models import User
from app_platform import definitions, instances, templates
from app_platform.models import WorkflowDefinition
from app_platform.tests.test_foundation import project_for, sample
from organizations.services import create_organization


def workflow_sample():
    """A single model ("ticket") with a text `status` field driving one
    workflow: draft -> open -> closed, with the close transition marked
    requires_approval, mirroring composite_sample()'s own
    pre-generated-id pattern so states/transitions can reference each
    other within the same payload."""
    model_id = str(uuid.uuid4())
    status_id = str(uuid.uuid4())
    workflow_id = str(uuid.uuid4())
    draft_id, open_id, closed_id = str(uuid.uuid4()), str(uuid.uuid4()), str(uuid.uuid4())
    return {
        "schema_version": 1,
        "models": [
            {
                "id": model_id,
                "key": "ticket",
                "label": "Ticket",
                "fields": [{"id": status_id, "key": "status", "label": "Status", "data_type": "text"}],
                "workflows": [
                    {
                        "id": workflow_id,
                        "key": "lifecycle",
                        "label": "Lifecycle",
                        "state_field": status_id,
                        "states": [
                            {"id": draft_id, "key": "draft", "label": "Draft"},
                            {"id": open_id, "key": "open", "label": "Open"},
                            {"id": closed_id, "key": "closed", "label": "Closed"},
                        ],
                        "transitions": [
                            {
                                "key": "submit",
                                "label": "Submit",
                                "from_state": draft_id,
                                "to_state": open_id,
                            },
                            {
                                "key": "close",
                                "label": "Close",
                                "from_state": open_id,
                                "to_state": closed_id,
                                "requires_approval": True,
                            },
                        ],
                    }
                ],
            }
        ],
        "relationships": [],
    }


class DraftValidationTests(TestCase):
    def test_a_valid_workflow_is_accepted(self):
        definition = definitions.validate_definition(workflow_sample())
        [model] = definition["models"]
        [workflow] = model["workflows"]
        self.assertEqual(len(workflow["states"]), 3)
        self.assertEqual(len(workflow["transitions"]), 2)
        self.assertTrue(workflow["transitions"][1]["requires_approval"])

    def test_a_model_without_workflows_still_validates_unchanged(self):
        definition = definitions.validate_definition(sample())
        for model in definition["models"]:
            self.assertEqual(model.get("workflows", []), [])

    def test_state_field_must_belong_to_the_same_model(self):
        d = workflow_sample()
        d["models"][0]["workflows"][0]["state_field"] = str(uuid.uuid4())
        with self.assertRaises(ValidationError):
            definitions.validate_definition(d)

    def test_state_field_must_be_text(self):
        d = workflow_sample()
        d["models"][0]["fields"].append(
            {"id": str(uuid.uuid4()), "key": "qty", "label": "Qty", "data_type": "integer"}
        )
        d["models"][0]["workflows"][0]["state_field"] = d["models"][0]["fields"][1]["id"]
        with self.assertRaises(ValidationError):
            definitions.validate_definition(d)

    def test_transition_to_state_must_belong_to_the_same_workflow(self):
        d = workflow_sample()
        d["models"][0]["workflows"][0]["transitions"][0]["to_state"] = str(uuid.uuid4())
        with self.assertRaises(ValidationError):
            definitions.validate_definition(d)

    def test_transition_from_state_none_means_any_state_and_is_accepted(self):
        d = workflow_sample()
        d["models"][0]["workflows"][0]["transitions"][0]["from_state"] = None
        definition = definitions.validate_definition(d)
        [transition] = [
            t for t in definition["models"][0]["workflows"][0]["transitions"] if t["key"] == "submit"
        ]
        self.assertIsNone(transition["from_state"])

    def test_condition_field_must_belong_to_the_workflow_model(self):
        d = workflow_sample()
        d["models"][0]["workflows"][0]["transitions"][0]["conditions"] = [
            {"field_id": str(uuid.uuid4()), "operator": "is_null"}
        ]
        with self.assertRaises(ValidationError):
            definitions.validate_definition(d)

    def test_action_value_must_be_valid_for_the_field_type(self):
        d = workflow_sample()
        status_id = d["models"][0]["fields"][0]["id"]
        d["models"][0]["workflows"][0]["transitions"][0]["field_actions"] = [
            {"field_id": status_id, "value": 123}
        ]
        with self.assertRaises(ValidationError):
            definitions.validate_definition(d)

    def test_unsafe_notify_url_is_rejected(self):
        d = workflow_sample()
        d["models"][0]["workflows"][0]["transitions"][0]["notify_url"] = "http://169.254.169.254/hook"
        with self.assertRaises(ValidationError):
            definitions.validate_definition(d)

    def test_eq_condition_without_a_value_is_rejected(self):
        d = workflow_sample()
        status_id = d["models"][0]["fields"][0]["id"]
        d["models"][0]["workflows"][0]["transitions"][0]["conditions"] = [
            {"field_id": status_id, "operator": "eq"}
        ]
        with self.assertRaises(ValidationError):
            definitions.validate_definition(d)


class InstallTests(TestCase):
    def setUp(self):
        call_command("seed_permissions", verbosity=0)
        self.owner = User.objects.create_user(email="wf-install@example.com")
        self.org = create_organization(name="Workflow Install Org", created_by=self.owner)
        self.project = project_for(self.owner, self.org)

    def _install(self, draft):
        template = templates.create_template(self.owner, self.org, {"label": "App", "draft": draft})
        version = templates.publish_template(self.owner, template)
        return instances.install(
            self.owner, self.project, {"label": "Runtime", "template_version": str(version.id)}
        )

    def test_install_creates_the_workflow_states_and_transitions(self):
        instance = self._install(workflow_sample())
        ticket = instance.models.get(key="ticket")
        workflow = ticket.workflows.get(key="lifecycle")
        self.assertEqual(workflow.state_field.key, "status")
        self.assertEqual({s.key for s in workflow.states.all()}, {"draft", "open", "closed"})

        submit = workflow.transitions.get(key="submit")
        self.assertEqual(submit.from_state.key, "draft")
        self.assertEqual(submit.to_state.key, "open")
        self.assertFalse(submit.requires_approval)

        close = workflow.transitions.get(key="close")
        self.assertEqual(close.from_state.key, "open")
        self.assertEqual(close.to_state.key, "closed")
        self.assertTrue(close.requires_approval)

    def test_condition_and_action_field_ids_are_translated_to_real_field_ids(self):
        d = workflow_sample()
        status_id = d["models"][0]["fields"][0]["id"]
        d["models"][0]["workflows"][0]["transitions"][0]["field_actions"] = [
            {"field_id": status_id, "value": "auto-submitted"}
        ]
        instance = self._install(d)
        ticket = instance.models.get(key="ticket")
        status_field = ticket.fields.get(key="status")
        submit = ticket.workflows.get(key="lifecycle").transitions.get(key="submit")
        self.assertEqual(
            submit.field_actions, [{"field_id": str(status_field.id), "value": "auto-submitted"}]
        )


class LiveAddTests(TestCase):
    def setUp(self):
        call_command("seed_permissions", verbosity=0)
        self.owner = User.objects.create_user(email="wf-live@example.com")
        self.org = create_organization(name="Workflow Live Org", created_by=self.owner)
        self.project = project_for(self.owner, self.org)
        template = templates.create_template(self.owner, self.org, {"label": "App", "draft": sample()})
        version = templates.publish_template(self.owner, template)
        self.instance = instances.install(
            self.owner, self.project, {"label": "Runtime", "template_version": str(version.id)}
        )
        self.item = self.instance.models.get(key="item")
        self.name_field = self.item.fields.get(key="name")

    def test_add_workflow_state_and_transition_on_an_unprovisioned_instance(self):
        workflow = instances.add_workflow(
            self.owner,
            self.item,
            {"key": "lifecycle", "label": "Lifecycle", "state_field": str(self.name_field.id)},
        )
        self.assertEqual(WorkflowDefinition.objects.filter(pk=workflow.id).count(), 1)

        draft_state = instances.add_state(self.owner, workflow, {"key": "draft", "label": "Draft"})
        open_state = instances.add_state(self.owner, workflow, {"key": "open", "label": "Open"})

        transition = instances.add_transition(
            self.owner,
            workflow,
            {
                "key": "submit",
                "label": "Submit",
                "from_state": str(draft_state.id),
                "to_state": str(open_state.id),
            },
        )
        self.assertEqual(transition.from_state_id, draft_state.id)
        self.assertEqual(transition.to_state_id, open_state.id)

    def test_add_workflow_rejects_a_non_text_state_field(self):
        price_field = self.item.fields.get(key="price")
        with self.assertRaises(ValidationError):
            instances.add_workflow(
                self.owner,
                self.item,
                {"key": "lifecycle", "label": "Lifecycle", "state_field": str(price_field.id)},
            )

    def test_add_transition_rejects_a_state_from_a_different_workflow(self):
        workflow_a = instances.add_workflow(
            self.owner, self.item, {"key": "a", "label": "A", "state_field": str(self.name_field.id)}
        )
        workflow_b = instances.add_workflow(
            self.owner, self.item, {"key": "b", "label": "B", "state_field": str(self.name_field.id)}
        )
        state_in_b = instances.add_state(self.owner, workflow_b, {"key": "x", "label": "X"})
        with self.assertRaises(ValidationError):
            instances.add_transition(
                self.owner,
                workflow_a,
                {"key": "go", "label": "Go", "to_state": str(state_in_b.id)},
            )
