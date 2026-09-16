"""Phase 8 -- Warehouses reference application
(docs/implementation/APP_PLATFORM_ROADMAP.md,
docs/implementation/APP_PLATFORM_PHASE8.md). Same bar as Phase 4's Spare
Parts template test suite: draft validity, install-time metadata, real
Postgres schema on provisioning (relationship-only composite constraint,
two distinct relationships from one model to the same target model), and
a realistic workflow through the real record API.

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
from app_platform.reference_templates import warehouses_reference_definition
from app_platform.runtime_plan import plan_runtime
from app_platform.tests.test_foundation import project_for
from databases.models import DBIndex
from organizations.services import create_organization


class DraftValidationTests(TestCase):
    def test_the_draft_validates_cleanly(self):
        definition = validate_definition(warehouses_reference_definition())
        self.assertEqual(len(definition["models"]), 10)
        self.assertEqual(len(definition["relationships"]), 12)

    def test_stock_level_has_a_relationship_only_composite_constraint(self):
        definition = validate_definition(warehouses_reference_definition())
        [stock_level] = [m for m in definition["models"] if m["key"] == "stock_level"]
        [constraint] = stock_level["constraints"]
        self.assertEqual(constraint["field_ids"], [])
        self.assertEqual(len(constraint["relationship_ids"]), 2)


class InstallTests(TestCase):
    def setUp(self):
        call_command("seed_permissions", verbosity=0)
        self.owner = User.objects.create_user(email="warehouses-install@example.com")
        self.org = create_organization(name="Warehouses Install Org", created_by=self.owner)
        self.project = project_for(self.owner, self.org)

    def _install(self):
        template = templates.create_template(
            self.owner, self.org, {"label": "Warehouses", "draft": warehouses_reference_definition()}
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
                "warehouse", "zone", "bin_location", "item", "stock_level",
                "inbound_shipment", "inbound_shipment_line",
                "outbound_shipment", "outbound_shipment_line", "transfer_order",
            },
        )

    def test_transfer_order_has_two_distinct_relationships_to_warehouse(self):
        instance = self._install()
        transfer_order = instance.models.get(key="transfer_order")
        source = transfer_order.outgoing.get(key="source_warehouse")
        destination = transfer_order.outgoing.get(key="destination_warehouse")
        self.assertEqual(source.target_model.key, "warehouse")
        self.assertEqual(destination.target_model.key, "warehouse")
        self.assertNotEqual(source.id, destination.id)


class ProvisioningAndWorkflowTests(TransactionTestCase):
    databases = {"default", "tenant"}

    def setUp(self):
        call_command("seed_permissions", verbosity=0)
        self.actor = User.objects.create_user(email="warehouses-workflow@example.com")
        self.org = create_organization(name="Warehouses Workflow Org", created_by=self.actor)
        self.project = project_for(self.actor, self.org)
        template = templates.create_template(
            self.actor, self.org, {"label": "Warehouses", "draft": warehouses_reference_definition()}
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

    def test_stock_level_constraint_is_real_in_the_provisioned_schema(self):
        constraint = self.models["stock_level"].constraints.get(key="item_bin_location_unique")
        index_id = self.receipt.bindings["constraints"][str(constraint.id)]
        index = DBIndex.objects.get(pk=index_id)
        self.assertTrue(index.is_unique)

    def test_full_receiving_stocking_and_transfer_workflow(self):
        main_warehouse = self._create("warehouse", name="Main DC", code="MAIN")
        overflow_warehouse = self._create("warehouse", name="Overflow DC", code="OVERFLOW")
        zone = self._create("zone", name="Zone A", zone_warehouse=main_warehouse["id"])
        bin_a = self._create("bin_location", code="A-01", bin_location_zone=zone["id"], capacity=100)
        item = self._create("item", sku="SKU-001", name="Widget")

        self._create(
            "stock_level", stock_level_item=item["id"], stock_level_bin_location=bin_a["id"], quantity_on_hand=50
        )
        # One stock row per (item, bin location) -- a duplicate is
        # genuinely rejected by the real composite constraint.
        duplicate = self.client.post(
            self._records_url("stock_level"),
            {
                str(self._relation("stock_level", "stock_level_item").id): item["id"],
                str(self._relation("stock_level", "stock_level_bin_location").id): bin_a["id"],
                str(self._field("stock_level", "quantity_on_hand").id): 5,
            },
            format="json",
        )
        self.assertEqual(duplicate.status_code, 400, duplicate.data)

        inbound = self._create(
            "inbound_shipment", inbound_shipment_warehouse=main_warehouse["id"],
            reference_number="IN-0001", status="pending",
        )
        self._create(
            "inbound_shipment_line", inbound_shipment_line_shipment=inbound["id"],
            inbound_shipment_line_item=item["id"], quantity_expected=50, quantity_received=50,
        )

        outbound = self._create(
            "outbound_shipment", outbound_shipment_warehouse=main_warehouse["id"],
            reference_number="OUT-0001", status="pending",
        )
        self._create(
            "outbound_shipment_line", outbound_shipment_line_shipment=outbound["id"],
            outbound_shipment_line_item=item["id"], quantity=5,
        )

        transfer = self._create(
            "transfer_order", source_warehouse=main_warehouse["id"], destination_warehouse=overflow_warehouse["id"],
            status="pending",
        )
        self.assertEqual(transfer[str(self._relation("transfer_order", "source_warehouse").id)], main_warehouse["id"])
        self.assertEqual(
            transfer[str(self._relation("transfer_order", "destination_warehouse").id)], overflow_warehouse["id"]
        )
