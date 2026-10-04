"""`databases.rows.update_row_if` -- the compare-and-swap primitive App
Platform's Phase 5 workflow engine uses to apply a state transition
concurrency-safely (docs/implementation/APP_PLATFORM_PHASE5.md). Proves
the primitive itself against a real PostgreSQL connection, independent of
App Platform, mirroring test_indexing.py's own service-level structure."""

from concurrent.futures import ThreadPoolExecutor

from django.db import close_old_connections, connections
from django.test import TransactionTestCase
from psycopg import sql

from accounts.models import User
from databases import services
from databases.rows import RowConflict, RowNotFound, get_row, insert_row, update_row_if
from organizations.services import create_organization
from permissions.management.commands.seed_permissions import Command as SeedPermissionsCommand
from workspaces.models import Project, Workspace


class UpdateRowIfTestBase(TransactionTestCase):
    databases = {"default", "tenant"}

    def setUp(self):
        SeedPermissionsCommand().handle()
        self.actor = User.objects.create_user(email="cas-admin@example.com")
        self.org = create_organization(name="CAS Org", created_by=self.actor)
        workspace = Workspace.objects.create(organization=self.org, name="WS", created_by=self.actor)
        project = Project.objects.create(workspace=workspace, name="Proj", created_by=self.actor)
        self.tenant_db = services.create_tenant_database(actor=self.actor, project=project, name="DB")
        self.table = services.create_table(actor=self.actor, tenant_database=self.tenant_db, name="tickets")
        services.add_column(actor=self.actor, table=self.table, name="status", data_type="text")
        services.add_column(actor=self.actor, table=self.table, name="closed_by", data_type="text")
        self.row = insert_row(self.table, {"status": "pending"})

    def tearDown(self):
        with connections["tenant"].cursor() as cursor:
            cursor.execute(
                sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE").format(sql.Identifier(self.tenant_db.schema_name))
            )
        super().tearDown()


class UpdateRowIfTests(UpdateRowIfTestBase):
    def test_matching_expected_value_succeeds(self):
        updated = update_row_if(
            self.table, self.row["id"], expected={"status": "pending"}, data={"status": "approved"}
        )
        self.assertEqual(updated["status"], "approved")

    def test_stale_expected_value_raises_conflict_not_a_silent_overwrite(self):
        update_row_if(self.table, self.row["id"], expected={"status": "pending"}, data={"status": "approved"})
        with self.assertRaises(RowConflict):
            update_row_if(
                self.table, self.row["id"], expected={"status": "pending"}, data={"status": "rejected"}
            )
        # The winning write is untouched by the loser's failed attempt.
        self.assertEqual(get_row(self.table, self.row["id"])["status"], "approved")

    def test_missing_row_raises_not_found_not_conflict(self):
        with self.assertRaises(RowNotFound):
            update_row_if(
                self.table, "00000000-0000-0000-0000-000000000000",
                expected={"status": "pending"}, data={"status": "approved"},
            )

    def test_empty_expected_matches_any_current_value(self):
        updated = update_row_if(self.table, self.row["id"], expected={}, data={"status": "approved"})
        self.assertEqual(updated["status"], "approved")

    def test_multiple_expected_columns_and_multiple_set_columns(self):
        updated = update_row_if(
            self.table, self.row["id"],
            expected={"status": "pending", "closed_by": None},
            data={"status": "approved", "closed_by": "alice"},
        )
        self.assertEqual(updated["status"], "approved")
        self.assertEqual(updated["closed_by"], "alice")

    def test_concurrent_mutually_exclusive_updates_exactly_one_wins(self):
        """The exact scenario this primitive exists for: two different,
        mutually-exclusive transitions racing on the same starting state --
        the database's own compare-and-swap is the real gate, not an
        application-level lock (mirrors test_composite_constraints.py's
        own concurrency-test pattern)."""

        def attempt(target_status):
            close_old_connections()
            try:
                update_row_if(
                    self.table, self.row["id"], expected={"status": "pending"}, data={"status": target_status}
                )
                return target_status
            except RowConflict:
                return None
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(attempt, ["approved", "rejected"]))

        winners = [r for r in results if r is not None]
        self.assertEqual(len(winners), 1)
        self.assertEqual(get_row(self.table, self.row["id"])["status"], winners[0])
