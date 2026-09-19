"""Atomic receive/sell business operations on the real Spare Parts template
(ADR-0016, Local Edition P0: no partial business transaction commit).

The template declares a quantity ledger, so provisioning binds it with no API
call. A "sale" is an order, its line, the stock movement and an invoice: these
tests prove it commits as one unit or not at all, against real PostgreSQL --
including real concurrent sales and a permission denial midway through.
"""

import uuid
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from django.core.management import call_command
from django.db import connections
from django.test import SimpleTestCase, TransactionTestCase
from django.urls import reverse
from psycopg import sql
from rest_framework.exceptions import ValidationError
from rest_framework.test import APIClient

from accounts.models import User
from app_platform import instances, provisioning, quantity_ledger, templates
from app_platform.definitions import validate_definition
from app_platform.models import QuantityLedgerBinding
from app_platform.reference_templates.spare_parts import spare_parts_reference_definition
from app_platform.runtime_plan import plan_runtime
from app_platform.tests.test_foundation import project_for
from app_platform.tests.test_quantity_ledger import _LedgerFixture
from organizations.models import Membership
from organizations.services import create_organization


class TransactionBase(TransactionTestCase):
    databases = {"default", "tenant"}

    def setUp(self):
        call_command("seed_permissions", verbosity=0)
        self.actor = User.objects.create_user(email="shop-owner@example.com")
        self.org = create_organization(name="Shop Org", created_by=self.actor)
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
        self.part = self._create("part", name="Oil Filter")
        self.warehouse = self._create("warehouse", name="Main", code="MAIN")
        self.customer = self._create("customer", name="Walk-in")

    def tearDown(self):
        with connections["tenant"].cursor() as cursor:
            cursor.execute(
                sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE").format(sql.Identifier(self.plan["schema_name"]))
            )
        super().tearDown()

    # -- helpers ---------------------------------------------------------
    def _definition_id(self, model_key, key):
        model = self.models[model_key]
        field = model.fields.filter(key=key).first()
        return str(field.id if field is not None else model.outgoing.get(key=key).id)

    def _payload(self, model_key, **values):
        return {self._definition_id(model_key, key): value for key, value in values.items()}

    def _create(self, model_key, client=None, **values):
        response = (client or self.client).post(
            f"/api/v1/app-models/{self.models[model_key].id}/records/",
            self._payload(model_key, **values),
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)
        return response.data

    def _records(self, model_key):
        response = self.client.get(f"/api/v1/app-models/{self.models[model_key].id}/records/?limit=100")
        self.assertEqual(response.status_code, 200, response.data)
        return response.data["results"]

    def _balance(self):
        rows = self._records("inventory")
        return rows[0][self._definition_id("inventory", "quantity_on_hand")] if rows else None

    def _op(self, op, model_key, ref=None, **values):
        operation = {
            "op": op,
            "model": str(self.models[model_key].id),
            "data": self._payload(model_key, **values),
        }
        if ref:
            operation["ref"] = ref
        return operation

    def _movement_op(self, delta, movement_type, warehouse=None):
        return self._op(
            "create",
            "stock_movement",
            stock_movement_part=self.part["id"],
            stock_movement_warehouse=warehouse or self.warehouse["id"],
            quantity_delta=delta,
            movement_type=movement_type,
        )

    def _sale_ops(self, quantity, invoice_number="INV-1"):
        return [
            self._op("create", "sales_order", ref="order", customer=self.customer["id"], status="confirmed"),
            self._op(
                "create",
                "sales_order_line",
                sales_order_line_sales_order={"$ref": "order"},
                sales_order_line_part=self.part["id"],
                quantity=quantity,
                unit_price="15.00",
                line_total=f"{15 * quantity}.00",
            ),
            self._movement_op(-quantity, "sale"),
            self._op(
                "create",
                "invoice",
                invoice_number=invoice_number,
                invoice_sales_order={"$ref": "order"},
                amount_due=f"{15 * quantity}.00",
                status="unpaid",
            ),
        ]

    def _post(self, operations, client=None, key=None):
        extra = {"HTTP_IDEMPOTENCY_KEY": key} if key else {}
        return (client or self.client).post(
            f"/api/v1/app-instances/{self.instance.id}/transactions/",
            {"operations": operations},
            format="json",
            **extra,
        )

    def _receive(self, quantity):
        response = self._post([self._movement_op(quantity, "receive")])
        self.assertEqual(response.status_code, 201, response.data)
        return response

    def _assert_no_sale_documents(self):
        for model_key in ("sales_order", "sales_order_line", "invoice"):
            self.assertEqual(self._records(model_key), [], model_key)


class TemplateLedgerTests(TransactionBase):
    def test_provisioning_bound_the_templates_declared_ledger_with_no_api_call(self):
        binding = QuantityLedgerBinding.objects.get(instance=self.instance)
        self.assertEqual(binding.balance_field.key, "quantity_on_hand")
        self.assertEqual(binding.movement_field.key, "quantity_delta")
        self.assertEqual(binding.dimensions.count(), 2)
        self.assertFalse(binding.allow_negative)

    def test_a_direct_inventory_edit_is_rejected_so_stock_only_changes_through_movements(self):
        row = self._create(
            "inventory", part=self.part["id"], warehouse=self.warehouse["id"], quantity_on_hand=0
        )
        response = self.client.patch(
            f"/api/v1/app-models/{self.models['inventory'].id}/records/{row['id']}/",
            self._payload("inventory", quantity_on_hand=999),
            format="json",
        )
        self.assertEqual(response.status_code, 400, response.data)
        self.assertEqual(self._balance(), 0)


class ReceiveAndSellTests(TransactionBase):
    def test_receive_100_then_sell_5_leaves_95_with_a_complete_sales_document(self):
        self._receive(100)
        self.assertEqual(self._balance(), 100)

        response = self._post(self._sale_ops(5))
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual([r["operation"] for r in response.data["results"]], [0, 1, 2, 3])

        self.assertEqual(self._balance(), 95)
        self.assertEqual(len(self._records("sales_order")), 1)
        self.assertEqual(len(self._records("sales_order_line")), 1)
        self.assertEqual(len(self._records("invoice")), 1)
        self.assertEqual(len(self._records("stock_movement")), 2)
        binding = QuantityLedgerBinding.objects.get(instance=self.instance)
        self.assertEqual(quantity_ledger.reconcile(binding), [])

        order_id = response.data["results"][0]["record"]["id"]
        invoice = self._records("invoice")[0]
        self.assertEqual(invoice[self._definition_id("invoice", "invoice_sales_order")], order_id)

    def test_selling_the_exact_remaining_stock_reaches_zero(self):
        self._receive(5)
        self.assertEqual(self._post(self._sale_ops(5)).status_code, 201)
        self.assertEqual(self._balance(), 0)

    def test_receiving_against_a_purchase_order_updates_it_in_the_same_transaction(self):
        supplier = self._create("supplier", name="Acme")
        order = self._create("purchase_order", supplier=supplier["id"], status="draft")
        response = self._post(
            [
                {
                    "op": "update",
                    "model": str(self.models["purchase_order"].id),
                    "record": order["id"],
                    "data": self._payload("purchase_order", status="received"),
                },
                self._movement_op(20, "receive"),
            ]
        )
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(self._balance(), 20)
        status_id = self._definition_id("purchase_order", "status")
        self.assertEqual(self._records("purchase_order")[0][status_id], "received")


class AtomicityTests(TransactionBase):
    def test_a_sale_the_stock_cannot_cover_leaves_no_partial_documents(self):
        self._receive(5)
        response = self._post(self._sale_ops(6))
        self.assertEqual(response.status_code, 400, response.data)
        self.assertEqual(response.data["operation"], 2)  # the movement, after order+line were created
        self.assertIn("negative", response.data["detail"])
        self._assert_no_sale_documents()
        self.assertEqual(self._balance(), 5)
        self.assertEqual(len(self._records("stock_movement")), 1)

    def test_a_failing_later_operation_rolls_back_an_earlier_update(self):
        supplier = self._create("supplier", name="Acme")
        order = self._create("purchase_order", supplier=supplier["id"], status="draft")
        response = self._post(
            [
                {
                    "op": "update",
                    "model": str(self.models["purchase_order"].id),
                    "record": order["id"],
                    "data": self._payload("purchase_order", status="received"),
                },
                self._movement_op(20, "receive", warehouse=str(uuid.uuid4())),  # no such warehouse
            ]
        )
        self.assertEqual(response.status_code, 400, response.data)
        self.assertEqual(response.data["operation"], 1)
        status_id = self._definition_id("purchase_order", "status")
        self.assertEqual(self._records("purchase_order")[0][status_id], "draft")
        self.assertEqual(self._records("stock_movement"), [])

    def test_an_unknown_reference_is_rejected_and_nothing_persists(self):
        operations = self._sale_ops(1)
        operations[1]["data"][self._definition_id("sales_order_line", "sales_order_line_sales_order")] = {
            "$ref": "nope"
        }
        response = self._post(operations)
        self.assertEqual(response.status_code, 400, response.data)
        self.assertEqual(response.data["operation"], 1)
        self._assert_no_sale_documents()

    def test_a_forward_reference_is_rejected(self):
        operations = self._sale_ops(1)
        operations[0], operations[1] = operations[1], operations[0]  # line before the order it references
        response = self._post(operations)
        self.assertEqual(response.status_code, 400, response.data)
        self._assert_no_sale_documents()

    def test_a_duplicate_reference_name_is_rejected(self):
        operations = self._sale_ops(1)
        operations[3]["ref"] = "order"
        self._receive(5)
        response = self._post(operations)
        self.assertEqual(response.status_code, 400, response.data)
        self.assertEqual(response.data["operation"], 3)
        self._assert_no_sale_documents()
        self.assertEqual(self._balance(), 5)

    def test_an_empty_or_oversized_transaction_is_rejected(self):
        self.assertEqual(self._post([]).status_code, 400)
        many = [self._movement_op(1, "receive")] * 101
        self.assertEqual(self._post(many).status_code, 400)
        self.assertEqual(self._records("stock_movement"), [])

    def test_a_model_from_another_instance_is_unknown(self):
        foreign = _LedgerFixture.build("foreign-tx@example.com", "Foreign Tx Org")
        try:
            operation = {
                "op": "create",
                "model": str(foreign.item_model.id),
                "data": {str(foreign.item_model.fields.get(key="name").id): "Intruder"},
            }
            response = self._post([self._movement_op(5, "receive"), operation])
            self.assertEqual(response.status_code, 400, response.data)
            self.assertEqual(response.data["operation"], 1)
            self.assertEqual(self._records("stock_movement"), [])
            self.assertEqual(foreign.balance(), None)
        finally:
            foreign.drop_schema()


class IdempotencyTests(TransactionBase):
    def test_replaying_a_sale_with_the_same_key_does_not_sell_twice(self):
        self._receive(100)
        first = self._post(self._sale_ops(5), key="sale-0001")
        second = self._post(self._sale_ops(5), key="sale-0001")
        self.assertEqual(first.status_code, 201, first.data)
        self.assertEqual(second.status_code, 201, second.data)
        self.assertEqual(first.json(), second.json())
        self.assertEqual(self._balance(), 95)
        self.assertEqual(len(self._records("sales_order")), 1)
        self.assertEqual(len(self._records("stock_movement")), 2)

    def test_reusing_a_key_for_a_different_sale_is_rejected(self):
        self._receive(100)
        self.assertEqual(self._post(self._sale_ops(5), key="sale-0002").status_code, 201)
        response = self._post(self._sale_ops(7), key="sale-0002")
        self.assertEqual(response.status_code, 409, response.data)  # the journal's own conflict contract
        self.assertEqual(self._balance(), 95)
        self.assertEqual(len(self._records("sales_order")), 1)


class AuthorizationTests(TransactionBase):
    def setUp(self):
        super().setUp()
        self.cashier = User.objects.create_user(email="cashier@example.com")
        Membership.objects.create(user=self.cashier, organization=self.org, status=Membership.Status.ACTIVE)
        self.cashier_client = APIClient()
        self.cashier_client.force_authenticate(self.cashier)
        self._receive(50)

    def _grant(self, *model_keys, level="write"):
        for model_key in model_keys:
            response = self.client.post(
                reverse("share-grant-list-create", args=[self.org.id]),
                {
                    "resource_type": "app_model",
                    "resource_id": str(self.models[model_key].id),
                    "principal_type": "user",
                    "user_id": str(self.cashier.id),
                    "level": level,
                },
                format="json",
            )
            self.assertEqual(response.status_code, 201, response.data)

    def test_a_member_with_no_grants_cannot_run_a_transaction(self):
        response = self._post(self._sale_ops(1), client=self.cashier_client)
        self.assertEqual(response.status_code, 403, response.data)
        self.assertEqual(response.data["operation"], 0)
        self._assert_no_sale_documents()

    def test_missing_write_on_the_movement_model_denies_the_sale_and_undoes_earlier_steps(self):
        self._grant("sales_order", "sales_order_line", "invoice", "inventory")
        response = self._post(self._sale_ops(1), client=self.cashier_client)
        self.assertEqual(response.status_code, 403, response.data)
        self.assertEqual(response.data["operation"], 2)  # order and line succeeded first, then rolled back
        self._assert_no_sale_documents()
        self.assertEqual(self._balance(), 50)

    def test_write_on_the_movement_model_alone_is_not_enough_to_change_a_balance(self):
        self._grant("sales_order", "sales_order_line", "invoice", "stock_movement")
        response = self._post(self._sale_ops(1), client=self.cashier_client)
        self.assertEqual(response.status_code, 403, response.data)
        self._assert_no_sale_documents()
        self.assertEqual(self._balance(), 50)

    def test_a_member_with_every_needed_grant_can_sell(self):
        self._grant("sales_order", "sales_order_line", "invoice", "stock_movement", "inventory")
        response = self._post(self._sale_ops(1), client=self.cashier_client)
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(self._balance(), 49)

    def test_the_transaction_endpoint_is_not_opted_in_for_bearer_token_clients(self):
        # FoundationView denies any method not listed here to an Application's
        # bearer token; this endpoint deliberately lists none.
        from app_platform.record_views import TransactionView

        self.assertEqual(TransactionView.service_account_methods, frozenset())


class ConcurrentSalesTests(TransactionBase):
    def test_concurrent_sales_never_oversell_and_leave_no_orphan_documents(self):
        self._receive(50)
        barrier = Barrier(5)
        operations_by_thread = [self._sale_ops(20, invoice_number=f"INV-{i}") for i in range(5)]
        url = f"/api/v1/app-instances/{self.instance.id}/transactions/"

        def run(operations):
            connections.close_all()
            try:
                client = APIClient()
                client.force_authenticate(self.actor)
                barrier.wait(timeout=10)
                return client.post(url, {"operations": operations}, format="json")
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=5) as pool:
            responses = [
                f.result(timeout=60) for f in [pool.submit(run, ops) for ops in operations_by_thread]
            ]
        succeeded = [r for r in responses if r.status_code == 201]
        rejected = [r for r in responses if r.status_code == 400]
        self.assertEqual(len(succeeded) + len(rejected), 5, [r.status_code for r in responses])
        self.assertEqual(len(succeeded), 2)  # floor(50 / 20)
        self.assertEqual(self._balance(), 10)
        # A rejected sale leaves nothing behind: exactly one order, line and
        # invoice per SUCCESSFUL sale, and 1 receipt + 2 sale movements.
        self.assertEqual(len(self._records("sales_order")), 2)
        self.assertEqual(len(self._records("sales_order_line")), 2)
        self.assertEqual(len(self._records("invoice")), 2)
        self.assertEqual(len(self._records("stock_movement")), 3)
        binding = QuantityLedgerBinding.objects.get(instance=self.instance)
        self.assertEqual(quantity_ledger.reconcile(binding), [])


class LedgerDeclarationValidationTests(SimpleTestCase):
    """A broken declaration must be rejected when the template is saved, not
    discovered as a failed provisioning on a customer's machine."""

    def setUp(self):
        self.definition = spare_parts_reference_definition()
        self.ledger = self.definition["quantity_ledgers"][0]

    def _rejects(self):
        with self.assertRaises(ValidationError):
            validate_definition(self.definition)

    def test_the_shipped_declaration_is_valid(self):
        self.assertEqual(len(validate_definition(self.definition)["quantity_ledgers"]), 1)

    def test_a_definition_without_a_declaration_keeps_its_shape(self):
        del self.definition["quantity_ledgers"]
        self.assertNotIn("quantity_ledgers", validate_definition(self.definition))

    def test_a_single_dimension_is_rejected(self):
        self.ledger["dimensions"] = self.ledger["dimensions"][:1]
        self._rejects()

    def test_an_unknown_field_is_rejected(self):
        self.ledger["balance_field"] = str(uuid.uuid4())
        self._rejects()

    def test_a_balance_field_that_does_not_default_to_zero_is_rejected(self):
        inventory = next(m for m in self.definition["models"] if m["key"] == "inventory")
        next(f for f in inventory["fields"] if f["key"] == "quantity_on_hand")["default_value"] = 5
        self._rejects()

    def test_a_non_integer_movement_field_is_rejected(self):
        movement = next(m for m in self.definition["models"] if m["key"] == "stock_movement")
        next(f for f in movement["fields"] if f["key"] == "quantity_delta")["data_type"] = "text"
        self._rejects()

    def test_a_balance_model_without_the_matching_composite_constraint_is_rejected(self):
        inventory = next(m for m in self.definition["models"] if m["key"] == "inventory")
        inventory["constraints"] = []
        self._rejects()

    def test_mismatched_dimension_targets_are_rejected(self):
        first, second = self.ledger["dimensions"]
        second["movement_relationship"] = first["movement_relationship"]
        self._rejects()


class OlderTemplateVersionTests(TransactionBase):
    """An already-published version that declares no ledger must still install
    and provision exactly as before -- no ledger, no behavior change."""

    def setUp(self):
        call_command("seed_permissions", verbosity=0)
        self.actor = User.objects.create_user(email="legacy-owner@example.com")
        self.org = create_organization(name="Legacy Org", created_by=self.actor)
        self.project = project_for(self.actor, self.org)
        definition = spare_parts_reference_definition()
        del definition["quantity_ledgers"]
        template = templates.create_template(self.actor, self.org, {"label": "Legacy", "draft": definition})
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

    def test_no_ledger_is_bound_and_inventory_stays_directly_writable(self):
        self.assertFalse(QuantityLedgerBinding.objects.filter(instance=self.instance).exists())
        part = self._create("part", name="Legacy Part")
        warehouse = self._create("warehouse", name="Main", code="MAIN")
        self._create("inventory", part=part["id"], warehouse=warehouse["id"], quantity_on_hand=10)
        self.assertEqual(self._balance(), 10)


class MovementTimestampContractTests(TransactionBase):
    """The browser stamps each movement with `occurred_at`. The platform's datetime contract
    (databases/formats.py, shared with the CSV importer) is naive `YYYY-MM-DDTHH:MM:SS`; the
    browser's own `Date.toISOString()` form (`...T13:35:00.646Z`) is refused. The refusal is safe --
    nothing is committed -- but it means a client must send the documented form. Found by the
    real-stack browser journey; the API had never been exercised with `occurred_at`."""

    def _receive_at(self, stamp):
        operation = self._movement_op(100, "receive")
        operation["data"][self._definition_id("stock_movement", "occurred_at")] = stamp
        return self._post([operation])

    def test_the_documented_timestamp_form_is_accepted_and_returned_unchanged(self):
        response = self._receive_at("2026-09-19T13:35:00")
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(self._balance(), 100)
        movement = self._records("stock_movement")[0]
        stored = str(movement[self._definition_id("stock_movement", "occurred_at")]).replace(" ", "T")
        self.assertTrue(stored.startswith("2026-09-19T13:35:00"), stored)

    def test_an_iso_timestamp_with_milliseconds_and_a_zone_is_refused_and_commits_nothing(self):
        response = self._receive_at("2026-09-19T13:35:00.646Z")
        self.assertEqual(response.status_code, 400, response.data)
        self.assertIn("ISO datetime", response.data["detail"])
        self.assertEqual(self._records("stock_movement"), [])
        self.assertIsNone(self._balance())
