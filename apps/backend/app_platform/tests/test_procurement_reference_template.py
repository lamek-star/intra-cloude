"""Phase 8 -- Procurement reference application
(docs/implementation/APP_PLATFORM_ROADMAP.md,
docs/implementation/APP_PLATFORM_PHASE8.md). Same bar as Phase 4's Spare
Parts template test suite: draft validity, install-time metadata, real
Postgres schema on provisioning (relationship-only composite constraint,
nullable set_null relationships), and a realistic workflow through the
real record API.

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
from app_platform.reference_templates import procurement_reference_definition
from app_platform.runtime_plan import plan_runtime
from app_platform.tests.test_foundation import project_for
from databases.models import DBIndex
from organizations.services import create_organization


class DraftValidationTests(TestCase):
    def test_the_draft_validates_cleanly(self):
        definition = validate_definition(procurement_reference_definition())
        self.assertEqual(len(definition["models"]), 9)
        self.assertEqual(len(definition["relationships"]), 11)

    def test_goods_receipt_line_has_a_relationship_only_composite_constraint(self):
        definition = validate_definition(procurement_reference_definition())
        [goods_receipt_line] = [m for m in definition["models"] if m["key"] == "goods_receipt_line"]
        [constraint] = goods_receipt_line["constraints"]
        self.assertEqual(constraint["field_ids"], [])
        self.assertEqual(len(constraint["relationship_ids"]), 2)


class InstallTests(TestCase):
    def setUp(self):
        call_command("seed_permissions", verbosity=0)
        self.owner = User.objects.create_user(email="procurement-install@example.com")
        self.org = create_organization(name="Procurement Install Org", created_by=self.owner)
        self.project = project_for(self.owner, self.org)

    def _install(self):
        template = templates.create_template(
            self.owner, self.org, {"label": "Procurement", "draft": procurement_reference_definition()}
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
                "vendor", "purchase_requisition", "requisition_line", "purchase_order",
                "purchase_order_line", "goods_receipt", "goods_receipt_line",
                "vendor_invoice", "approval",
            },
        )

    def test_purchase_order_requisition_is_nullable_on_delete(self):
        instance = self._install()
        purchase_order = instance.models.get(key="purchase_order")
        relation = purchase_order.outgoing.get(key="purchase_order_requisition")
        self.assertEqual(relation.deletion_policy, "set_null")


class ProvisioningAndWorkflowTests(TransactionTestCase):
    databases = {"default", "tenant"}

    def setUp(self):
        call_command("seed_permissions", verbosity=0)
        self.actor = User.objects.create_user(email="procurement-workflow@example.com")
        self.org = create_organization(name="Procurement Workflow Org", created_by=self.actor)
        self.project = project_for(self.actor, self.org)
        template = templates.create_template(
            self.actor, self.org, {"label": "Procurement", "draft": procurement_reference_definition()}
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

    def test_goods_receipt_line_constraint_is_real_in_the_provisioned_schema(self):
        constraint = self.models["goods_receipt_line"].constraints.get(key="receipt_order_line_unique")
        index_id = self.receipt.bindings["constraints"][str(constraint.id)]
        index = DBIndex.objects.get(pk=index_id)
        self.assertTrue(index.is_unique)

    def test_full_requisition_to_receipt_workflow(self):
        vendor = self._create("vendor", name="Global Supplies Inc")
        requisition = self._create("purchase_requisition", requested_by="Ops Team", status="draft")
        requisition_line = self._create(
            "requisition_line", requisition_line_requisition=requisition["id"],
            item_description="Office chairs", quantity=10, estimated_cost="150.00",
        )
        self._create(
            "approval",
            approval_requisition=requisition["id"],
            approver_name="Finance Lead",
            decision="approved",
        )

        purchase_order = self._create(
            "purchase_order",
            purchase_order_vendor=vendor["id"],
            purchase_order_requisition=requisition["id"],
            status="ordered",
            total_amount="1500.00",
        )
        purchase_order_line = self._create(
            "purchase_order_line", purchase_order_line_purchase_order=purchase_order["id"],
            purchase_order_line_requisition_line=requisition_line["id"],
            quantity=10, unit_cost="150.00", line_total="1500.00",
        )

        goods_receipt = self._create(
            "goods_receipt", goods_receipt_purchase_order=purchase_order["id"],
            receipt_number="GR-0001", received_date="2026-09-16",
        )
        self._create(
            "goods_receipt_line",
            goods_receipt_line_goods_receipt=goods_receipt["id"],
            goods_receipt_line_purchase_order_line=purchase_order_line["id"],
            quantity_received=10,
        )
        # One receipt line per (goods receipt, PO line) -- a duplicate is
        # genuinely rejected by the real composite constraint.
        duplicate = self.client.post(
            self._records_url("goods_receipt_line"),
            {
                str(
                    self._relation("goods_receipt_line", "goods_receipt_line_goods_receipt").id
                ): goods_receipt["id"],
                str(
                    self._relation("goods_receipt_line", "goods_receipt_line_purchase_order_line").id
                ): purchase_order_line["id"],
                str(self._field("goods_receipt_line", "quantity_received").id): 10,
            },
            format="json",
        )
        self.assertEqual(duplicate.status_code, 400, duplicate.data)

        vendor_invoice = self._create(
            "vendor_invoice",
            vendor_invoice_purchase_order=purchase_order["id"],
            vendor_invoice_vendor=vendor["id"],
            invoice_number="VINV-0001",
            amount="1500.00",
            status="unpaid",
        )
        self.assertEqual(vendor_invoice[str(self._field("vendor_invoice", "invoice_number").id)], "VINV-0001")
