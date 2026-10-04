"""Phase 8 -- CRM reference application
(docs/implementation/APP_PLATFORM_ROADMAP.md,
docs/implementation/APP_PLATFORM_PHASE8.md). Same bar as Phase 4's Spare
Parts template test suite: draft validity, install-time metadata, real
Postgres schema on provisioning (nullable set_null relationship, native
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
from app_platform.reference_templates import crm_reference_definition
from app_platform.runtime_plan import plan_runtime
from app_platform.tests.test_foundation import project_for
from organizations.services import create_organization


class DraftValidationTests(TestCase):
    def test_the_draft_validates_cleanly(self):
        definition = validate_definition(crm_reference_definition())
        self.assertEqual(len(definition["models"]), 8)
        self.assertEqual(len(definition["relationships"]), 9)


class InstallTests(TestCase):
    def setUp(self):
        call_command("seed_permissions", verbosity=0)
        self.owner = User.objects.create_user(email="crm-install@example.com")
        self.org = create_organization(name="CRM Install Org", created_by=self.owner)
        self.project = project_for(self.owner, self.org)

    def _install(self):
        template = templates.create_template(
            self.owner, self.org, {"label": "CRM", "draft": crm_reference_definition()}
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
            {
                "account",
                "contact",
                "lead",
                "campaign",
                "opportunity",
                "opportunity_line_item",
                "activity",
                "note",
            },
        )

    def test_opportunity_campaign_is_nullable_on_delete(self):
        instance = self._install()
        opportunity = instance.models.get(key="opportunity")
        relation = opportunity.outgoing.get(key="opportunity_campaign")
        self.assertEqual(relation.deletion_policy, "set_null")

    def test_campaign_targeted_contacts_is_many_to_many(self):
        instance = self._install()
        campaign = instance.models.get(key="campaign")
        relation = campaign.outgoing.get(key="targeted_contacts")
        self.assertEqual(relation.kind, "many_to_many")
        self.assertEqual(relation.target_model.key, "contact")


class ProvisioningAndWorkflowTests(TransactionTestCase):
    databases = {"default", "tenant"}

    def setUp(self):
        call_command("seed_permissions", verbosity=0)
        self.actor = User.objects.create_user(email="crm-workflow@example.com")
        self.org = create_organization(name="CRM Workflow Org", created_by=self.actor)
        self.project = project_for(self.actor, self.org)
        template = templates.create_template(
            self.actor, self.org, {"label": "CRM", "draft": crm_reference_definition()}
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

    def _field(self, model_key, field_key):
        return self.models[model_key].fields.get(key=field_key)

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

    def test_deleting_a_campaign_orphans_its_opportunities_not_blocks_it(self):
        account = self._create("account", name="Acme Co")
        campaign = self._create("campaign", name="Fall Push")
        opportunity = self._create(
            "opportunity", name="Acme Renewal", stage="prospecting",
            opportunity_account=account["id"], opportunity_campaign=campaign["id"],
        )
        delete = self.client.delete(f"{self._records_url('campaign')}{campaign['id']}/")
        self.assertEqual(delete.status_code, 204, delete.data)
        refetched = self.client.get(f"{self._records_url('opportunity')}{opportunity['id']}/")
        self.assertIsNone(refetched.data[str(self._relation("opportunity", "opportunity_campaign").id)])

    def test_full_lead_to_pipeline_workflow(self):
        account = self._create("account", name="Globex Corp")
        contact = self._create("contact", first_name="Pat", last_name="Nguyen", contact_account=account["id"])
        self._create("lead", name="Referral Lead", status="new", source="referral")
        opportunity = self._create(
            "opportunity", name="Globex Deal", amount="10000.00", stage="prospecting",
            opportunity_account=account["id"], opportunity_contact=contact["id"],
        )
        self._create(
            "opportunity_line_item", opportunity_line_item_opportunity=opportunity["id"],
            quantity=2, unit_price="500.00", line_total="1000.00",
        )
        self._create(
            "activity", subject="Follow up call", activity_contact=contact["id"],
            activity_opportunity=opportunity["id"], completed=False,
        )
        self._create("note", body="Initial discovery call went well.", note_account=account["id"])

        campaign = self._create("campaign", name="Q4 Outreach")
        targeted_relation = self._relation("campaign", "targeted_contacts")
        linked = self.client.patch(
            f"{self._records_url('campaign')}{campaign['id']}/",
            {str(targeted_relation.id): [contact["id"]]},
            format="json",
        )
        self.assertEqual(linked.status_code, 200, linked.data)
        self.assertEqual(linked.data[str(targeted_relation.id)], [contact["id"]])
