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
