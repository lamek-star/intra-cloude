"""Post-Phase-3 Integration Enablement, Part 2/3: generic B-tree indexing
and single-field uniqueness for App Platform fields, at the underlying
`databases.services` primitive level (`add_column`'s new `is_indexed`
parameter, plus the new `add_unique_constraint`/`add_index` retrofit
functions for an already-materialized column). App Platform's own
schema_evolution.py wiring is covered separately in
app_platform/tests/test_field_indexing.py; this file proves the
primitives themselves are correct against a real PostgreSQL connection,
independent of App Platform."""

from django.db import connections
from django.test import TestCase
from psycopg import sql

from accounts.models import User
from databases import services
from databases.models import DBIndex
from databases.services import SchemaValidationError
from organizations.services import create_organization
from permissions.management.commands.seed_permissions import Command as SeedPermissionsCommand
from workspaces.models import Project, Workspace


class IndexingTestBase(TestCase):
    databases = {"default", "tenant"}

    def setUp(self):
        SeedPermissionsCommand().handle()
        self.actor = User.objects.create_user(email="index-admin@example.com")
        self.org = create_organization(name="Index Org", created_by=self.actor)
        workspace = Workspace.objects.create(organization=self.org, name="WS", created_by=self.actor)
        project = Project.objects.create(workspace=workspace, name="Proj", created_by=self.actor)
        self.tenant_db = services.create_tenant_database(actor=self.actor, project=project, name="DB")
        self.table = services.create_table(actor=self.actor, tenant_database=self.tenant_db, name="parts")

    def tearDown(self):
        with connections["tenant"].cursor() as cursor:
            cursor.execute(
                sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE").format(sql.Identifier(self.tenant_db.schema_name))
            )
        super().tearDown()

    def _real_indexes(self, table_name):
        with connections["tenant"].cursor() as cursor:
            cursor.execute(
                "SELECT indexname, indexdef FROM pg_indexes WHERE schemaname = %s AND tablename = %s",
                [self.tenant_db.schema_name, table_name],
            )
            return {row[0]: row[1] for row in cursor.fetchall()}

    def _insert(self, column_name, value):
        with connections["tenant"].cursor() as cursor:
            cursor.execute(
                sql.SQL("INSERT INTO {}.{} ({}) VALUES (%s) RETURNING id").format(
                    sql.Identifier(self.tenant_db.schema_name),
                    sql.Identifier(self.table.name),
                    sql.Identifier(column_name),
                ),
                [value],
            )
            return cursor.fetchone()[0]

    def _insert_default_values(self):
        with connections["tenant"].cursor() as cursor:
            cursor.execute(
                sql.SQL("INSERT INTO {}.{} DEFAULT VALUES").format(
                    sql.Identifier(self.tenant_db.schema_name), sql.Identifier(self.table.name)
                )
            )


class NewColumnIndexingTests(IndexingTestBase):
    def test_add_column_with_is_indexed_creates_a_real_non_unique_index(self):
        column = services.add_column(
            actor=self.actor, table=self.table, name="sku", data_type="text", is_indexed=True
        )
        self.assertFalse(column.is_unique)
        indexes = self._real_indexes(self.table.name)
        self.assertIn(f"idx_{column.id.hex}", indexes)
        self.assertNotIn("UNIQUE", indexes[f"idx_{column.id.hex}"])

        db_index = DBIndex.objects.get(table=self.table, columns=column)
        self.assertFalse(db_index.is_unique)

    def test_add_column_with_is_unique_still_works_and_creates_exactly_one_new_index(self):
        # Inline `ADD COLUMN ... UNIQUE` lets Postgres auto-name the
        # resulting constraint/index itself (e.g. "parts_code_key") --
        # pre-existing behavior, unrelated to this change -- so the real
        # pg_indexes name never actually matches DBIndex.name here (unlike
        # the new add_unique_constraint/add_index retrofit paths below,
        # which explicitly name their own DDL to match).
        before = self._real_indexes(self.table.name)  # the primary key's own implicit index
        services.add_column(actor=self.actor, table=self.table, name="code", data_type="text", is_unique=True)
        indexes = self._real_indexes(self.table.name)
        self.assertEqual(len(indexes), len(before) + 1)
        new_index_def = next(v for k, v in indexes.items() if k not in before)
        self.assertIn("UNIQUE", new_index_def)
        self.assertIn("(code)", new_index_def)

    def test_adding_a_unique_column_to_a_populated_table_with_a_shared_default_fails_cleanly(self):
        self._insert_default_values()
        self._insert_default_values()
        before = self._real_indexes(self.table.name)

        with self.assertRaises(SchemaValidationError):
            services.add_column(
                actor=self.actor,
                table=self.table,
                name="dupe_default",
                data_type="text",
                is_unique=True,
                default_value="same-for-everyone",
            )
        # No partial column, no partial index -- the whole ALTER TABLE
        # rolled back as one transaction.
        self.assertEqual(self._real_indexes(self.table.name), before)
        with connections["tenant"].cursor() as cursor:
            cursor.execute(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_schema=%s AND table_name=%s AND column_name='dupe_default'",
                [self.tenant_db.schema_name, self.table.name],
            )
            self.assertIsNone(cursor.fetchone())


class RetrofitUniqueConstraintTests(IndexingTestBase):
    def setUp(self):
        super().setUp()
        self.column = services.add_column(
            actor=self.actor, table=self.table, name="normalized_number", data_type="text"
        )

    def test_add_unique_constraint_on_clean_data_succeeds(self):
        self._insert("normalized_number", "AAA111")
        self._insert("normalized_number", "BBB222")

        index = services.add_unique_constraint(actor=self.actor, column=self.column)
        self.assertTrue(index.is_unique)
        self.column.refresh_from_db()
        self.assertTrue(self.column.is_unique)

        indexes = self._real_indexes(self.table.name)
        self.assertIn(index.name, indexes)
        self.assertIn("UNIQUE", indexes[index.name])

    def test_add_unique_constraint_fails_safely_when_duplicates_exist(self):
        self._insert("normalized_number", "SAME")
        self._insert("normalized_number", "SAME")
        before_rows = self._count_rows()
        before_indexes = self._real_indexes(self.table.name)

        with self.assertRaises(SchemaValidationError):
            services.add_unique_constraint(actor=self.actor, column=self.column)

        # No destructive reconciliation: both duplicate rows still exist,
        # no index was left half-created.
        self.assertEqual(self._count_rows(), before_rows)
        self.assertEqual(self._real_indexes(self.table.name), before_indexes)
        self.column.refresh_from_db()
        self.assertFalse(self.column.is_unique)

    def test_add_unique_constraint_is_idempotent(self):
        self._insert("normalized_number", "ONLYONE")
        first = services.add_unique_constraint(actor=self.actor, column=self.column)
        second = services.add_unique_constraint(actor=self.actor, column=self.column)
        self.assertEqual(first.id, second.id)
        self.assertEqual(DBIndex.objects.filter(table=self.table, columns=self.column).count(), 1)

    def _count_rows(self):
        with connections["tenant"].cursor() as cursor:
            cursor.execute(
                sql.SQL("SELECT COUNT(*) FROM {}.{}").format(
                    sql.Identifier(self.tenant_db.schema_name), sql.Identifier(self.table.name)
                )
            )
            return cursor.fetchone()[0]


class RetrofitIndexTests(IndexingTestBase):
    def test_add_index_on_an_existing_column_creates_a_real_non_unique_index(self):
        column = services.add_column(actor=self.actor, table=self.table, name="make", data_type="text")
        index = services.add_index(actor=self.actor, column=column)
        self.assertFalse(index.is_unique)
        indexes = self._real_indexes(self.table.name)
        self.assertIn(index.name, indexes)
        self.assertNotIn("UNIQUE", indexes[index.name])

    def test_add_index_is_idempotent(self):
        column = services.add_column(actor=self.actor, table=self.table, name="model", data_type="text")
        first = services.add_index(actor=self.actor, column=column)
        second = services.add_index(actor=self.actor, column=column)
        self.assertEqual(first.id, second.id)
        self.assertEqual(DBIndex.objects.filter(table=self.table, columns=column).count(), 1)

    def test_add_index_on_an_already_unique_column_returns_its_existing_index(self):
        column = services.add_column(
            actor=self.actor, table=self.table, name="serial", data_type="text", is_unique=True
        )
        unique_index = DBIndex.objects.get(table=self.table, columns=column)
        returned = services.add_index(actor=self.actor, column=column)
        self.assertEqual(returned.id, unique_index.id)
        self.assertTrue(returned.is_unique)
