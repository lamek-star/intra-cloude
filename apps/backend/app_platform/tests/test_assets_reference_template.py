"""Phase 8 -- Assets reference application
(docs/implementation/APP_PLATFORM_ROADMAP.md,
docs/implementation/APP_PLATFORM_PHASE8.md). Same bar as Phase 4's Spare
Parts template test suite: draft validity, install-time metadata, real
Postgres schema on provisioning (composite constraint mixing a field and
a relationship, two independent `org_unit_reference` fields, nullable
set_null vendor relationship), and a realistic workflow through the real
record API.

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
from app_platform.reference_templates import assets_reference_definition
from app_platform.runtime_plan import plan_runtime
from app_platform.tests.test_foundation import project_for
from databases.models import DBIndex
from organizations.services import create_organization


class DraftValidationTests(TestCase):
    def test_the_draft_validates_cleanly(self):
        definition = validate_definition(assets_reference_definition())
        self.assertEqual(len(definition["models"]), 8)
        self.assertEqual(len(definition["relationships"]), 7)

    def test_depreciation_schedule_has_a_mixed_composite_constraint(self):
        definition = validate_definition(assets_reference_definition())
        [depreciation_schedule] = [m for m in definition["models"] if m["key"] == "depreciation_schedule"]
        [constraint] = depreciation_schedule["constraints"]
        self.assertEqual(len(constraint["field_ids"]), 1)
        self.assertEqual(len(constraint["relationship_ids"]), 1)


class InstallTests(TestCase):
    def setUp(self):
        call_command("seed_permissions", verbosity=0)
        self.owner = User.objects.create_user(email="assets-install@example.com")
        self.org = create_organization(name="Assets Install Org", created_by=self.owner)
        self.project = project_for(self.owner, self.org)

    def _install(self):
        template = templates.create_template(
            self.owner, self.org, {"label": "Assets", "draft": assets_reference_definition()}
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
                "asset_category", "location", "vendor", "asset",
                "asset_assignment", "maintenance_record", "depreciation_schedule", "disposal",
            },
        )

    def test_asset_and_assignment_both_have_independent_org_unit_reference_fields(self):
        instance = self._install()
        asset = instance.models.get(key="asset")
        assignment = instance.models.get(key="asset_assignment")
        self.assertEqual(asset.fields.get(key="org_unit").data_type, "org_unit_reference")
        self.assertEqual(assignment.fields.get(key="assigned_to_unit").data_type, "org_unit_reference")

    def test_asset_vendor_is_nullable_on_delete(self):
        instance = self._install()
        asset = instance.models.get(key="asset")
        relation = asset.outgoing.get(key="asset_vendor")
        self.assertEqual(relation.deletion_policy, "set_null")


class ProvisioningAndWorkflowTests(TransactionTestCase):
    databases = {"default", "tenant"}

    def setUp(self):
        call_command("seed_permissions", verbosity=0)
        self.actor = User.objects.create_user(email="assets-workflow@example.com")
        self.org = create_organization(name="Assets Workflow Org", created_by=self.actor)
        self.project = project_for(self.actor, self.org)
        template = templates.create_template(
            self.actor, self.org, {"label": "Assets", "draft": assets_reference_definition()}
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

    def test_depreciation_constraint_is_real_in_the_provisioned_schema(self):
        constraint = self.models["depreciation_schedule"].constraints.get(key="asset_period_unique")
        index_id = self.receipt.bindings["constraints"][str(constraint.id)]
        index = DBIndex.objects.get(pk=index_id)
        self.assertTrue(index.is_unique)

    def test_full_acquisition_assignment_and_depreciation_workflow(self):
        category = self._create("asset_category", name="Laptops", code="LAP")
        location = self._create("location", name="HQ Office", code="HQ")
        asset = self._create(
            "asset", name="ThinkPad X1", asset_tag="AST-0001", asset_category=category["id"],
            asset_location=location["id"], status="in_service",
        )
        self._create(
            "asset_assignment", asset_assignment_asset=asset["id"],
            notes="Assigned to onboarding kit",
        )
        self._create(
            "maintenance_record", maintenance_record_asset=asset["id"],
            performed_at="2026-09-01", description="Battery replacement", cost="80.00",
        )
        self._create(
            "depreciation_schedule", depreciation_schedule_asset=asset["id"],
            period_date="2026-09-01", depreciation_amount="50.00", book_value="950.00",
        )
        # One depreciation entry per (asset, period_date) -- a duplicate
        # is genuinely rejected by the real composite constraint.
        duplicate = self.client.post(
            self._records_url("depreciation_schedule"),
            {
                str(self._relation("depreciation_schedule", "depreciation_schedule_asset").id): asset["id"],
                str(self._field("depreciation_schedule", "period_date").id): "2026-09-01",
            },
            format="json",
        )
        self.assertEqual(duplicate.status_code, 400, duplicate.data)

        disposal = self._create(
            "disposal",
            disposal_asset=asset["id"],
            disposed_at="2026-09-16",
            method="recycled",
            proceeds="0.00",
        )
        self.assertEqual(disposal[str(self._relation("disposal", "disposal_asset").id)], asset["id"])
