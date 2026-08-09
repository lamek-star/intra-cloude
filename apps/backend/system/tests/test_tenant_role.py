"""
Phase 11 (docs/security/THREAT_MODEL.md TB3): provisioning a genuinely
least-privilege tenant-database role, verified against the real live
tenant PostgreSQL server — not just that the SQL ran, but that the new
role can actually do what it's supposed to (CREATE SCHEMA) and cannot do
what it must not (CREATE DATABASE, a superuser/CREATEDB-only operation).
"""

import uuid

import psycopg
from django.db import connections
from django.test import TestCase

from system.tenant_role import TenantRoleError, provision_role


class ProvisionTenantRoleTests(TestCase):
    databases = {"tenant"}

    def setUp(self):
        self.role_name = f"pdc_test_role_{uuid.uuid4().hex[:12]}"
        self.password = "a-real-generated-password-1!"
        self.db = connections["tenant"].settings_dict

    def _connect_kwargs(self, dbname):
        return {
            "host": self.db["HOST"] or "localhost",
            "port": int(self.db["PORT"] or 5432),
            "dbname": dbname,
            "user": self.db["USER"],
            "password": self.db["PASSWORD"],
            "autocommit": True,
        }

    def tearDown(self):
        # The schema is a tenant-database-local object — dropping it has
        # to happen on a connection to that database, not "postgres".
        with psycopg.connect(**self._connect_kwargs(self.db["NAME"])) as conn, conn.cursor() as cur:
            cur.execute(f'DROP SCHEMA IF EXISTS "test_schema_{self.role_name}" CASCADE')  # noqa: S608

        # DROP ROLE fails while the role still holds the GRANT ... ON
        # DATABASE privilege provision_role() gave it — confirmed by
        # actually running this: "role ... cannot be dropped because some
        # objects depend on it / privileges for database ...". Revoke
        # first, from any connection (database-level ACLs aren't scoped
        # to "being connected to that database").
        with psycopg.connect(**self._connect_kwargs("postgres")) as conn, conn.cursor() as cur:
            cur.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", [self.role_name])
            if cur.fetchone():
                cur.execute(f'REVOKE ALL PRIVILEGES ON DATABASE "{self.db["NAME"]}" FROM "{self.role_name}"')
                cur.execute(f'DROP ROLE "{self.role_name}"')

    def _connect_as_new_role(self):
        return psycopg.connect(
            host=self.db["HOST"] or "localhost",
            port=int(self.db["PORT"] or 5432),
            dbname=self.db["NAME"],
            user=self.role_name,
            password=self.password,
            autocommit=True,
            connect_timeout=10,
        )

    def test_new_role_can_create_a_schema_but_not_a_database(self):
        provision_role(self.role_name, self.password)

        schema_name = f"test_schema_{self.role_name}"
        with self._connect_as_new_role() as conn, conn.cursor() as cur:
            # CREATE grant on the database is enough to CREATE SCHEMA —
            # exactly what databases/services.py needs for org databases.
            cur.execute(f'CREATE SCHEMA "{schema_name}"')  # noqa: S608

        with self._connect_as_new_role() as conn, conn.cursor() as cur:
            with self.assertRaises(psycopg.errors.InsufficientPrivilege):
                cur.execute(f'CREATE DATABASE "some_db_{self.role_name}"')  # noqa: S608

    def test_new_role_is_not_superuser_and_cannot_createdb_or_createrole(self):
        provision_role(self.role_name, self.password)

        with psycopg.connect(
            host=self.db["HOST"] or "localhost",
            port=int(self.db["PORT"] or 5432),
            dbname="postgres",
            user=self.db["USER"],
            password=self.db["PASSWORD"],
            autocommit=True,
        ) as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT rolsuper, rolcreatedb, rolcreaterole FROM pg_roles WHERE rolname = %s",
                [self.role_name],
            )
            rolsuper, rolcreatedb, rolcreaterole = cur.fetchone()
        self.assertFalse(rolsuper)
        self.assertFalse(rolcreatedb)
        self.assertFalse(rolcreaterole)

    def test_provisioning_a_duplicate_role_name_is_rejected(self):
        provision_role(self.role_name, self.password)
        with self.assertRaises(TenantRoleError):
            provision_role(self.role_name, "a-different-password-1!")
