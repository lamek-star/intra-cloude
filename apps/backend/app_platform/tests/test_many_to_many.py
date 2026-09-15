"""Native many-to-many relationships for App Platform. Built up
incrementally alongside the feature -- this first slice covers only the
data-model change (RelationshipDefinition.kind now allows "many_to_many",
deletion_policy normalization); provisioning/record-level tests land in
later commits as the corresponding code ships (see
C:\\Users\\Hp\\.claude\\plans\\precious-inventing-seal.md for the full
sequencing)."""

from concurrent.futures import ThreadPoolExecutor

from django.core.management import call_command
from django.db import IntegrityError, close_old_connections, connections, transaction
from django.test import TestCase, TransactionTestCase
from psycopg import sql
from rest_framework.test import APIClient

from accounts.models import User
from app_platform import instances, provisioning, templates
from app_platform.models import RelationshipDefinition
from app_platform.runtime_plan import plan_runtime
from app_platform.tests.test_foundation import project_for, sample
from databases.models import DBTable
from organizations.services import create_organization


class RelationshipKindTests(TestCase):
    """Pre-provision only -- no tenant DB involved yet, matching
    instances.add_relationship's existing behavior for an unprovisioned
    instance (a pure metadata write)."""

    @classmethod
    def setUpTestData(cls):
        call_command("seed_permissions", verbosity=0)
        cls.owner = User.objects.create_user(email="m2m-owner@example.com")
        cls.org = create_organization(name="M2M Org", created_by=cls.owner)
        cls.project = project_for(cls.owner, cls.org)
        template = templates.create_template(cls.owner, cls.org, {"label": "App", "draft": sample()})
        version = templates.publish_template(cls.owner, template)
        cls.instance = instances.install(
            cls.owner, cls.project, {"label": "Runtime", "template_version": str(version.id)}
        )
        cls.item = cls.instance.models.get(key="item")
        cls.group = cls.instance.models.get(key="group")

    def test_many_to_many_kind_is_accepted_and_persisted(self):
        relation = instances.add_relationship(
            self.owner,
            self.instance,
            {
                "key": "compatible_groups",
                "label": "Compatible Groups",
                "source_model": str(self.item.id),
                "target_model": str(self.group.id),
                "kind": "many_to_many",
            },
        )
        self.assertEqual(relation.kind, "many_to_many")
        relation.refresh_from_db()
        self.assertEqual(relation.kind, "many_to_many")

    def test_deletion_policy_is_normalized_to_restrict_for_many_to_many(self):
        relation = instances.add_relationship(
            self.owner,
            self.instance,
            {
                "key": "compatible_groups_2",
                "label": "Compatible Groups 2",
                "source_model": str(self.item.id),
                "target_model": str(self.group.id),
                "kind": "many_to_many",
                "deletion_policy": "set_null",
            },
        )
        self.assertEqual(relation.deletion_policy, "restrict")

    def test_many_to_one_kind_still_works_unchanged(self):
        relation = instances.add_relationship(
            self.owner,
            self.instance,
            {
                "key": "backup_group",
                "label": "Backup Group",
                "source_model": str(self.item.id),
                "target_model": str(self.group.id),
            },
        )
        self.assertEqual(relation.kind, "many_to_one")

    def test_database_constraint_still_rejects_an_invalid_kind_value(self):
        """The CheckConstraint genuinely narrows to exactly these two
        values, not left wide open -- a raw write bypassing the
        serializer entirely must still be rejected at the DB layer,
        matching this project's own "database constraint is the real
        gate" discipline."""
        relation = RelationshipDefinition(
            instance=self.instance,
            key="invalid_kind_probe",
            label="Invalid",
            source_model=self.item,
            target_model=self.group,
            kind="one_to_one",
            position=999,
        )
        # A nested atomic block gives Postgres a savepoint to roll back to
        # on failure -- without it, the failed INSERT poisons the whole
        # test-wrapping transaction and every later query in this test
        # (and, since setUpTestData's transaction wraps the class, every
        # later test in this class) raises "current transaction is
        # aborted" instead.
        with self.assertRaises(Exception) as ctx:
            with transaction.atomic():
                relation.save()
        self.assertIn("app_relation_kind_valid", str(ctx.exception))


class ProvisioningTests(TransactionTestCase):
    """Both provisioning paths -- a fresh runtime built with an M:M
    relationship already in place, and a live addition to an
    already-provisioned instance -- produce a real join table with real
    composite-unique + FK constraints + a target-side index. Record-level
    read/write through records.py lands in a later commit; these tests
    only prove the physical schema is correct."""

    databases = {"default", "tenant"}

    def setUp(self):
        call_command("seed_permissions", verbosity=0)
        self.actor = User.objects.create_user(email="m2m-provision@example.com")
        self.org = create_organization(name="M2M Provision Org", created_by=self.actor)
        self.project = project_for(self.actor, self.org)
        template = templates.create_template(self.actor, self.org, {"label": "App", "draft": sample()})
        version = templates.publish_template(self.actor, template)
        self.instance = instances.install(
            self.actor, self.project, {"label": "Runtime", "template_version": str(version.id)}
        )
        self.item = self.instance.models.get(key="item")
        self.group = self.instance.models.get(key="group")
        self.schema_name = None

    def tearDown(self):
        if self.schema_name:
            with connections["tenant"].cursor() as cursor:
                cursor.execute(
                    sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE").format(sql.Identifier(self.schema_name))
                )
        super().tearDown()

    def _provision(self):
        plan = plan_runtime(self.actor, self.instance)
        self.schema_name = plan["schema_name"]
        provisioning.reserve(self.actor, self.instance, plan["fingerprint"])
        return provisioning.execute(self.instance.id, self.actor)

    def _join_table_indexes(self, receipt, join_table):
        with connections["tenant"].cursor() as cursor:
            cursor.execute(
                "SELECT indexname, indexdef FROM pg_indexes WHERE schemaname = %s AND tablename = %s",
                [receipt.database.schema_name, join_table.name],
            )
            return {row[0]: row[1] for row in cursor.fetchall()}

    def _join_table_fk_delete_rules(self, receipt, join_table):
        with connections["tenant"].cursor() as cursor:
            cursor.execute(
                "SELECT confdeltype FROM pg_constraint "
                "WHERE conrelid = to_regclass(%s) AND contype = 'f' ORDER BY conname",
                [f"{receipt.database.schema_name}.{join_table.name}"],
            )
            return [row[0] for row in cursor.fetchall()]

    def _assert_join_table_is_well_formed(self, receipt, binding):
        self.assertEqual(binding["kind"], "many_to_many")
        join_table = DBTable.objects.get(pk=binding["join_table"])

        indexes = self._join_table_indexes(receipt, join_table)
        # Exclude the table's own primary key index (also reported as
        # "UNIQUE" by pg_indexes) -- only the composite constraint on
        # (source_id, target_id) is under test here.
        unique_defs = [v for k, v in indexes.items() if "UNIQUE" in v and "pkey" not in k]
        self.assertEqual(len(unique_defs), 1)
        self.assertIn("source_id", unique_defs[0])
        self.assertIn("target_id", unique_defs[0])
        non_unique_defs = [v for v in indexes.values() if "UNIQUE" not in v and "pkey" not in v]
        self.assertTrue(any("target_id" in v for v in non_unique_defs))

        # 'c' = ON DELETE CASCADE, for both the source_id and target_id FKs.
        self.assertEqual(self._join_table_fk_delete_rules(receipt, join_table), ["c", "c"])
        return join_table

    def test_initial_provisioning_creates_a_real_join_table_with_constraints(self):
        relation = instances.add_relationship(
            self.actor,
            self.instance,
            {
                "key": "compatible_groups",
                "label": "Compatible Groups",
                "source_model": str(self.item.id),
                "target_model": str(self.group.id),
                "kind": "many_to_many",
            },
        )
        receipt = self._provision()
        binding = receipt.bindings["relationships"][str(relation.id)]
        self._assert_join_table_is_well_formed(receipt, binding)

    def test_live_addition_to_a_populated_instance_creates_a_working_join_table(self):
        receipt = self._provision()
        item_table = DBTable.objects.get(pk=receipt.bindings["models"][str(self.item.id)])
        group_table = DBTable.objects.get(pk=receipt.bindings["models"][str(self.group.id)])
        with connections["tenant"].cursor() as cursor:
            cursor.execute(
                sql.SQL("INSERT INTO {}.{} DEFAULT VALUES RETURNING id").format(
                    sql.Identifier(receipt.database.schema_name), sql.Identifier(item_table.name)
                )
            )
            item_id = cursor.fetchone()[0]
            cursor.execute(
                sql.SQL("INSERT INTO {}.{} DEFAULT VALUES RETURNING id").format(
                    sql.Identifier(receipt.database.schema_name), sql.Identifier(group_table.name)
                )
            )
            group_id = cursor.fetchone()[0]

        relation = instances.add_relationship(
            self.actor,
            self.instance,
            {
                "key": "compatible_groups",
                "label": "Compatible Groups",
                "source_model": str(self.item.id),
                "target_model": str(self.group.id),
                "kind": "many_to_many",
            },
        )
        receipt.refresh_from_db()
        binding = receipt.bindings["relationships"][str(relation.id)]
        join_table = self._assert_join_table_is_well_formed(receipt, binding)

        with connections["tenant"].cursor() as cursor:
            cursor.execute(
                sql.SQL("INSERT INTO {}.{} (source_id, target_id) VALUES (%s, %s)").format(
                    sql.Identifier(receipt.database.schema_name), sql.Identifier(join_table.name)
                ),
                [item_id, group_id],
            )
            cursor.execute(
                sql.SQL("SELECT COUNT(*) FROM {}.{}").format(
                    sql.Identifier(receipt.database.schema_name), sql.Identifier(join_table.name)
                )
            )
            self.assertEqual(cursor.fetchone()[0], 1)


class RecordAPITests(TransactionTestCase):
    """Step 4: records.py's read/write handling for many_to_many, driven
    through the real record API exactly like every other App Platform
    record test -- covering plan section 7's scenarios 3-6, 8-9 (1-2 are
    covered by ProvisioningTests above; 7, cross-org isolation, is a
    generic model-resolution behavior unchanged by this feature, not
    re-tested here)."""

    databases = {"default", "tenant"}

    def setUp(self):
        call_command("seed_permissions", verbosity=0)
        self.actor = User.objects.create_user(email="m2m-records@example.com")
        self.org = create_organization(name="M2M Records Org", created_by=self.actor)
        self.project = project_for(self.actor, self.org)
        template = templates.create_template(self.actor, self.org, {"label": "App", "draft": sample()})
        version = templates.publish_template(self.actor, template)
        self.instance = instances.install(
            self.actor, self.project, {"label": "Runtime", "template_version": str(version.id)}
        )
        self.item = self.instance.models.get(key="item")
        self.group = self.instance.models.get(key="group")
        self.relation = instances.add_relationship(
            self.actor,
            self.instance,
            {
                "key": "compatible_groups",
                "label": "Compatible Groups",
                "source_model": str(self.item.id),
                "target_model": str(self.group.id),
                "kind": "many_to_many",
            },
        )
        plan = plan_runtime(self.actor, self.instance)
        self.schema_name = plan["schema_name"]
        provisioning.reserve(self.actor, self.instance, plan["fingerprint"])
        self.receipt = provisioning.execute(self.instance.id, self.actor)

        self.client = APIClient()
        self.client.force_authenticate(self.actor)
        self.items_url = f"/api/v1/app-models/{self.item.id}/records/"
        self.groups_url = f"/api/v1/app-models/{self.group.id}/records/"
        self.relation_id = str(self.relation.id)

        self.group_a = self._create_group()
        self.group_b = self._create_group()

    def tearDown(self):
        with connections["tenant"].cursor() as cursor:
            cursor.execute(
                sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE").format(sql.Identifier(self.schema_name))
            )
        super().tearDown()

    def _create_group(self):
        response = self.client.post(self.groups_url, {}, format="json")
        assert response.status_code == 201, response.data
        return response.data["id"]

    def _create_item(self, group_ids):
        response = self.client.post(self.items_url, {self.relation_id: group_ids}, format="json")
        assert response.status_code == 201, response.data
        return response.data

    def _join_table(self):
        binding = self.receipt.bindings["relationships"][self.relation_id]
        return DBTable.objects.select_related("tenant_database").get(pk=binding["join_table"])

    def test_create_and_read_from_both_directions(self):
        item = self._create_item([self.group_a, self.group_b])
        self.assertEqual(sorted(item[self.relation_id]), sorted([self.group_a, self.group_b]))

        detail = self.client.get(f"{self.items_url}{item['id']}/")
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(sorted(detail.data[self.relation_id]), sorted([self.group_a, self.group_b]))

        listing = self.client.get(self.items_url)
        self.assertEqual(listing.status_code, 200)
        [listed] = listing.data["results"]
        self.assertEqual(sorted(listed[self.relation_id]), sorted([self.group_a, self.group_b]))

        # Read from the target side too -- read-only, but must reflect the
        # same association written from the source.
        group_detail = self.client.get(f"{self.groups_url}{self.group_a}/")
        self.assertEqual(group_detail.status_code, 200)
        self.assertEqual(group_detail.data[self.relation_id], [item["id"]])

    def test_write_is_blocked_from_the_target_side(self):
        item = self._create_item([])
        response = self.client.patch(
            f"{self.groups_url}{self.group_a}/", {self.relation_id: [item["id"]]}, format="json"
        )
        self.assertEqual(response.status_code, 400)

    def test_update_diffs_associations_rather_than_replacing_blindly(self):
        item = self._create_item([self.group_a])
        response = self.client.patch(
            f"{self.items_url}{item['id']}/", {self.relation_id: [self.group_b]}, format="json"
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data[self.relation_id], [self.group_b])

        response = self.client.patch(f"{self.items_url}{item['id']}/", {self.relation_id: []}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data[self.relation_id], [])

    def test_update_with_the_relationship_key_omitted_leaves_associations_unchanged(self):
        item = self._create_item([self.group_a])
        response = self.client.patch(f"{self.items_url}{item['id']}/", {}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data[self.relation_id], [self.group_a])

    def test_deleting_a_record_cascades_the_association_away(self):
        item = self._create_item([self.group_a])
        delete = self.client.delete(f"{self.items_url}{item['id']}/")
        self.assertEqual(delete.status_code, 204)

        group_detail = self.client.get(f"{self.groups_url}{self.group_a}/")
        self.assertEqual(group_detail.data[self.relation_id], [])
        with connections["tenant"].cursor() as cursor:
            join_table = self._join_table()
            cursor.execute(
                sql.SQL("SELECT COUNT(*) FROM {}.{}").format(
                    sql.Identifier(self.receipt.database.schema_name), sql.Identifier(join_table.name)
                )
            )
            self.assertEqual(cursor.fetchone()[0], 0)

    def test_a_duplicate_pair_raw_insert_bypassing_records_py_is_still_rejected(self):
        item = self._create_item([self.group_a])
        join_table = self._join_table()
        with self.assertRaises(IntegrityError):
            with transaction.atomic(using="tenant"):
                with connections["tenant"].cursor() as cursor:
                    cursor.execute(
                        sql.SQL("INSERT INTO {}.{} (source_id, target_id) VALUES (%s, %s)").format(
                            sql.Identifier(self.receipt.database.schema_name), sql.Identifier(join_table.name)
                        ),
                        [item["id"], self.group_a],
                    )

    def test_unsanctioned_direct_write_to_the_join_tables_catalog_row_is_rejected(self):
        """Parity with the existing trigger-guard security tests
        (test_field_indexing.py) -- a join table's own catalog row is
        just another row on databases_dbtable, governed by the same
        app_runtime_catalog_guard trigger, with no special-case carve-out
        for M:M."""
        join_table = self._join_table()
        with self.assertRaises(Exception) as ctx:
            DBTable.objects.filter(pk=join_table.id).update(name="hacked")
        self.assertIn("Managed runtime catalog requires a schema migration", str(ctx.exception))

    def test_concurrent_addition_of_the_same_new_pair_the_database_constraint_is_the_real_gate(self):
        """Mirrors test_field_indexing.py's own concurrency proof: the
        diff in update_record is deliberately racy (see its docstring) --
        the real UNIQUE(source_id, target_id) constraint on the join
        table is what actually prevents a duplicate pair from landing
        when two requests race to add the exact same new association."""
        item = self._create_item([])

        def add_group(_):
            close_old_connections()
            client = APIClient()
            client.force_authenticate(self.actor)
            try:
                return client.patch(
                    f"{self.items_url}{item['id']}/", {self.relation_id: [self.group_a]}, format="json"
                )
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as pool:
            responses = list(pool.map(add_group, [None, None]))

        statuses = sorted(r.status_code for r in responses)
        self.assertEqual(statuses, [200, 400])
        detail = self.client.get(f"{self.items_url}{item['id']}/")
        self.assertEqual(detail.data[self.relation_id], [self.group_a])
