"""Post-Phase-3 Integration Enablement, Part 2/3: generic App Platform
field indexing and single-field uniqueness. The underlying PostgreSQL
primitives (databases.services.add_column's new is_indexed parameter,
add_unique_constraint/add_index) are unit-tested directly against a real
connection in databases/tests/test_indexing.py; this file proves the
App Platform-level wiring end to end -- template/live-add-time
unique/indexed fields, the retrofit action against an already-
provisioned, possibly populated instance, record-level enforcement, and
the record-API filter/EXPLAIN evidence an external client's exact-match
lookup is actually index-backed."""

from concurrent.futures import ThreadPoolExecutor

from django.core.management import call_command
from django.db import close_old_connections, connections, transaction
from django.test import TransactionTestCase
from psycopg import sql
from rest_framework.test import APIClient

from accounts.models import User
from app_platform import instances, provisioning, templates
from app_platform.models import FieldDefinition
from app_platform.runtime_plan import plan_runtime
from app_platform.tests.test_foundation import project_for, sample
from databases.models import DBColumn, DBIndex
from organizations.models import Membership
from organizations.services import create_organization
from permissions.services import assign_role, grant_resource_permission


class FieldIndexingTestBase(TransactionTestCase):
    databases = {"default", "tenant"}

    def setUp(self):
        call_command("seed_permissions", verbosity=0)
        self.actor = User.objects.create_user(email="index-owner@example.com")
        self.org = create_organization(name="Index Org", created_by=self.actor)
        self.project = project_for(self.actor, self.org)
        self.client = APIClient()
        self.client.force_authenticate(self.actor)

    def _install(self):
        template = templates.create_template(self.actor, self.org, {"label": "App", "draft": sample()})
        version = templates.publish_template(self.actor, template)
        return instances.install(
            self.actor, self.project, {"label": "Runtime", "template_version": str(version.id)}
        )

    def _provision(self, instance):
        plan = plan_runtime(self.actor, instance)
        provisioning.reserve(self.actor, instance, plan["fingerprint"])
        receipt = provisioning.execute(instance.id, self.actor)
        return plan, receipt

    def _drop_schema(self, plan):
        with connections["tenant"].cursor() as cursor:
            cursor.execute(
                sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE").format(sql.Identifier(plan["schema_name"]))
            )


class NewFieldUniqueIndexedTests(FieldIndexingTestBase):
    def setUp(self):
        super().setUp()
        self.instance = self._install()
        self.item = self.instance.models.get(key="item")

    def test_installing_a_template_with_a_unique_field_provisions_a_real_unique_column(self):
        template = templates.create_template(
            self.actor, self.org, {"label": "Parts App", "draft": self._unique_field_definition()}
        )
        version = templates.publish_template(self.actor, template)
        instance = instances.install(
            self.actor, self.project, {"label": "Parts", "template_version": str(version.id)}
        )
        plan, receipt = self._provision(instance)
        try:
            part = instance.models.get(key="part")
            number_field = part.fields.get(key="number")
            self.assertTrue(number_field.unique)

            create = self.client.post(
                f"/api/v1/app-models/{part.id}/records/", {str(number_field.id): "AAA111"}, format="json"
            )
            self.assertEqual(create.status_code, 201, create.data)

            dupe = self.client.post(
                f"/api/v1/app-models/{part.id}/records/", {str(number_field.id): "AAA111"}, format="json"
            )
            self.assertEqual(dupe.status_code, 400, dupe.data)
            self.assertIn("already exists", dupe.data["detail"])
        finally:
            self._drop_schema(plan)

    def _unique_field_definition(self):
        d = sample()
        for model in d["models"]:
            if model["key"] == "item":
                model["key"] = "part"
                model["label"] = "Part"
                for field in model["fields"]:
                    if field["key"] == "name":
                        field["key"] = "number"
                        field["label"] = "Number"
                        field["unique"] = True
        return d

    def test_adding_a_new_field_live_with_unique_true_on_an_unpopulated_model(self):
        plan, receipt = self._provision(self.instance)
        try:
            resp = self.client.post(
                f"/api/v1/app-models/{self.item.id}/fields/",
                {"key": "sku", "label": "SKU", "data_type": "text", "unique": True},
                format="json",
            )
            self.assertEqual(resp.status_code, 201, resp.data)
            self.assertTrue(resp.data["unique"])
            field = FieldDefinition.objects.get(pk=resp.data["id"])
            self.assertTrue(field.unique)
        finally:
            self._drop_schema(plan)

    def test_adding_a_new_indexed_field_live_creates_a_real_index(self):
        plan, receipt = self._provision(self.instance)
        try:
            resp = self.client.post(
                f"/api/v1/app-models/{self.item.id}/fields/",
                {"key": "make", "label": "Make", "data_type": "text", "indexed": True},
                format="json",
            )
            self.assertEqual(resp.status_code, 201, resp.data)
            field = FieldDefinition.objects.get(pk=resp.data["id"])
            self.assertTrue(field.indexed)
            column_id = receipt_bindings_field(receipt, field)
            self.assertTrue(DBIndex.objects.filter(columns__id=column_id, is_unique=False).exists())
        finally:
            self._drop_schema(plan)


class RetrofitUniqueFieldTests(FieldIndexingTestBase):
    def setUp(self):
        super().setUp()
        self.instance = self._install()
        self.item = self.instance.models.get(key="item")
        self.plan, self.receipt = self._provision(self.instance)
        self.number_field = self.client.post(
            f"/api/v1/app-models/{self.item.id}/fields/",
            {"key": "part_number", "label": "Part Number", "data_type": "text"},
            format="json",
        ).data

    def tearDown(self):
        self._drop_schema(self.plan)
        super().tearDown()

    # UNIQUE CONSTRAINT TESTS 1-10 from the task:

    def test_1_unique_field_provisions_correctly_via_new_field_creation(self):
        resp = self.client.post(
            f"/api/v1/app-models/{self.item.id}/fields/",
            {"key": "code", "label": "Code", "data_type": "text", "unique": True},
            format="json",
        )
        self.assertEqual(resp.status_code, 201, resp.data)
        self.assertTrue(resp.data["unique"])

    def test_2_duplicate_create_rejected(self):
        self._retrofit_unique()
        self.client.post(
            f"/api/v1/app-models/{self.item.id}/records/",
            {str(self.number_field["id"]): "SAME"},
            format="json",
        )
        dupe = self.client.post(
            f"/api/v1/app-models/{self.item.id}/records/",
            {str(self.number_field["id"]): "SAME"},
            format="json",
        )
        self.assertEqual(dupe.status_code, 400, dupe.data)
        self.assertIn("already exists", dupe.data["detail"])

    def test_3_duplicate_update_rejected(self):
        self._retrofit_unique()
        first = self.client.post(
            f"/api/v1/app-models/{self.item.id}/records/",
            {str(self.number_field["id"]): "ONE"},
            format="json",
        )
        second = self.client.post(
            f"/api/v1/app-models/{self.item.id}/records/",
            {str(self.number_field["id"]): "TWO"},
            format="json",
        )
        clash = self.client.patch(
            f"/api/v1/app-models/{self.item.id}/records/{second.data['id']}/",
            {str(self.number_field["id"]): "ONE"},
            format="json",
        )
        self.assertEqual(clash.status_code, 400, clash.data)
        self.assertIn("already exists", clash.data["detail"])
        del first  # only used to occupy the value "ONE"

    def test_4_different_values_accepted(self):
        self._retrofit_unique()
        a = self.client.post(
            f"/api/v1/app-models/{self.item.id}/records/",
            {str(self.number_field["id"]): "ALPHA"},
            format="json",
        )
        b = self.client.post(
            f"/api/v1/app-models/{self.item.id}/records/",
            {str(self.number_field["id"]): "BETA"},
            format="json",
        )
        self.assertEqual(a.status_code, 201, a.data)
        self.assertEqual(b.status_code, 201, b.data)

    def test_5_existing_populated_model_can_safely_add_uniqueness_when_data_is_clean(self):
        self.client.post(
            f"/api/v1/app-models/{self.item.id}/records/",
            {str(self.number_field["id"]): "CLEAN-1"},
            format="json",
        )
        self.client.post(
            f"/api/v1/app-models/{self.item.id}/records/",
            {str(self.number_field["id"]): "CLEAN-2"},
            format="json",
        )
        resp = self._retrofit_unique()
        self.assertEqual(resp.status_code, 200, resp.data)
        self.assertTrue(resp.data["unique"])

    def test_6_adding_uniqueness_fails_safely_when_duplicates_exist(self):
        self.client.post(
            f"/api/v1/app-models/{self.item.id}/records/",
            {str(self.number_field["id"]): "DUPE"},
            format="json",
        )
        self.client.post(
            f"/api/v1/app-models/{self.item.id}/records/",
            {str(self.number_field["id"]): "DUPE"},
            format="json",
        )
        resp = self._retrofit_unique()
        self.assertEqual(resp.status_code, 400, resp.data)

    def test_7_failed_uniqueness_migration_preserves_existing_data(self):
        self.client.post(
            f"/api/v1/app-models/{self.item.id}/records/",
            {str(self.number_field["id"]): "DUPE"},
            format="json",
        )
        self.client.post(
            f"/api/v1/app-models/{self.item.id}/records/",
            {str(self.number_field["id"]): "DUPE"},
            format="json",
        )
        self._retrofit_unique()
        listing = self.client.get(f"/api/v1/app-models/{self.item.id}/records/")
        self.assertEqual(listing.data["count"], 2)
        field = FieldDefinition.objects.get(pk=self.number_field["id"])
        self.assertFalse(field.unique)

    def test_8_re_running_the_retrofit_is_idempotent(self):
        self.client.post(
            f"/api/v1/app-models/{self.item.id}/records/",
            {str(self.number_field["id"]): "ONLY"},
            format="json",
        )
        first = self._retrofit_unique()
        second = self._retrofit_unique()
        self.assertEqual(first.status_code, 200, first.data)
        self.assertEqual(second.status_code, 200, second.data)
        field_id = self.number_field["id"]
        self.assertEqual(
            DBIndex.objects.filter(
                columns__id=receipt_bindings_field(self.receipt, FieldDefinition.objects.get(pk=field_id))
            ).count(),
            1,
        )

    def test_9_changing_label_or_position_does_not_recreate_uniqueness(self):
        self._retrofit_unique()
        field = FieldDefinition.objects.get(pk=self.number_field["id"])
        column_id_before = receipt_bindings_field(self.receipt, field)

        rename = self.client.patch(
            f"/api/v1/app-fields/{field.id}/", {"label": "Renamed"}, format="json"
        )
        self.assertEqual(rename.status_code, 200, rename.data)
        self.receipt.refresh_from_db()
        column_id_after = receipt_bindings_field(self.receipt, field)
        self.assertEqual(column_id_before, column_id_after)
        field.refresh_from_db()
        self.assertTrue(field.unique)

    def test_10_tenant_isolation_remains_intact_for_the_retrofit_action(self):
        outsider = User.objects.create_user(email="index-outsider@example.com")
        outsider_org = create_organization(name="Outsider Org", created_by=outsider)
        Membership.objects.create(user=outsider, organization=self.org, status=Membership.Status.ACTIVE)
        del outsider_org
        client = APIClient()
        client.force_authenticate(outsider)
        # Active member of the SAME org, but no role/grant covering
        # database.schema.manage -- deny-by-default, not "any member of
        # the org can mutate schema."
        resp = client.post(f"/api/v1/app-fields/{self.number_field['id']}/unique/")
        self.assertEqual(resp.status_code, 403)
        field = FieldDefinition.objects.get(pk=self.number_field["id"])
        self.assertFalse(field.unique)

        # Two separate resources, matching Phase 3 step 3's own established
        # split: app_instance.schema.manage (resource-scoped is enough,
        # this is a metadata/definition action) plus database.schema.manage
        # (org-wide only -- add_unique_constraint's own require, since it's
        # real tenant DDL).
        grant_resource_permission(
            user=outsider,
            permission_code="app_instance.schema.manage",
            organization_id=self.org.id,
            resource_type="app_instance",
            resource_id=self.instance.id,
        )
        assign_role(user=outsider, role_slug="database-administrator", organization=self.org)
        allowed = client.post(f"/api/v1/app-fields/{self.number_field['id']}/unique/")
        self.assertEqual(allowed.status_code, 200, allowed.data)

    def test_direct_unsanctioned_orm_write_to_unique_is_still_blocked_once_provisioned(self):
        """Security review: the two new migration-0009 trigger exemptions
        are narrowly gated on the schema_evolution session flag
        (SET LOCAL, set only by mark_addition_transaction()) -- a write
        that reaches app_platform_fielddefinition / databases_dbcolumn by
        ANY other path, with the flag unset, must still be rejected by
        the database itself, not merely by this module's own Python-level
        checks. Bypasses instances.py/schema_evolution.py entirely on
        purpose to prove the DB-level backstop actually backstops."""
        with self.assertRaises(Exception) as ctx:
            FieldDefinition.objects.filter(pk=self.number_field["id"]).update(unique=True)
        self.assertIn("Reserved runtime definitions require a schema migration", str(ctx.exception))
        field = FieldDefinition.objects.get(pk=self.number_field["id"])
        self.assertFalse(field.unique)

        column_id = receipt_bindings_field(self.receipt, field)
        with self.assertRaises(Exception) as ctx:
            DBColumn.objects.filter(pk=column_id).update(is_unique=True)
        self.assertIn("Managed runtime catalog requires a schema migration", str(ctx.exception))

    def test_concurrent_duplicate_record_creates_the_database_constraint_is_the_real_gate(self):
        """Security review requirement: uniqueness must be enforced by the
        real Postgres constraint, never an application-level pre-check
        alone (a pre-check has an inherent TOCTOU race between two
        concurrent requests). Nothing in records.create_record does a
        SELECT-then-INSERT uniqueness check -- it relies entirely on the
        real UNIQUE constraint and translates the resulting
        UniqueViolation cleanly (records.py's _run). Proven with real
        threads and separate connections, not just reasoned about."""
        self._retrofit_unique()
        field_id = self.number_field["id"]

        def create(value):
            close_old_connections()
            client = APIClient()
            client.force_authenticate(self.actor)
            try:
                return client.post(
                    f"/api/v1/app-models/{self.item.id}/records/", {field_id: value}, format="json"
                )
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as pool:
            responses = list(pool.map(create, ["RACE", "RACE"]))

        statuses = sorted(r.status_code for r in responses)
        self.assertEqual(statuses, [201, 400])
        listing = self.client.get(f"/api/v1/app-models/{self.item.id}/records/?{field_id}=RACE")
        self.assertEqual(listing.data["count"], 1)

    def _retrofit_unique(self):
        return self.client.post(f"/api/v1/app-fields/{self.number_field['id']}/unique/")


class IndexBackedSearchEvidenceTests(FieldIndexingTestBase):
    """Part 4/8: the exact-match record filter is index-backed once a
    field is unique/indexed -- no new query-layer code, proven with a
    real EXPLAIN against the actual query records.list_records issues."""

    def setUp(self):
        super().setUp()
        self.instance = self._install()
        self.item = self.instance.models.get(key="item")
        self.plan, self.receipt = self._provision(self.instance)

    def tearDown(self):
        self._drop_schema(self.plan)
        super().tearDown()

    def test_exact_match_filter_on_a_unique_field_uses_a_real_index_scan(self):
        field_resp = self.client.post(
            f"/api/v1/app-models/{self.item.id}/fields/",
            {"key": "normalized_number", "label": "Normalized Number", "data_type": "text", "unique": True},
            format="json",
        )
        field_id = field_resp.data["id"]
        self.client.post(
            f"/api/v1/app-models/{self.item.id}/records/",
            {field_id: "044650K290"},
            format="json",
        )
        field = FieldDefinition.objects.get(pk=field_id)
        column_id = receipt_bindings_field(self.receipt, field)
        column = DBColumn.objects.get(pk=column_id)
        table = column.table

        # A 1-row table is correctly judged cheaper as a sequential scan
        # by Postgres's own cost-based planner regardless of any index --
        # that's the planner doing its job, not evidence the index is
        # unusable. `enable_seqscan = off` (this transaction only) is the
        # standard technique to prove the index is structurally usable
        # for this exact predicate without needing a large dataset here;
        # a real "the planner naturally prefers it at scale" check runs
        # separately against a disposable, moderately large synthetic
        # dataset -- see TEST_STATUS.md for that evidence, never claimed
        # by this small, permanent unit test.
        with transaction.atomic(using="tenant"), connections["tenant"].cursor() as cursor:
            cursor.execute("SET LOCAL enable_seqscan = off")
            cursor.execute(
                sql.SQL("EXPLAIN SELECT * FROM {}.{} WHERE {} = %s").format(
                    sql.Identifier(table.tenant_database.schema_name),
                    sql.Identifier(table.name),
                    sql.Identifier(column.name),
                ),
                ["044650K290"],
            )
            plan_lines = "\n".join(row[0] for row in cursor.fetchall())
        self.assertIn("Index", plan_lines, plan_lines)

        api_lookup = self.client.get(
            f"/api/v1/app-models/{self.item.id}/records/?{field_id}=044650K290"
        )
        self.assertEqual(api_lookup.status_code, 200, api_lookup.data)
        self.assertEqual(api_lookup.data["count"], 1)
        self.assertEqual(api_lookup.data["results"][0][field_id], "044650K290")


def receipt_bindings_field(receipt, field):
    receipt.refresh_from_db()
    return receipt.bindings["fields"][str(field.id)]
