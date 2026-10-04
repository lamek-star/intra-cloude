"""Native many-to-many relationships for App Platform, Step 2: the
underlying `databases.services.add_composite_unique_constraint` primitive
-- a narrow, join-table-specific "exactly two named columns" constraint,
deliberately distinct from the deferred, out-of-scope general composite-
uniqueness-for-arbitrary-fields feature (see
docs/SPARE_PARTS_INTEGRATION_READINESS.md). Proven here against a real
PostgreSQL connection, independent of App Platform -- app_platform's own
join-table provisioning is covered separately in
app_platform/tests/test_many_to_many.py."""

import uuid

from django.core.management import call_command
from django.db import IntegrityError, connections, transaction
from django.test import TestCase, TransactionTestCase
from psycopg import sql

from accounts.models import User
from app_platform import instances, provisioning, schema_evolution, templates
from app_platform.runtime_plan import plan_runtime
from app_platform.tests.test_foundation import project_for, sample
from databases import services
from databases.models import DBIndex
from databases.services import SchemaPermissionDenied, SchemaValidationError
from organizations.services import create_organization
from permissions.management.commands.seed_permissions import Command as SeedPermissionsCommand
from workspaces.models import Project, Workspace


class JoinTableConstraintTests(TestCase):
    databases = {"default", "tenant"}

    def setUp(self):
        SeedPermissionsCommand().handle()
        self.actor = User.objects.create_user(email="join-admin@example.com")
        self.org = create_organization(name="Join Org", created_by=self.actor)
        workspace = Workspace.objects.create(organization=self.org, name="WS", created_by=self.actor)
        project = Project.objects.create(workspace=workspace, name="Proj", created_by=self.actor)
        self.tenant_db = services.create_tenant_database(actor=self.actor, project=project, name="DB")
        self.table = services.create_table(
            actor=self.actor, tenant_database=self.tenant_db, name="j_item_group"
        )
        self.column_a = services.add_column(
            actor=self.actor, table=self.table, name="source_id", data_type="uuid"
        )
        self.column_b = services.add_column(
            actor=self.actor, table=self.table, name="target_id", data_type="uuid"
        )

    def tearDown(self):
        with connections["tenant"].cursor() as cursor:
            cursor.execute(
                sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE").format(sql.Identifier(self.tenant_db.schema_name))
            )
        super().tearDown()

    def _real_indexes(self):
        with connections["tenant"].cursor() as cursor:
            cursor.execute(
                "SELECT indexname, indexdef FROM pg_indexes WHERE schemaname = %s AND tablename = %s",
                [self.tenant_db.schema_name, self.table.name],
            )
            return {row[0]: row[1] for row in cursor.fetchall()}

    def _insert(self, source, target):
        with connections["tenant"].cursor() as cursor:
            cursor.execute(
                sql.SQL("INSERT INTO {}.{} (source_id, target_id) VALUES (%s, %s)").format(
                    sql.Identifier(self.tenant_db.schema_name), sql.Identifier(self.table.name)
                ),
                [source, target],
            )

    def test_creates_a_real_composite_unique_constraint(self):
        index = services.add_composite_unique_constraint(
            actor=self.actor, table=self.table, column_a=self.column_a, column_b=self.column_b
        )
        self.assertTrue(index.is_unique)
        indexes = self._real_indexes()
        self.assertIn(index.name, indexes)
        self.assertIn("UNIQUE", indexes[index.name])
        self.assertIn("source_id", indexes[index.name])
        self.assertIn("target_id", indexes[index.name])

    def test_a_duplicate_pair_raw_insert_is_rejected_by_postgres(self):
        services.add_composite_unique_constraint(
            actor=self.actor, table=self.table, column_a=self.column_a, column_b=self.column_b
        )
        source, target = uuid.uuid4(), uuid.uuid4()
        self._insert(source, target)
        # A nested atomic block gives Postgres a savepoint to roll back to
        # on failure -- without it, the failed INSERT poisons the whole
        # test-wrapping "tenant" transaction, and tearDown's own cleanup
        # query on that same connection then fails too.
        with self.assertRaises(IntegrityError):
            with transaction.atomic(using="tenant"):
                self._insert(source, target)

    def test_the_same_pair_of_values_under_different_ordering_is_still_a_distinct_row(self):
        # A composite UNIQUE(source_id, target_id) constraint is
        # order-sensitive -- (A, B) and (B, A) are different rows. Native
        # M:M treats source/target as directional (join table columns are
        # fixed roles, not a symmetric pair), so this is intentional, not
        # a gap.
        services.add_composite_unique_constraint(
            actor=self.actor, table=self.table, column_a=self.column_a, column_b=self.column_b
        )
        a, b = uuid.uuid4(), uuid.uuid4()
        self._insert(a, b)
        self._insert(b, a)  # must not raise

    def test_is_idempotent(self):
        first = services.add_composite_unique_constraint(
            actor=self.actor, table=self.table, column_a=self.column_a, column_b=self.column_b
        )
        second = services.add_composite_unique_constraint(
            actor=self.actor, table=self.table, column_a=self.column_a, column_b=self.column_b
        )
        self.assertEqual(first.id, second.id)
        self.assertEqual(
            DBIndex.objects.filter(table=self.table, is_unique=True, columns=self.column_a)
            .filter(columns=self.column_b)
            .count(),
            1,
        )

    def test_neither_column_is_individually_marked_unique(self):
        services.add_composite_unique_constraint(
            actor=self.actor, table=self.table, column_a=self.column_a, column_b=self.column_b
        )
        self.column_a.refresh_from_db()
        self.column_b.refresh_from_db()
        self.assertFalse(self.column_a.is_unique)
        self.assertFalse(self.column_b.is_unique)

    def test_denies_an_actor_without_database_schema_manage(self):
        outsider = User.objects.create_user(email="join-outsider@example.com")
        with self.assertRaises(SchemaPermissionDenied):
            services.add_composite_unique_constraint(
                actor=outsider, table=self.table, column_a=self.column_a, column_b=self.column_b
            )

    def test_rejects_a_column_that_belongs_to_a_different_table(self):
        other_table = services.create_table(actor=self.actor, tenant_database=self.tenant_db, name="other")
        other_column = services.add_column(
            actor=self.actor, table=other_table, name="whatever", data_type="uuid"
        )
        with self.assertRaises(SchemaValidationError):
            services.add_composite_unique_constraint(
                actor=self.actor, table=self.table, column_a=self.column_a, column_b=other_column
            )

    def test_rejects_the_same_column_twice(self):
        with self.assertRaises(SchemaValidationError):
            services.add_composite_unique_constraint(
                actor=self.actor, table=self.table, column_a=self.column_a, column_b=self.column_a
            )

class ManagedSchemaGuardTests(TransactionTestCase):
    """A join table is always created inside an already-provisioned App
    Platform runtime (via allow_managed_schema=True, exactly like every
    other schema_evolution.py call) -- proving the ordinary, unprivileged
    path is refused on such a schema, and the sanctioned one is not,
    needs a real provisioned instance rather than a bare tenant DB."""

    databases = {"default", "tenant"}

    def setUp(self):
        call_command("seed_permissions", verbosity=0)
        self.actor = User.objects.create_user(email="join-managed@example.com")
        self.org = create_organization(name="Join Managed Org", created_by=self.actor)
        self.project = project_for(self.actor, self.org)
        template = templates.create_template(self.actor, self.org, {"label": "App", "draft": sample()})
        version = templates.publish_template(self.actor, template)
        self.instance = instances.install(
            self.actor, self.project, {"label": "Runtime", "template_version": str(version.id)}
        )
        self.plan = plan_runtime(self.actor, self.instance)
        provisioning.reserve(self.actor, self.instance, self.plan["fingerprint"])
        self.receipt = provisioning.execute(self.instance.id, self.actor)

    def tearDown(self):
        with connections["tenant"].cursor() as cursor:
            cursor.execute(
                sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE").format(sql.Identifier(self.plan["schema_name"]))
            )
        super().tearDown()

    def test_denies_a_composite_constraint_on_a_managed_application_schema(self):
        # Building a managed-schema table/columns/constraint at all needs
        # the same "SET LOCAL app_platform.schema_evolution = 'on'" flag
        # schema_evolution.py itself sets before touching a provisioned
        # runtime's catalog rows -- allow_managed_schema=True alone only
        # bypasses the Python-level _require_unmanaged_schema check, not
        # the real Postgres trigger guard (app_runtime_catalog_guard).
        with transaction.atomic():
            schema_evolution.require_addition(self.actor, self.instance)
            schema_evolution.mark_addition_transaction()
            managed_table = services.create_table(
                actor=self.actor,
                tenant_database=self.receipt.database,
                name="managed_join",
                allow_managed_schema=True,
            )
            col_a = services.add_column(
                actor=self.actor, table=managed_table, name="a", data_type="uuid", allow_managed_schema=True
            )
            col_b = services.add_column(
                actor=self.actor, table=managed_table, name="b", data_type="uuid", allow_managed_schema=True
            )

            with self.assertRaises(SchemaValidationError):
                services.add_composite_unique_constraint(
                    actor=self.actor, table=managed_table, column_a=col_a, column_b=col_b
                )
            # ...but the sanctioned schema_evolution path (allow_managed_schema=True) works fine:
            index = services.add_composite_unique_constraint(
                actor=self.actor,
                table=managed_table,
                column_a=col_a,
                column_b=col_b,
                allow_managed_schema=True,
            )
        self.assertTrue(index.is_unique)
