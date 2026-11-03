"""
Full round-trip integration tests against a real PostgreSQL tenant
connection — every DDL operation is verified by actually querying
`information_schema` afterward, not just asserting the API response.
"""

from django.db import connections
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import User
from databases.models import TenantDatabase
from organizations.models import Membership
from permissions.management.commands.seed_permissions import Command as SeedPermissionsCommand


class DatabaseBuilderTestBase(APITestCase):
    databases = {"default", "tenant"}

    def setUp(self):
        SeedPermissionsCommand().handle()
        self.admin = User.objects.create_user(email="db-admin@example.com", password="x")
        self.client.force_login(self.admin)

        org = self.client.post(reverse("organization-list-create"), {"name": "Acme"})
        self.org_id = org.data["id"]
        ws = self.client.post(reverse("workspace-list-create", args=[self.org_id]), {"name": "WS"})
        proj = self.client.post(reverse("project-list-create", args=[ws.data["id"]]), {"name": "Proj"})
        self.project_id = proj.data["id"]


class TenantDatabaseCreationTests(DatabaseBuilderTestBase):
    def test_create_tenant_database_creates_real_schema(self):
        resp = self.client.post(
            reverse("tenant-database-list-create", args=[self.project_id]), {"name": "Analytics"}
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        db_id = resp.data["id"]
        tenant_db = TenantDatabase.objects.get(id=db_id)

        with connections["tenant"].cursor() as cursor:
            cursor.execute(
                "SELECT schema_name FROM information_schema.schemata WHERE schema_name = %s",
                [tenant_db.schema_name],
            )
            self.assertIsNotNone(cursor.fetchone())

    def test_delete_tenant_database_drops_real_schema(self):
        create = self.client.post(
            reverse("tenant-database-list-create", args=[self.project_id]), {"name": "Temp"}
        )
        db_id = create.data["id"]
        schema_name = TenantDatabase.objects.get(id=db_id).schema_name

        resp = self.client.delete(reverse("tenant-database-detail", args=[db_id]))
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)

        with connections["tenant"].cursor() as cursor:
            cursor.execute(
                "SELECT schema_name FROM information_schema.schemata WHERE schema_name = %s",
                [schema_name],
            )
            self.assertIsNone(cursor.fetchone())


class TableColumnForeignKeyTests(DatabaseBuilderTestBase):
    def setUp(self):
        super().setUp()
        db = self.client.post(reverse("tenant-database-list-create", args=[self.project_id]), {"name": "App"})
        self.tenant_database_id = db.data["id"]
        self.schema_name = TenantDatabase.objects.get(id=self.tenant_database_id).schema_name

    def test_create_table_creates_real_table_with_uuid_pk(self):
        resp = self.client.post(
            reverse("table-list-create", args=[self.tenant_database_id]), {"name": "customers"}
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(len(resp.data["columns"]), 1)
        self.assertEqual(resp.data["columns"][0]["name"], "id")

        with connections["tenant"].cursor() as cursor:
            cursor.execute(
                "SELECT data_type FROM information_schema.columns "
                "WHERE table_schema=%s AND table_name=%s AND column_name='id'",
                [self.schema_name, "customers"],
            )
            self.assertEqual(cursor.fetchone()[0], "uuid")

    def test_add_column_creates_real_column_with_correct_type(self):
        table = self.client.post(
            reverse("table-list-create", args=[self.tenant_database_id]), {"name": "customers"}
        )
        table_id = table.data["id"]

        resp = self.client.post(
            reverse("column-create", args=[table_id]),
            {
                "name": "email",
                "data_type": "varchar",
                "max_length": 320,
                "is_nullable": False,
                "is_unique": True,
            },
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

        with connections["tenant"].cursor() as cursor:
            cursor.execute(
                "SELECT data_type, character_maximum_length, is_nullable FROM information_schema.columns "
                "WHERE table_schema=%s AND table_name=%s AND column_name='email'",
                [self.schema_name, "customers"],
            )
            data_type, max_len, is_nullable = cursor.fetchone()
            self.assertEqual(data_type, "character varying")
            self.assertEqual(max_len, 320)
            self.assertEqual(is_nullable, "NO")

    def test_column_with_injection_shaped_default_is_stored_as_a_safe_literal(self):
        table = self.client.post(
            reverse("table-list-create", args=[self.tenant_database_id]), {"name": "notes"}
        )
        table_id = table.data["id"]

        malicious = "'; DROP TABLE notes; --"
        resp = self.client.post(
            reverse("column-create", args=[table_id]),
            {"name": "body", "data_type": "text", "default_value": malicious},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

        with connections["tenant"].cursor() as cursor:
            # If the injection had worked, this table would no longer exist.
            cursor.execute(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema=%s AND table_name='notes'",
                [self.schema_name],
            )
            self.assertIsNotNone(cursor.fetchone())

            cursor.execute(
                "SELECT column_default FROM information_schema.columns "
                "WHERE table_schema=%s AND table_name='notes' AND column_name='body'",
                [self.schema_name],
            )
            default_text = cursor.fetchone()[0]
            self.assertIn(malicious.replace("'", "''"), default_text)

    def test_reject_table_name_with_injection_attempt(self):
        resp = self.client.post(
            reverse("table-list-create", args=[self.tenant_database_id]),
            {"name": "customers; DROP SCHEMA public CASCADE; --"},
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_reject_column_name_with_injection_attempt(self):
        table = self.client.post(
            reverse("table-list-create", args=[self.tenant_database_id]), {"name": "widgets"}
        )
        resp = self.client.post(
            reverse("column-create", args=[table.data["id"]]),
            {"name": "a\"; DROP TABLE widgets; --", "data_type": "text"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_add_foreign_key_creates_real_constraint(self):
        customers = self.client.post(
            reverse("table-list-create", args=[self.tenant_database_id]), {"name": "customers"}
        )
        orders = self.client.post(
            reverse("table-list-create", args=[self.tenant_database_id]), {"name": "orders"}
        )
        orders_id = orders.data["id"]
        customers_pk_id = customers.data["columns"][0]["id"]

        fk_column = self.client.post(
            reverse("column-create", args=[orders_id]),
            {"name": "customer_id", "data_type": "uuid", "is_nullable": False},
            format="json",
        )

        resp = self.client.post(
            reverse("foreign-key-create", args=[orders_id]),
            {
                "column_id": fk_column.data["id"],
                "references_table_id": customers.data["id"],
                "references_column_id": customers_pk_id,
                "on_delete": "cascade",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

        with connections["tenant"].cursor() as cursor:
            cursor.execute(
                "SELECT constraint_type FROM information_schema.table_constraints "
                "WHERE table_schema=%s AND table_name='orders' AND constraint_type='FOREIGN KEY'",
                [self.schema_name],
            )
            self.assertIsNotNone(cursor.fetchone())

    def test_foreign_key_type_mismatch_is_rejected(self):
        customers = self.client.post(
            reverse("table-list-create", args=[self.tenant_database_id]), {"name": "customers2"}
        )
        orders = self.client.post(
            reverse("table-list-create", args=[self.tenant_database_id]), {"name": "orders2"}
        )
        fk_column = self.client.post(
            reverse("column-create", args=[orders.data["id"]]),
            {"name": "customer_ref", "data_type": "text"},  # wrong type on purpose
            format="json",
        )

        resp = self.client.post(
            reverse("foreign-key-create", args=[orders.data["id"]]),
            {
                "column_id": fk_column.data["id"],
                "references_table_id": customers.data["id"],
                "references_column_id": customers.data["columns"][0]["id"],
            },
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_delete_table_drops_real_table(self):
        table = self.client.post(
            reverse("table-list-create", args=[self.tenant_database_id]), {"name": "temp_table"}
        )
        table_id = table.data["id"]

        resp = self.client.delete(reverse("table-detail", args=[table_id]))
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)

        with connections["tenant"].cursor() as cursor:
            cursor.execute(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema=%s AND table_name='temp_table'",
                [self.schema_name],
            )
            self.assertIsNone(cursor.fetchone())


class DatabaseBuilderPermissionTests(DatabaseBuilderTestBase):
    def test_member_without_database_create_permission_is_forbidden(self):
        member = User.objects.create_user(email="plain@example.com", password="x")
        Membership.objects.create(
            user=member, organization_id=self.org_id, status=Membership.Status.ACTIVE
        )
        self.client.force_login(member)

        resp = self.client.post(
            reverse("tenant-database-list-create", args=[self.project_id]), {"name": "Nope"}
        )
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)


class SchemaReadVisibilityTests(DatabaseBuilderTestBase):
    """
    An active organization member with no role or ShareGrant/ResourceGrant
    on a tenant database must not be able to read its schema (table/column
    names and types) — matching the row-data endpoints (test_rows.py's
    RowPermissionTests) and storage's FileListCreateView, both of which
    already require the matching `*.read` permission before listing
    anything. The tenant-database and table detail/list endpoints
    previously only checked organization membership, leaking schema
    metadata to any member regardless of Sharing settings.
    """

    def setUp(self):
        super().setUp()
        db = self.client.post(
            reverse("tenant-database-list-create", args=[self.project_id]), {"name": "CRM"}
        )
        self.db_id = db.data["id"]
        table = self.client.post(reverse("table-list-create", args=[self.db_id]), {"name": "contacts"})
        self.table_id = table.data["id"]

        self.outsider = User.objects.create_user(email="schema-outsider@example.com", password="x")
        Membership.objects.create(
            user=self.outsider, organization_id=self.org_id, status=Membership.Status.ACTIVE
        )
        self.client.force_login(self.outsider)

    def test_member_without_database_read_cannot_view_database_detail(self):
        resp = self.client.get(reverse("tenant-database-detail", args=[self.db_id]))
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_member_without_database_read_cannot_list_tables(self):
        resp = self.client.get(reverse("table-list-create", args=[self.db_id]))
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_member_without_database_read_cannot_view_table_detail(self):
        resp = self.client.get(reverse("table-detail", args=[self.table_id]))
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_a_share_grant_restores_read_access_to_the_schema(self):
        self.client.force_login(self.admin)
        share = self.client.post(
            reverse("share-grant-list-create", args=[self.org_id]),
            {
                "resource_type": "databases.tenant_database",
                "resource_id": self.db_id,
                "principal_type": "user",
                "user_id": str(self.outsider.id),
                "level": "read",
            },
            format="json",
        )
        self.assertEqual(share.status_code, status.HTTP_201_CREATED, share.data)

        self.client.force_login(self.outsider)
        resp = self.client.get(reverse("table-list-create", args=[self.db_id]))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data), 1)


class TenantDatabaseListVisibilityTests(DatabaseBuilderTestBase):
    """TenantDatabaseListCreateView.get previously listed every
    TenantDatabase in a project (name, created_by) via get_member_project
    only -- no database.read check at all, role-wide or resource-scoped
    -- the same class of gap as SchemaReadVisibilityTests above, on the
    list-at-the-project-level sibling endpoint. Fixed by filtering per-
    database (role-wide OR a per-database ResourceGrant), matching
    storage's identical BucketListCreateView.get fix, since database.read
    is resource-scoped at the TenantDatabase level and a single
    all-or-nothing check would incorrectly hide a database the caller can
    already reach directly via a ResourceGrant."""

    def setUp(self):
        super().setUp()
        visible = self.client.post(
            reverse("tenant-database-list-create", args=[self.project_id]), {"name": "Visible"}
        )
        self.visible_db_id = visible.data["id"]
        hidden = self.client.post(
            reverse("tenant-database-list-create", args=[self.project_id]), {"name": "Hidden"}
        )
        self.hidden_db_id = hidden.data["id"]

        self.outsider = User.objects.create_user(email="dblist-outsider@example.com", password="x")
        Membership.objects.create(
            user=self.outsider, organization_id=self.org_id, status=Membership.Status.ACTIVE
        )
        self.client.force_login(self.outsider)

    def test_member_with_no_grants_sees_no_databases(self):
        resp = self.client.get(reverse("tenant-database-list-create", args=[self.project_id]))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data, [])

    def test_member_with_a_resource_grant_on_one_database_sees_only_that_one(self):
        from permissions.services import grant_resource_permission

        grant_resource_permission(
            user=self.outsider,
            permission_code="database.read",
            organization_id=self.org_id,
            resource_type="databases.tenant_database",
            resource_id=self.visible_db_id,
            granted_by=self.admin,
        )

        resp = self.client.get(reverse("tenant-database-list-create", args=[self.project_id]))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual([d["id"] for d in resp.data], [self.visible_db_id])


class RowRuleViolationTests(DatabaseBuilderTestBase):
    """A row the database refuses (unique value, link to a missing row) is a clear
    400 with a reason, never a 500 -- and nothing is written."""

    def setUp(self):
        super().setUp()
        db = self.client.post(reverse("tenant-database-list-create", args=[self.project_id]), {"name": "HR"})
        self.tenant_database_id = db.data["id"]
        tables_url = reverse("table-list-create", args=[self.tenant_database_id])
        units = self.client.post(tables_url, {"name": "units"})
        staff = self.client.post(tables_url, {"name": "staff"})
        self.staff_id = staff.data["id"]
        self.client.post(
            reverse("column-create", args=[self.staff_id]),
            {"name": "employee_no", "data_type": "varchar", "max_length": 20, "is_unique": True},
            format="json",
        )
        unit_col = self.client.post(
            reverse("column-create", args=[self.staff_id]),
            {"name": "unit_id", "data_type": "uuid", "is_nullable": True},
            format="json",
        )
        self.client.post(
            reverse("foreign-key-create", args=[self.staff_id]),
            {
                "column_id": unit_col.data["id"],
                "references_table_id": units.data["id"],
                "references_column_id": units.data["columns"][0]["id"],
                "on_delete": "restrict",
            },
            format="json",
        )
        self.rows_url = reverse("row-list-create", args=[self.staff_id])

    def _count(self):
        return self.client.get(self.rows_url).data["count"]

    def test_a_duplicate_unique_value_is_a_clear_400(self):
        first = self.client.post(self.rows_url, {"employee_no": "EMP-1"}, format="json")
        self.assertEqual(first.status_code, status.HTTP_201_CREATED)
        dup = self.client.post(self.rows_url, {"employee_no": "EMP-1"}, format="json")
        self.assertEqual(dup.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("already exists", dup.data["detail"])
        self.assertEqual(self._count(), 1)

    def test_a_link_to_a_missing_row_is_a_clear_400(self):
        missing_unit = "00000000-0000-4000-8000-000000000001"
        body = {"employee_no": "EMP-2", "unit_id": missing_unit}
        resp = self.client.post(self.rows_url, body, format="json")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("linked row does not exist", resp.data["detail"])
        self.assertEqual(self._count(), 0)

    def test_an_update_to_a_duplicate_value_is_a_clear_400_and_changes_nothing(self):
        self.client.post(self.rows_url, {"employee_no": "EMP-1"}, format="json")
        other = self.client.post(self.rows_url, {"employee_no": "EMP-2"}, format="json")
        detail_url = reverse("row-detail", args=[self.staff_id, other.data["id"]])
        resp = self.client.patch(detail_url, {"employee_no": "EMP-1"}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("already exists", resp.data["detail"])
        kept = self.client.get(detail_url)
        self.assertEqual(kept.data["employee_no"], "EMP-2")


class LinkedRowLookupTests(DatabaseBuilderTestBase):
    """H8: the data explorer can list a table's links and fetch the linked rows by id, so it can
    show a name instead of a raw id -- both need database.read."""

    def setUp(self):
        super().setUp()
        db = self.client.post(reverse("tenant-database-list-create", args=[self.project_id]), {"name": "Lib"})
        tables_url = reverse("table-list-create", args=[db.data["id"]])
        books = self.client.post(tables_url, {"name": "books"})
        loans = self.client.post(tables_url, {"name": "loans"})
        self.books_id, self.loans_id = books.data["id"], loans.data["id"]
        self.client.post(
            reverse("column-create", args=[self.books_id]),
            {"name": "title", "data_type": "text"},
            format="json",
        )
        book_col = self.client.post(
            reverse("column-create", args=[self.loans_id]),
            {"name": "book_id", "data_type": "uuid", "is_nullable": True},
            format="json",
        )
        self.client.post(
            reverse("foreign-key-create", args=[self.loans_id]),
            {
                "column_id": book_col.data["id"],
                "references_table_id": self.books_id,
                "references_column_id": books.data["columns"][0]["id"],
            },
            format="json",
        )
        rows_url = reverse("row-list-create", args=[self.books_id])
        self.book_ids = [
            str(self.client.post(rows_url, {"title": t}, format="json").data["id"]) for t in ("A", "B", "C")
        ]

    def test_the_tables_links_are_listed(self):
        resp = self.client.get(reverse("foreign-key-create", args=[self.loans_id]))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data), 1)
        self.assertEqual(str(resp.data[0]["references_table"]), self.books_id)

    def test_rows_can_be_fetched_by_id(self):
        resp = self.client.get(
            reverse("row-list-create", args=[self.books_id]), {"ids": ",".join(self.book_ids[:2])}
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual({r["title"] for r in resp.data["results"]}, {"A", "B"})

    def test_malformed_ids_are_a_400(self):
        resp = self.client.get(reverse("row-list-create", args=[self.books_id]), {"ids": "not-an-id"})
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_a_member_without_database_read_gets_neither(self):
        outsider = User.objects.create_user(email="db-reader-none@example.com", password="x")
        Membership.objects.create(user=outsider, organization_id=self.org_id, status=Membership.Status.ACTIVE)
        self.client.force_login(outsider)
        self.assertEqual(
            self.client.get(reverse("foreign-key-create", args=[self.loans_id])).status_code,
            status.HTTP_403_FORBIDDEN,
        )
        resp = self.client.get(reverse("row-list-create", args=[self.books_id]), {"ids": self.book_ids[0]})
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)
