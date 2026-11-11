"""ADR-0016's closing half: the generic integer quantity ledger's atomicity,
concurrency, and bypass-prevention guarantees over a real Postgres tenant
schema -- not mocked. A minimal Item/Warehouse/Inventory/StockMovement
runtime, shaped exactly like reference_templates/spare_parts.py's own
Inventory(Part, Warehouse), proves: receive, sell, rollback after an
induced mid-transaction failure, insufficient-stock rejection, concurrent
receive/sell, duplicate/replayed requests via the existing Idempotency-Key
mechanism, cross-organization isolation, and that the invariant holds even
for a direct SQL write that never goes through records.py at all."""

import uuid
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest.mock import patch

from django.core.management import call_command
from django.db import IntegrityError, connections, transaction
from django.test import TransactionTestCase
from psycopg import sql
from rest_framework.exceptions import ValidationError
from rest_framework.test import APIClient

from accounts.models import User
from app_platform import instances, provisioning, quantity_ledger, templates
from app_platform.reference_templates._helpers import _field, _model, _relationship
from app_platform.runtime_plan import plan_runtime
from app_platform.tests.test_foundation import project_for
from organizations.services import create_organization


def _ledger_sample():
    item_id, warehouse_id, inventory_id, movement_id = (str(uuid.uuid4()) for _ in range(4))
    quantity_id, quantity_field = _field("quantity", "Quantity", "integer", required=True, default_value=0)
    delta_id, delta_field = _field("delta", "Delta", "integer", required=True)
    item = _model(item_id, "item", "Item", [_field("name", "Name", "text", required=True)])
    warehouse = _model(
        warehouse_id, "warehouse", "Warehouse", [_field("name", "Name", "text", required=True)]
    )
    inventory = _model(inventory_id, "inventory", "Inventory", [(quantity_id, quantity_field)])
    movement = _model(movement_id, "stock_movement", "Stock Movement", [(delta_id, delta_field)])

    inventory_item_rel = _relationship("inventory_item", "Item", inventory_id, item_id)
    inventory_warehouse_rel = _relationship("inventory_warehouse", "Warehouse", inventory_id, warehouse_id)
    movement_item_rel = _relationship("movement_item", "Item", movement_id, item_id)
    movement_warehouse_rel = _relationship("movement_warehouse", "Warehouse", movement_id, warehouse_id)
    inventory["constraints"] = [
        {
            "key": "item_warehouse_unique",
            "label": "One inventory row per Item and Warehouse",
            "field_ids": [],
            "relationship_ids": [inventory_item_rel["id"], inventory_warehouse_rel["id"]],
        }
    ]
    return {
        "schema_version": 1,
        "models": [item, warehouse, inventory, movement],
        "relationships": [
            inventory_item_rel,
            inventory_warehouse_rel,
            movement_item_rel,
            movement_warehouse_rel,
        ],
    }


class LedgerTestBase(TransactionTestCase):
    databases = {"default", "tenant"}

    def setUp(self):
        call_command("seed_permissions", verbosity=0)
        self.actor = User.objects.create_user(email="ledger-owner@example.com")
        self.org = create_organization(name="Ledger Org", created_by=self.actor)
        self.project = project_for(self.actor, self.org)

        template = templates.create_template(
            self.actor, self.org, {"label": "Ledger App", "draft": _ledger_sample()}
        )
        version = templates.publish_template(self.actor, template)
        self.instance = instances.install(
            self.actor, self.project, {"label": "Runtime", "template_version": str(version.id)}
        )
        self.item_model = self.instance.models.get(key="item")
        self.warehouse_model = self.instance.models.get(key="warehouse")
        self.inventory_model = self.instance.models.get(key="inventory")
        self.movement_model = self.instance.models.get(key="stock_movement")
        self.quantity_field = self.inventory_model.fields.get(key="quantity")
        self.delta_field = self.movement_model.fields.get(key="delta")
        self.inventory_item_rel = self.instance.relationships.get(key="inventory_item")
        self.inventory_warehouse_rel = self.instance.relationships.get(key="inventory_warehouse")
        self.movement_item_rel = self.instance.relationships.get(key="movement_item")
        self.movement_warehouse_rel = self.instance.relationships.get(key="movement_warehouse")

        self.plan = plan_runtime(self.actor, self.instance)
        provisioning.reserve(self.actor, self.instance, self.plan["fingerprint"])
        self.receipt = provisioning.execute(self.instance.id, self.actor)

        self.client = APIClient()
        self.client.force_authenticate(self.actor)

        self.item_id = self._create_item("Widget")
        self.warehouse_id = self._create_warehouse("Main")

        self.binding = quantity_ledger.bind(
            self.actor,
            self.instance,
            {
                "balance_model_id": str(self.inventory_model.id),
                "balance_field_id": str(self.quantity_field.id),
                "movement_model_id": str(self.movement_model.id),
                "movement_field_id": str(self.delta_field.id),
                "dimensions": [
                    {
                        "balance_relationship_id": str(self.inventory_item_rel.id),
                        "movement_relationship_id": str(self.movement_item_rel.id),
                    },
                    {
                        "balance_relationship_id": str(self.inventory_warehouse_rel.id),
                        "movement_relationship_id": str(self.movement_warehouse_rel.id),
                    },
                ],
            },
        )

    def tearDown(self):
        with connections["tenant"].cursor() as cursor:
            cursor.execute(
                sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE").format(sql.Identifier(self.plan["schema_name"]))
            )
        super().tearDown()

    def _create_item(self, name):
        response = self.client.post(
            f"/api/v1/app-models/{self.item_model.id}/records/",
            {str(self.item_model.fields.get(key="name").id): name},
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)
        return response.data["id"]

    def _create_warehouse(self, name):
        response = self.client.post(
            f"/api/v1/app-models/{self.warehouse_model.id}/records/",
            {str(self.warehouse_model.fields.get(key="name").id): name},
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)
        return response.data["id"]

    def _movement(self, delta, *, item_id=None, warehouse_id=None, idempotency_key=None):
        extra = {"HTTP_IDEMPOTENCY_KEY": idempotency_key} if idempotency_key else {}
        return self.client.post(
            f"/api/v1/app-models/{self.movement_model.id}/records/",
            {
                str(self.delta_field.id): delta,
                str(self.movement_item_rel.id): item_id or self.item_id,
                str(self.movement_warehouse_rel.id): warehouse_id or self.warehouse_id,
            },
            format="json",
            **extra,
        )

    def _inventory_rows(self):
        response = self.client.get(f"/api/v1/app-models/{self.inventory_model.id}/records/")
        self.assertEqual(response.status_code, 200, response.data)
        return response.data["results"]

    def _movement_rows(self):
        response = self.client.get(f"/api/v1/app-models/{self.movement_model.id}/records/")
        self.assertEqual(response.status_code, 200, response.data)
        return response.data["results"]

    def _balance(self):
        rows = self._inventory_rows()
        if not rows:
            return None
        return rows[0][str(self.quantity_field.id)]


class ReceiveSellTests(LedgerTestBase):
    def test_receive_creates_balance_row_atomically_with_its_movement(self):
        response = self._movement(100)
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(self._balance(), 100)
        self.assertEqual(len(self._movement_rows()), 1)

    def test_sell_decrements_an_existing_balance(self):
        self._movement(100)
        response = self._movement(-30)
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(self._balance(), 70)
        self.assertEqual(len(self._movement_rows()), 2)

    def test_reversing_movement_corrects_an_earlier_one(self):
        self._movement(100)
        self._movement(-40)
        response = self._movement(40)  # explicit reversal, per ADR-0016
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(self._balance(), 100)


class InsufficientStockTests(LedgerTestBase):
    def test_selling_below_zero_is_rejected_and_nothing_commits(self):
        response = self._movement(-5)
        self.assertEqual(response.status_code, 400, response.data)
        self.assertIn("negative", response.data["detail"])
        self.assertEqual(self._inventory_rows(), [])
        self.assertEqual(self._movement_rows(), [])

    def test_selling_below_zero_after_a_partial_receive_is_rejected(self):
        self._movement(10)
        response = self._movement(-11)
        self.assertEqual(response.status_code, 400, response.data)
        self.assertEqual(self._balance(), 10)  # unchanged -- the rejected movement never committed
        self.assertEqual(len(self._movement_rows()), 1)


class RollbackTests(LedgerTestBase):
    def test_a_failure_after_the_trigger_runs_rolls_back_both_effects(self):
        # operation_journal.append runs synchronously inside the same
        # tenant transaction as row_ops.insert_row -- an unrelated failure
        # there, after the movement trigger already upserted the balance,
        # must still roll back the whole transaction: the balance upsert
        # is not somehow detached from the surrounding transaction just
        # because it happened inside a trigger.
        with patch("app_platform.operation_journal.append", side_effect=OSError("induced failure")):
            response = self._movement(100)
        self.assertEqual(response.status_code, 500)
        self.assertEqual(self._inventory_rows(), [])
        self.assertEqual(self._movement_rows(), [])


class IdempotencyTests(LedgerTestBase):
    def test_a_replayed_request_does_not_double_apply_the_ledger_effect(self):
        first = self._movement(100, idempotency_key="receive-1")
        second = self._movement(100, idempotency_key="receive-1")
        self.assertEqual(first.status_code, 201, first.data)
        self.assertEqual(second.status_code, 201, second.data)
        # A replayed response comes back from operation_journal's stored
        # JSON, not a fresh serialization -- compare rendered JSON, not
        # .data, the same distinction test_record_idempotency.py's own
        # replay test already draws (a value like `id` is a native UUID
        # object pre-render but a plain string once round-tripped through
        # JSON).
        self.assertEqual(first.json(), second.json())
        self.assertEqual(self._balance(), 100)
        self.assertEqual(len(self._movement_rows()), 1)


class ConcurrencyTests(LedgerTestBase):
    def test_concurrent_receives_on_the_same_dimension_settle_to_the_exact_sum(self):
        barrier = Barrier(5)

        def run():
            connections.close_all()
            try:
                client = APIClient()
                client.force_authenticate(self.actor)
                barrier.wait(timeout=10)
                return client.post(
                    f"/api/v1/app-models/{self.movement_model.id}/records/",
                    {
                        str(self.delta_field.id): 10,
                        str(self.movement_item_rel.id): self.item_id,
                        str(self.movement_warehouse_rel.id): self.warehouse_id,
                    },
                    format="json",
                )
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=5) as pool:
            responses = [future.result(timeout=30) for future in [pool.submit(run) for _ in range(5)]]
        self.assertEqual([r.status_code for r in responses], [201] * 5)
        self.assertEqual(self._balance(), 50)
        self.assertEqual(len(self._movement_rows()), 5)

    def test_concurrent_sells_never_drive_the_balance_negative(self):
        self._movement(50)
        barrier = Barrier(5)

        def run():
            connections.close_all()
            try:
                client = APIClient()
                client.force_authenticate(self.actor)
                barrier.wait(timeout=10)
                return client.post(
                    f"/api/v1/app-models/{self.movement_model.id}/records/",
                    {
                        str(self.delta_field.id): -20,
                        str(self.movement_item_rel.id): self.item_id,
                        str(self.movement_warehouse_rel.id): self.warehouse_id,
                    },
                    format="json",
                )
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=5) as pool:
            responses = [future.result(timeout=30) for future in [pool.submit(run) for _ in range(5)]]
        succeeded = [r for r in responses if r.status_code == 201]
        rejected = [r for r in responses if r.status_code == 400]
        self.assertEqual(len(succeeded) + len(rejected), 5)
        # Deterministic regardless of interleaving: exactly floor(50/20)
        # sells can ever succeed before the balance can no longer cover
        # another -20, and ON CONFLICT DO UPDATE's own row-level locking
        # serializes each contender's view of the current balance.
        self.assertEqual(len(succeeded), 2)
        self.assertEqual(self._balance(), 10)


class RawLedgerBase(LedgerTestBase):
    """Physical table/column identifiers for tests that write with raw SQL
    that never goes near the app_platform service layer at all."""

    def setUp(self):
        super().setUp()
        # Resolve physical names the same way schema_evolution/records do,
        # via the receipt's own bindings -- not re-derived by hand.
        from app_platform import schema_evolution

        self.schema = sql.Identifier(self.plan["schema_name"])
        self.balance_table = sql.Identifier(
            schema_evolution._table_for(self.receipt, self.binding.balance_model).name
        )
        self.movement_table = sql.Identifier(
            schema_evolution._table_for(self.receipt, self.binding.movement_model).name
        )
        self.balance_column = sql.Identifier(
            schema_evolution._column_for(self.receipt, self.binding.balance_field).name
        )
        self.movement_column = sql.Identifier(
            schema_evolution._column_for(self.receipt, self.binding.movement_field).name
        )
        self.movement_item_column = sql.Identifier(
            schema_evolution._column_for_relationship(self.receipt, self.movement_item_rel).name
        )
        self.movement_warehouse_column = sql.Identifier(
            schema_evolution._column_for_relationship(self.receipt, self.movement_warehouse_rel).name
        )
        self.balance_item_column = sql.Identifier(
            schema_evolution._column_for_relationship(self.receipt, self.inventory_item_rel).name
        )
        self.balance_warehouse_column = sql.Identifier(
            schema_evolution._column_for_relationship(self.receipt, self.inventory_warehouse_rel).name
        )

    def raw(self, statement, params=None):
        """Runs one statement against the tenant DB, formatting {schema}, {bal},
        {mv}, {bal_col}, {mv_col}, {mv_item}, {mv_wh}, {bal_item}, {bal_wh}."""
        composed = sql.SQL(statement).format(
            schema=self.schema,
            bal=self.balance_table,
            mv=self.movement_table,
            bal_col=self.balance_column,
            mv_col=self.movement_column,
            mv_item=self.movement_item_column,
            mv_wh=self.movement_warehouse_column,
            bal_item=self.balance_item_column,
            bal_wh=self.balance_warehouse_column,
        )
        with connections["tenant"].cursor() as cursor:
            cursor.execute(composed, params)


class DirectBypassTests(RawLedgerBase):
    """The invariant is enforced by the tenant database itself, not by
    records.py -- proven here with raw SQL."""

    def test_a_raw_sql_movement_insert_still_atomically_maintains_the_balance(self):
        with connections["tenant"].cursor() as cursor:
            cursor.execute(
                sql.SQL("INSERT INTO {}.{} ({}, {}, {}) VALUES (%s, %s, %s)").format(
                    self.schema,
                    self.movement_table,
                    self.movement_item_column,
                    self.movement_warehouse_column,
                    self.movement_column,
                ),
                [self.item_id, self.warehouse_id, 25],
            )
        self.assertEqual(self._balance(), 25)

    def test_a_raw_sql_update_of_the_guarded_balance_column_is_rejected(self):
        self._movement(100)
        with connections["tenant"].cursor() as cursor:
            with self.assertRaisesRegex(IntegrityError, "cannot be edited directly"):
                cursor.execute(
                    sql.SQL("UPDATE {}.{} SET {} = 999").format(
                        self.schema, self.balance_table, self.balance_column
                    )
                )
        self.assertEqual(self._balance(), 100)

    def test_a_raw_sql_delete_of_a_bound_balance_row_is_rejected(self):
        self._movement(100)
        with connections["tenant"].cursor() as cursor:
            with self.assertRaisesRegex(IntegrityError, "cannot be deleted directly"):
                cursor.execute(sql.SQL("DELETE FROM {}.{}").format(self.schema, self.balance_table))
        self.assertEqual(self._balance(), 100)


class MovementImmutabilityTests(RawLedgerBase):
    """A movement is append-only: editing or removing one would change the
    movement sum without changing the balance -- silent inventory drift."""

    def setUp(self):
        super().setUp()
        response = self._movement(100)
        self.assertEqual(response.status_code, 201, response.data)
        self.movement_id = response.data["id"]

    def _assert_unchanged(self):
        self.assertEqual(self._balance(), 100)
        rows = self._movement_rows()
        self.assertEqual([r[str(self.delta_field.id)] for r in rows], [100])

    def test_api_patch_of_a_movement_quantity_is_rejected(self):
        response = self.client.patch(
            f"/api/v1/app-models/{self.movement_model.id}/records/{self.movement_id}/",
            {str(self.delta_field.id): 5},
            format="json",
        )
        self.assertEqual(response.status_code, 400, response.data)
        self.assertIn("append-only", response.data["detail"])
        self._assert_unchanged()

    def test_api_delete_of_a_movement_is_rejected(self):
        response = self.client.delete(
            f"/api/v1/app-models/{self.movement_model.id}/records/{self.movement_id}/"
        )
        self.assertEqual(response.status_code, 400)
        self._assert_unchanged()

    def test_raw_update_of_a_movement_quantity_is_rejected(self):
        with self.assertRaisesRegex(IntegrityError, "append-only and cannot be edited"):
            self.raw("UPDATE {schema}.{mv} SET {mv_col} = 5")
        self._assert_unchanged()

    def test_raw_update_of_a_movement_dimension_is_rejected(self):
        other = self._create_warehouse("Shop")
        with self.assertRaisesRegex(IntegrityError, "append-only and cannot be edited"):
            self.raw("UPDATE {schema}.{mv} SET {mv_wh} = %s", [other])
        self._assert_unchanged()

    def test_raw_delete_of_a_movement_is_rejected(self):
        with self.assertRaisesRegex(IntegrityError, "append-only and cannot be deleted"):
            self.raw("DELETE FROM {schema}.{mv}")
        self._assert_unchanged()

    def test_truncate_of_either_table_is_rejected(self):
        for table in ("{mv}", "{bal}"):
            with self.assertRaisesRegex(IntegrityError, "cannot be truncated"):
                self.raw("TRUNCATE {schema}." + table)
        self._assert_unchanged()


class BalanceGuardTests(RawLedgerBase):
    def setUp(self):
        super().setUp()
        self._movement(100)

    def test_a_forged_bypass_flag_from_plain_sql_does_not_unlock_the_balance(self):
        with (
            self.assertRaisesRegex(IntegrityError, "cannot be edited directly"),
            transaction.atomic(using="tenant"),
        ):
            self.raw("SELECT set_config('app_platform.ledger_write', 'on', true)")
            self.raw("UPDATE {schema}.{bal} SET {bal_col} = 999")
        self.assertEqual(self._balance(), 100)

    def test_repointing_a_balance_row_to_another_dimension_is_rejected(self):
        other = self._create_item("Gadget")
        with self.assertRaisesRegex(IntegrityError, "cannot be edited directly"):
            self.raw("UPDATE {schema}.{bal} SET {bal_item} = %s", [other])
        self.assertEqual(self._balance(), 100)

    def test_a_raw_balance_insert_with_a_nonzero_start_is_rejected(self):
        other = self._create_item("Gadget")
        with self.assertRaisesRegex(IntegrityError, "must start at zero"):
            self.raw(
                "INSERT INTO {schema}.{bal} ({bal_item}, {bal_wh}, {bal_col}) VALUES (%s, %s, 50)",
                [other, self.warehouse_id],
            )
        self.assertEqual(len(self._inventory_rows()), 1)


class RequiredDimensionTests(RawLedgerBase):
    def test_a_movement_without_a_warehouse_is_rejected_via_the_api(self):
        response = self.client.post(
            f"/api/v1/app-models/{self.movement_model.id}/records/",
            {str(self.delta_field.id): 10, str(self.movement_item_rel.id): self.item_id},
            format="json",
        )
        self.assertEqual(response.status_code, 400, response.data)
        self.assertEqual(self._inventory_rows(), [])
        self.assertEqual(self._movement_rows(), [])

    def test_a_raw_movement_without_an_item_is_rejected_and_creates_no_orphan_balance(self):
        with self.assertRaisesRegex(IntegrityError, "must be set"):
            self.raw("INSERT INTO {schema}.{mv} ({mv_wh}, {mv_col}) VALUES (%s, 10)", [self.warehouse_id])
        self.assertEqual(self._inventory_rows(), [])


class InventoryMatrixTests(LedgerTestBase):
    def test_receive_100_sell_5_leaves_95(self):
        self.assertEqual(self._movement(100).status_code, 201)
        self.assertEqual(self._movement(-5).status_code, 201)
        self.assertEqual(self._balance(), 95)

    def test_selling_exactly_the_remaining_stock_reaches_zero_and_keeps_the_row(self):
        self._movement(5)
        self.assertEqual(self._movement(-5).status_code, 201)
        self.assertEqual(self._balance(), 0)
        self.assertEqual(len(self._inventory_rows()), 1)

    def test_selling_one_more_than_the_stock_is_rejected(self):
        self._movement(5)
        self.assertEqual(self._movement(-6).status_code, 400)
        self.assertEqual(self._balance(), 5)

    def test_stock_in_one_warehouse_does_not_cover_a_sale_from_another(self):
        self._movement(10)
        other = self._create_warehouse("Shop Floor")
        response = self._movement(-3, warehouse_id=other)
        self.assertEqual(response.status_code, 400, response.data)
        self.assertEqual(self._balance(), 10)
        self.assertEqual(len(self._inventory_rows()), 1)

    def test_stock_of_one_product_does_not_cover_a_sale_of_another(self):
        self._movement(10)
        other = self._create_item("Gadget")
        self.assertEqual(self._movement(-1, item_id=other).status_code, 400)
        self.assertEqual(self._balance(), 10)

    def test_a_movement_for_a_nonexistent_product_or_warehouse_is_rejected(self):
        self.assertEqual(self._movement(5, item_id=str(uuid.uuid4())).status_code, 400)
        self.assertEqual(self._movement(5, warehouse_id=str(uuid.uuid4())).status_code, 400)
        self.assertEqual(self._inventory_rows(), [])
        self.assertEqual(self._movement_rows(), [])

    def test_another_organizations_product_id_cannot_be_used(self):
        foreign = _LedgerFixture.build("foreign@example.com", "Foreign Org")
        try:
            self.assertEqual(self._movement(5, item_id=foreign.item_id).status_code, 400)
            self.assertEqual(self._inventory_rows(), [])
        finally:
            foreign.drop_schema()

    def test_an_allow_negative_ledger_permits_backorders(self):
        fixture = _LedgerFixture.build("neg@example.com", "Neg Org", allow_negative=True)
        try:
            fixture.movement(-5)
            self.assertEqual(fixture.balance(), -5)
        finally:
            fixture.drop_schema()


class ReconciliationTests(RawLedgerBase):
    def test_every_stored_balance_equals_the_sum_of_its_movements(self):
        other = self._create_warehouse("Shop Floor")
        for delta, warehouse in [(100, None), (-5, None), (40, other), (-40, other), (7, None)]:
            self.assertEqual(self._movement(delta, warehouse_id=warehouse).status_code, 201)
        self.assertEqual(quantity_ledger.reconcile(self.binding), [])

    def test_reconcile_reports_drift_introduced_behind_the_triggers_back(self):
        self._movement(100)
        # Only a DDL-capable role can do this -- the documented residual limit.
        self.raw("ALTER TABLE {schema}.{bal} DISABLE TRIGGER USER")
        self.raw("UPDATE {schema}.{bal} SET {bal_col} = 90")
        self.raw("ALTER TABLE {schema}.{bal} ENABLE TRIGGER USER")
        drift = quantity_ledger.reconcile(self.binding)
        self.assertEqual(len(drift), 1)
        self.assertEqual((drift[0]["stored"], drift[0]["expected"]), (90, 100))


class BindingContractTests(TransactionTestCase):
    databases = {"default", "tenant"}

    def setUp(self):
        call_command("seed_permissions", verbosity=0)

    def test_a_single_dimension_is_rejected_up_front(self):
        fixture = _LedgerFixture.build("one-dim@example.com", "One Dim Org", bind=False)
        try:
            payload = fixture.binding_payload()
            payload["dimensions"] = payload["dimensions"][:1]
            with self.assertRaises(ValidationError):
                quantity_ledger.bind(fixture.actor, fixture.instance, payload)
        finally:
            fixture.drop_schema()

    def test_binding_over_existing_business_data_is_refused(self):
        fixture = _LedgerFixture.build("nonempty@example.com", "Non Empty Org", bind=False)
        try:
            fixture.movement(10)  # plain movement row, no ledger yet
            with self.assertRaises(ValidationError):
                quantity_ledger.bind(fixture.actor, fixture.instance, fixture.binding_payload())
        finally:
            fixture.drop_schema()

    def test_the_same_fields_cannot_be_bound_twice(self):
        fixture = _LedgerFixture.build("twice@example.com", "Twice Org")
        try:
            with self.assertRaises(ValidationError):
                quantity_ledger.bind(fixture.actor, fixture.instance, fixture.binding_payload())
        finally:
            fixture.drop_schema()

    def test_another_organizations_user_cannot_see_or_create_a_binding(self):
        owner = _LedgerFixture.build("owner-x@example.com", "Owner X Org")
        outsider = User.objects.create_user(email="outsider-x@example.com")
        create_organization(name="Outsider Org", created_by=outsider)
        client = APIClient()
        client.force_authenticate(outsider)
        try:
            url = f"/api/v1/app-instances/{owner.instance.id}/quantity-ledgers/"
            self.assertEqual(client.get(url).status_code, 404)
            self.assertEqual(client.post(url, owner.binding_payload(), format="json").status_code, 404)
        finally:
            owner.drop_schema()


class BindingEndpointTests(TransactionTestCase):
    """The bind() service function itself is exercised directly by every
    other test class above (LedgerTestBase.setUp) -- this proves the real
    HTTP view/serializer/url wiring around it (views.QuantityLedgerList,
    serializers.QuantityLedgerBindingSerializer) also works end to end,
    not just the service layer."""

    databases = {"default", "tenant"}

    def test_binding_over_http_then_receiving_over_http(self):
        call_command("seed_permissions", verbosity=0)
        fixture = _LedgerFixture.build("endpoint@example.com", "Endpoint Org", bind=False)
        try:
            response = fixture.client.post(
                f"/api/v1/app-instances/{fixture.instance.id}/quantity-ledgers/",
                fixture.binding_payload(),
                format="json",
            )
            self.assertEqual(response.status_code, 201, response.data)
            self.assertEqual(len(response.data["dimensions"]), 2)

            listing = fixture.client.get(f"/api/v1/app-instances/{fixture.instance.id}/quantity-ledgers/")
            self.assertEqual(listing.status_code, 200, listing.data)
            self.assertEqual(listing.data["count"], 1)

            fixture.movement(100)
            self.assertEqual(fixture.balance(), 100)
        finally:
            fixture.drop_schema()


class CrossOrganizationIsolationTests(TransactionTestCase):
    databases = {"default", "tenant"}

    def test_receiving_in_one_organizations_ledger_never_touches_another(self):
        call_command("seed_permissions", verbosity=0)
        first = _LedgerFixture.build("iso-a@example.com", "Iso Org A")
        second = _LedgerFixture.build("iso-b@example.com", "Iso Org B")
        try:
            first.movement(100)
            self.assertEqual(first.balance(), 100)
            self.assertIsNone(second.balance())
        finally:
            first.drop_schema()
            second.drop_schema()


class _LedgerFixture:
    """Builds one full ledger-bound runtime for CrossOrganizationIsolationTests
    -- pulled out of LedgerTestBase.setUp so two independent instances (two
    different organizations) can exist side by side in a single test."""

    @classmethod
    def build(cls, email, org_name, *, bind=True, allow_negative=False):
        self = cls()
        self.actor = User.objects.create_user(email=email)
        self.org = create_organization(name=org_name, created_by=self.actor)
        self.project = project_for(self.actor, self.org)
        template = templates.create_template(
            self.actor, self.org, {"label": "Ledger App", "draft": _ledger_sample()}
        )
        version = templates.publish_template(self.actor, template)
        self.instance = instances.install(
            self.actor, self.project, {"label": "Runtime", "template_version": str(version.id)}
        )
        self.item_model = self.instance.models.get(key="item")
        self.warehouse_model = self.instance.models.get(key="warehouse")
        self.inventory_model = self.instance.models.get(key="inventory")
        self.movement_model = self.instance.models.get(key="stock_movement")
        self.quantity_field = self.inventory_model.fields.get(key="quantity")
        self.delta_field = self.movement_model.fields.get(key="delta")
        self.plan = plan_runtime(self.actor, self.instance)
        provisioning.reserve(self.actor, self.instance, self.plan["fingerprint"])
        self.receipt = provisioning.execute(self.instance.id, self.actor)
        self.client = APIClient()
        self.client.force_authenticate(self.actor)

        def _create(model, field_key, value):
            field = model.fields.get(key=field_key)
            response = self.client.post(
                f"/api/v1/app-models/{model.id}/records/", {str(field.id): value}, format="json"
            )
            assert response.status_code == 201, response.data
            return response.data["id"]

        self.item_id = _create(self.item_model, "name", "Widget")
        self.warehouse_id = _create(self.warehouse_model, "name", "Main")
        if bind:
            quantity_ledger.bind(
                self.actor, self.instance, {**self.binding_payload(), "allow_negative": allow_negative}
            )
        return self

    def binding_payload(self):
        return {
            "balance_model_id": str(self.inventory_model.id),
            "balance_field_id": str(self.quantity_field.id),
            "movement_model_id": str(self.movement_model.id),
            "movement_field_id": str(self.delta_field.id),
            "dimensions": [
                {
                    "balance_relationship_id": str(self.instance.relationships.get(key="inventory_item").id),
                    "movement_relationship_id": str(self.instance.relationships.get(key="movement_item").id),
                },
                {
                    "balance_relationship_id": str(
                        self.instance.relationships.get(key="inventory_warehouse").id
                    ),
                    "movement_relationship_id": str(
                        self.instance.relationships.get(key="movement_warehouse").id
                    ),
                },
            ],
        }

    def movement(self, delta):
        response = self.client.post(
            f"/api/v1/app-models/{self.movement_model.id}/records/",
            {
                str(self.delta_field.id): delta,
                str(self.instance.relationships.get(key="movement_item").id): self.item_id,
                str(self.instance.relationships.get(key="movement_warehouse").id): self.warehouse_id,
            },
            format="json",
        )
        assert response.status_code == 201, response.data
        return response

    def balance(self):
        response = self.client.get(f"/api/v1/app-models/{self.inventory_model.id}/records/")
        assert response.status_code == 200, response.data
        rows = response.data["results"]
        return rows[0][str(self.quantity_field.id)] if rows else None

    def drop_schema(self):
        with connections["tenant"].cursor() as cursor:
            cursor.execute(
                sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE").format(sql.Identifier(self.plan["schema_name"]))
            )
