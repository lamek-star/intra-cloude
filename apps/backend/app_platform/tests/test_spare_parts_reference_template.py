"""Phase 4 -- Inventory and Sales reference application
(docs/implementation/APP_PLATFORM_ROADMAP.md,
docs/implementation/APP_PLATFORM_PHASE4.md). Proves the
`spare_parts_reference_definition()` draft (app_platform/
reference_templates.py) is a real, working application built entirely on
Phases 1-3's generic primitives -- draft validity, install-time metadata,
real Postgres schema on provisioning (including the Inventory composite
constraint over two relationships, a self-referencing relationship, and
the native many-to-many join table), and a realistic business workflow
through the actual record API.

Cross-org isolation is not re-tested here: this template introduces no
new endpoint or resource type, only definitions installed through the
existing, already-isolation-tested `app_platform` pipeline (see
test_foundation.py::test_every_resource_endpoint_denies_foreign_organization
and the per-feature isolation tests in test_composite_constraints.py/
test_many_to_many.py) -- a deliberate decision, not an oversight."""

from django.core.management import call_command
from django.db import connections
from django.test import TestCase, TransactionTestCase
from psycopg import sql
from rest_framework.test import APIClient

from accounts.models import User
from app_platform import instances, provisioning, templates
from app_platform.definitions import validate_definition
from app_platform.reference_templates import spare_parts_reference_definition
from app_platform.runtime_plan import plan_runtime
from app_platform.tests.test_foundation import project_for
from databases.models import DBIndex
from organizations.services import create_organization


class DraftValidationTests(TestCase):
    def test_the_draft_validates_cleanly(self):
        definition = validate_definition(spare_parts_reference_definition())
        self.assertEqual(len(definition["models"]), 13)
        self.assertEqual(len(definition["relationships"]), 14)

    def test_inventory_has_a_relationship_only_composite_constraint(self):
        definition = validate_definition(spare_parts_reference_definition())
        [inventory] = [m for m in definition["models"] if m["key"] == "inventory"]
        [constraint] = inventory["constraints"]
        self.assertEqual(constraint["field_ids"], [])
        self.assertEqual(len(constraint["relationship_ids"]), 2)


class InstallTests(TestCase):
    def setUp(self):
        call_command("seed_permissions", verbosity=0)
        self.owner = User.objects.create_user(email="spare-install@example.com")
        self.org = create_organization(name="Spare Parts Install Org", created_by=self.owner)
        self.project = project_for(self.owner, self.org)

    def _install(self):
        template = templates.create_template(
            self.owner, self.org, {"label": "Spare Parts", "draft": spare_parts_reference_definition()}
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
                "part", "part_number", "vehicle", "warehouse", "inventory", "stock_movement",
                "supplier", "purchase_order", "purchase_order_line", "customer", "sales_order",
                "sales_order_line", "invoice",
            },
        )

    def test_inventory_constraint_resolves_to_real_relationship_rows(self):
        instance = self._install()
        inventory = instance.models.get(key="inventory")
        constraint = inventory.constraints.get(key="part_warehouse_unique")
        self.assertEqual(constraint.fields.count(), 0)
        self.assertEqual(
            {r.target_model.key for r in constraint.relationships.all()},
            {"part", "warehouse"},
        )

    def test_part_number_supersedes_is_self_referencing(self):
        instance = self._install()
        part_number = instance.models.get(key="part_number")
        supersedes = part_number.outgoing.get(key="supersedes")
        self.assertEqual(supersedes.source_model_id, part_number.id)
        self.assertEqual(supersedes.target_model_id, part_number.id)
        self.assertEqual(supersedes.deletion_policy, "set_null")

    def test_part_vehicle_is_many_to_many(self):
        instance = self._install()
        part = instance.models.get(key="part")
        relation = part.outgoing.get(key="compatible_vehicles")
        self.assertEqual(relation.kind, "many_to_many")
        self.assertEqual(relation.target_model.key, "vehicle")


class ProvisioningAndWorkflowTests(TransactionTestCase):
    """Fresh provisioning against real Postgres, then a realistic
    Supplier->PO->line / Part->PartNumber->Inventory / Customer->SO->
    line->Invoice / Part<->Vehicle workflow through the real record API --
    the same bar every other App Platform feature test uses."""

    databases = {"default", "tenant"}

    def setUp(self):
        call_command("seed_permissions", verbosity=0)
        self.actor = User.objects.create_user(email="spare-workflow@example.com")
        self.org = create_organization(name="Spare Parts Workflow Org", created_by=self.actor)
        self.project = project_for(self.actor, self.org)
        template = templates.create_template(
            self.actor, self.org, {"label": "Spare Parts", "draft": spare_parts_reference_definition()}
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

    def test_inventory_composite_constraint_is_real_in_the_provisioned_schema(self):
        constraint = self.models["inventory"].constraints.get(key="part_warehouse_unique")
        index_id = self.receipt.bindings["constraints"][str(constraint.id)]
        index = DBIndex.objects.get(pk=index_id)
        self.assertTrue(index.is_unique)

    def test_part_number_supersedes_self_reference_works_through_the_record_api(self):
        original = self._create("part_number", number="OEM-1")
        superseding = self._create("part_number", number="OEM-2", supersedes=original["id"])
        self.assertEqual(
            superseding[str(self._relation("part_number", "supersedes").id)], original["id"]
        )

    def test_full_inventory_purchasing_and_sales_workflow(self):
        part = self._create("part", name="Brake Pad")
        warehouse_a = self._create("warehouse", name="Main", code="MAIN")
        warehouse_b = self._create("warehouse", name="Overflow", code="OVERFLOW")

        # One inventory row per (part, warehouse); a second row for the
        # same pair is genuinely rejected by the real composite constraint.
        # The template declares a quantity ledger (ADR-0016): a balance starts at
        # zero and only changes through Stock Movements, never by a direct write.
        self._create("inventory", part=part["id"], warehouse=warehouse_a["id"], quantity_on_hand=0)
        duplicate = self.client.post(
            self._records_url("inventory"),
            {
                str(self._relation("inventory", "part").id): part["id"],
                str(self._relation("inventory", "warehouse").id): warehouse_a["id"],
            },
            format="json",
        )
        self.assertEqual(duplicate.status_code, 400, duplicate.data)
        self._create("inventory", part=part["id"], warehouse=warehouse_b["id"], quantity_on_hand=0)
        for warehouse, quantity in ((warehouse_a, 10), (warehouse_b, 5)):
            self._create(
                "stock_movement",
                stock_movement_part=part["id"],
                stock_movement_warehouse=warehouse["id"],
                quantity_delta=quantity,
                movement_type="receive",
            )
        on_hand = self._field("inventory", "quantity_on_hand").id
        balances = sorted(
            row[str(on_hand)] for row in self.client.get(self._records_url("inventory")).data["results"]
        )
        self.assertEqual(balances, [5, 10])

        supplier = self._create("supplier", name="Acme Parts Co")
        purchase_order = self._create("purchase_order", supplier=supplier["id"], status="draft")
        self._create(
            "purchase_order_line",
            purchase_order=purchase_order["id"],
            purchase_order_line_part=part["id"],
            quantity=20, unit_cost="5.00", line_total="100.00",
        )

        customer = self._create("customer", name="Downtown Garage")
        sales_order = self._create("sales_order", customer=customer["id"], status="draft")
        self._create(
            "sales_order_line",
            sales_order_line_sales_order=sales_order["id"],
            sales_order_line_part=part["id"],
            quantity=2, unit_price="15.00", line_total="30.00",
        )
        invoice = self._create(
            "invoice",
            invoice_sales_order=sales_order["id"],
            invoice_number="INV-0001",
            amount_due="30.00",
            status="unpaid",
        )
        self.assertEqual(invoice[str(self._field("invoice", "invoice_number").id)], "INV-0001")

        vehicle = self._create("vehicle", make="Toyota", model="Corolla", year=2020)
        compatible_relation = self._relation("part", "compatible_vehicles")
        linked = self.client.patch(
            f"{self._records_url('part')}{part['id']}/",
            {str(compatible_relation.id): [vehicle["id"]]},
            format="json",
        )
        self.assertEqual(linked.status_code, 200, linked.data)
        self.assertEqual(linked.data[str(compatible_relation.id)], [vehicle["id"]])
