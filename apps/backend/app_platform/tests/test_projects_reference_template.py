"""Phase 8 -- Projects reference application
(docs/implementation/APP_PLATFORM_ROADMAP.md,
docs/implementation/APP_PLATFORM_PHASE8.md). Same bar as Phase 4's Spare
Parts template test suite: draft validity, install-time metadata, real
Postgres schema on provisioning (nullable set_null relationships, native
many-to-many), and a realistic workflow through the real record API.

Cross-org isolation is not re-tested here for the same reason Phase 4's
own suite gives: this template introduces no new endpoint or resource
type, only definitions installed through the existing, already-isolation-
tested `app_platform` pipeline."""

from django.core.management import call_command
from django.db import connections
from django.test import TestCase, TransactionTestCase
from psycopg import sql
from rest_framework.test import APIClient

from accounts.models import User
from app_platform import instances, provisioning, templates
from app_platform.definitions import validate_definition
from app_platform.reference_templates import projects_reference_definition
from app_platform.runtime_plan import plan_runtime
from app_platform.tests.test_foundation import project_for
from organizations.services import create_organization


class DraftValidationTests(TestCase):
    def test_the_draft_validates_cleanly(self):
        definition = validate_definition(projects_reference_definition())
        self.assertEqual(len(definition["models"]), 8)
        self.assertEqual(len(definition["relationships"]), 8)


class InstallTests(TestCase):
    def setUp(self):
        call_command("seed_permissions", verbosity=0)
        self.owner = User.objects.create_user(email="projects-install@example.com")
        self.org = create_organization(name="Projects Install Org", created_by=self.owner)
        self.project = project_for(self.owner, self.org)

    def _install(self):
        template = templates.create_template(
            self.owner, self.org, {"label": "Projects", "draft": projects_reference_definition()}
        )
        version = templates.publish_template(self.owner, template)
        return instances.install(
            self.owner, self.project, {"label": "Runtime", "template_version": str(version.id)}
        )

    def test_install_creates_every_model(self):
        instance = self._install()
        keys = set(instance.models.values_list("key", flat=True))
        self.assertEqual(
            keys,
            {"client", "project", "milestone", "task_item", "task_assignment", "time_entry", "risk", "tag"},
        )

    def test_task_item_milestone_is_nullable_on_delete(self):
        instance = self._install()
        task_item = instance.models.get(key="task_item")
        relation = task_item.outgoing.get(key="task_item_milestone")
        self.assertEqual(relation.deletion_policy, "set_null")

    def test_project_tags_is_many_to_many(self):
        instance = self._install()
        project = instance.models.get(key="project")
        relation = project.outgoing.get(key="tags")
        self.assertEqual(relation.kind, "many_to_many")


class ProvisioningAndWorkflowTests(TransactionTestCase):
    databases = {"default", "tenant"}

    def setUp(self):
        call_command("seed_permissions", verbosity=0)
        self.actor = User.objects.create_user(email="projects-workflow@example.com")
        self.org = create_organization(name="Projects Workflow Org", created_by=self.actor)
        self.project = project_for(self.actor, self.org)
        template = templates.create_template(
            self.actor, self.org, {"label": "Projects", "draft": projects_reference_definition()}
        )
        version = templates.publish_template(self.actor, template)
        self.instance = instances.install(
            self.actor, self.project, {"label": "Runtime", "template_version": str(version.id)}
        )
        self.models = {m.key: m for m in self.instance.models.all()}
        self.plan = plan_runtime(self.actor, self.instance)
        provisioning.reserve(self.actor, self.instance, self.plan["fingerprint"])
        self.receipt = provisioning.execute(self.instance.id, self.actor)
        self.client = APIClient()
        self.client.force_authenticate(self.actor)

    def tearDown(self):
        with connections["tenant"].cursor() as cursor:
            cursor.execute(
                sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE").format(sql.Identifier(self.plan["schema_name"]))
            )
        super().tearDown()

    def _records_url(self, model_key):
        return f"/api/v1/app-models/{self.models[model_key].id}/records/"

    def _relation(self, model_key, relation_key):
        return self.models[model_key].outgoing.get(key=relation_key)

    def _create(self, model_key, **field_values):
        model = self.models[model_key]
        payload = {}
        for key, value in field_values.items():
            field = model.fields.filter(key=key).first()
            definition_id = field.id if field is not None else model.outgoing.get(key=key).id
            payload[str(definition_id)] = value
        response = self.client.post(self._records_url(model_key), payload, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        return response.data

    def test_full_delivery_and_time_tracking_workflow(self):
        client = self._create("client", name="Northwind Traders")
        project = self._create(
            "project", name="Website Revamp", code="WEB-01", project_client=client["id"], status="planning"
        )
        milestone = self._create(
            "milestone", name="Design Sign-off", milestone_project=project["id"], status="pending"
        )
        task = self._create(
            "task_item",
            title="Wireframes",
            task_item_project=project["id"],
            task_item_milestone=milestone["id"],
            status="todo",
            priority="high",
        )
        self._create(
            "task_assignment", task_assignment_task=task["id"], assignee_name="Morgan Lee", role="designer"
        )
        self._create("time_entry", time_entry_task=task["id"], logged_date="2026-09-16", hours="3.5")
        self._create(
            "risk", title="Scope creep", risk_project=project["id"], severity="medium", status="open"
        )

        # Deleting the milestone should orphan the task, not block it.
        delete = self.client.delete(f"{self._records_url('milestone')}{milestone['id']}/")
        self.assertEqual(delete.status_code, 204, delete.data)
        refetched = self.client.get(f"{self._records_url('task_item')}{task['id']}/")
        self.assertIsNone(refetched.data[str(self._relation("task_item", "task_item_milestone").id)])

        tag = self._create("tag", name="Priority")
        tags_relation = self._relation("project", "tags")
        linked = self.client.patch(
            f"{self._records_url('project')}{project['id']}/",
            {str(tags_relation.id): [tag["id"]]},
            format="json",
        )
        self.assertEqual(linked.status_code, 200, linked.data)
        self.assertEqual(linked.data[str(tags_relation.id)], [tag["id"]])
