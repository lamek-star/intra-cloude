"""MySQL/MariaDB and SQL Server connected databases (ADR-0024), against REAL servers, never mocks: the same
API as PostgreSQL (create with a connection test, schema, rows), a table name that needs quoting, binary
columns shown by size only, the engine's own port when none is given, TLS rules, and a read-only MySQL
session.

Each server is given in the environment, so CI without them skips these:
IF_TEST_MYSQL=host:port:database:user:password        (a user that may only SELECT)
IF_TEST_MYSQL_ADMIN=user:password                      (to create the fixture tables)
IF_TEST_MSSQL=host:port:database:user:password The fixture tables are made by the tests themselves (see
_mysql_fixture / _mssql_fixture)."""

import os
import unittest
import uuid

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITransactionTestCase

from accounts.models import User
from databases.connectors import ConnectionFailed, ConnectionParams, MySQLConnector
from permissions.management.commands.seed_permissions import Command as SeedPermissionsCommand


def _server(name):
    value = os.environ.get(name, "")
    if not value:
        return None
    host, port, database, user, password = value.split(":", 4)
    return {
        "host": host,
        "port": int(port),
        "database_name": database,
        "username": user,
        "password": password,
    }


MYSQL = _server("IF_TEST_MYSQL")
MSSQL = _server("IF_TEST_MSSQL")


class _EngineBase(APITransactionTestCase):
    databases = {"default", "tenant"}
    engine = ""
    server: dict | None = None

    def setUp(self):
        SeedPermissionsCommand().handle()
        self.admin = User.objects.create_user(email=f"{self.engine}-conn@example.com", password="x")
        self.client.force_login(self.admin)
        org = self.client.post(reverse("organization-list-create"), {"name": "Acme"}).data["id"]
        ws = self.client.post(reverse("workspace-list-create", args=[org]), {"name": "WS"}).data["id"]
        self.project_id = self.client.post(reverse("project-list-create", args=[ws]), {"name": "P"}).data[
            "id"
        ]

    def create(self, **overrides):
        body = {
            "name": f"{self.engine} {uuid.uuid4().hex[:6]}",
            "engine": self.engine,
            "sslmode": "prefer",
            **self.server,
        }
        body.update(overrides)
        if overrides.get("port") is None:
            body.pop("port", None)
        return self.client.post(
            reverse("connected-database-list-create", args=[self.project_id]), body, format="json"
        )

    def schema(self, conn_id):
        return {
            t["name"]: t for t in self.client.get(reverse("connected-database-schema", args=[conn_id])).data
        }

    def rows(self, conn_id, table):
        return self.client.get(reverse("connected-database-table-rows", args=[conn_id, table]))


@unittest.skipUnless(MYSQL, "set IF_TEST_MYSQL to a real MySQL server")
class MySQLConnectedDatabaseTests(_EngineBase):
    engine = "mysql"
    server = MYSQL

    def test_create_uses_port_3306_reads_the_schema_and_rows_and_quotes_odd_names(self):
        made = self.create(port=None)
        self.assertEqual(made.status_code, status.HTTP_201_CREATED, made.data)
        self.assertEqual((made.data["port"], made.data["status"]), (3306, "connected"))
        schema = self.schema(made.data["id"])
        self.assertIn("parts", schema)
        self.assertIn("odd`name", schema)
        self.assertEqual([c["name"] for c in schema["parts"]["columns"]][:2], ["id", "name"])
        parts = self.rows(made.data["id"], "parts")
        self.assertEqual(parts.status_code, 200, parts.data)
        self.assertEqual(parts.data["count"], 3)
        brake = next(r for r in parts.data["results"] if r["id"] == 1)
        self.assertEqual((brake["name"], brake["photo"]), ("Brake pad", "<5 bytes>"))
        odd = self.rows(made.data["id"], "odd`name")
        self.assertEqual(odd.data["results"], [{"x": 42}])
        page = self.client.get(
            reverse("connected-database-table-rows", args=[made.data["id"], "parts"]),
            {"limit": 1, "offset": 1},
        )
        self.assertEqual((page.data["count"], len(page.data["results"])), (3, 1))

    def test_a_table_not_in_the_live_schema_and_a_wrong_password_are_refused(self):
        made = self.create()
        self.assertEqual(
            self.rows(made.data["id"], "parts; DROP TABLE parts").status_code, status.HTTP_400_BAD_REQUEST
        )
        self.assertEqual(self.create(password="definitely-wrong").status_code, status.HTTP_400_BAD_REQUEST)

    def test_require_needs_tls_and_verify_full_needs_a_trusted_certificate(self):
        self.assertEqual(self.create(sslmode="require").data["status"], "connected")
        # The test server's certificate is self-signed: verify-full must not pass.
        self.assertEqual(self.create(sslmode="verify-full").status_code, status.HTTP_400_BAD_REQUEST)

    def test_the_session_is_read_only_even_for_a_user_who_could_write(self):
        admin_user, admin_password = os.environ["IF_TEST_MYSQL_ADMIN"].split(":", 1)
        params = ConnectionParams(
            host=MYSQL["host"],
            port=MYSQL["port"],
            database=MYSQL["database_name"],
            username=admin_user,
            password=admin_password,
            sslmode="prefer",
        )
        conn = MySQLConnector()._connect(params)
        try:
            with conn.cursor() as cur, self.assertRaises(Exception) as caught:
                cur.execute("INSERT INTO parts (id, name) VALUES (99, 'should not be written')")
            self.assertIn("READ ONLY", str(caught.exception).upper())
        finally:
            conn.close()


@unittest.skipUnless(MSSQL, "set IF_TEST_MSSQL to a real SQL Server")
class SQLServerConnectedDatabaseTests(_EngineBase):
    engine = "sqlserver"
    server = MSSQL

    def test_create_uses_port_1433_reads_the_schema_and_rows_and_quotes_odd_names(self):
        made = self.create(port=None)
        self.assertEqual(made.status_code, status.HTTP_201_CREATED, made.data)
        self.assertEqual((made.data["port"], made.data["status"]), (1433, "connected"))
        schema = self.schema(made.data["id"])
        self.assertIn("parts", schema)
        self.assertIn("odd]name", schema)
        parts = self.rows(made.data["id"], "parts")
        self.assertEqual(parts.status_code, 200, parts.data)
        self.assertEqual(parts.data["count"], 3)
        brake = next(r for r in parts.data["results"] if r["id"] == 1)
        self.assertEqual((brake["name"], brake["photo"]), ("Brake pad", "<5 bytes>"))
        self.assertEqual(self.rows(made.data["id"], "odd]name").data["results"], [{"x": 42}])
        page = self.client.get(
            reverse("connected-database-table-rows", args=[made.data["id"], "parts"]),
            {"limit": 2, "offset": 2},
        )
        self.assertEqual((page.data["count"], len(page.data["results"])), (3, 1))

    def test_encryption_required_works_and_verify_full_is_refused_up_front(self):
        self.assertEqual(self.create(sslmode="require").data["status"], "connected")
        refused = self.create(sslmode="verify-full")
        self.assertEqual(refused.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("sslmode", str(refused.data))

    def test_a_wrong_password_is_refused(self):
        self.assertEqual(self.create(password="definitely-wrong").status_code, status.HTTP_400_BAD_REQUEST)


class ConnectorRulesWithoutAServerTests(unittest.TestCase):
    def test_sql_server_never_attempts_verify_full(self):
        from databases.connectors import SQLServerConnector

        params = ConnectionParams(
            host="127.0.0.1", port=1433, database="x", username="u", password="p", sslmode="verify-full"
        )
        with self.assertRaises(ConnectionFailed):
            SQLServerConnector()._connect(params)

    def test_identifiers_are_quoted_by_each_engines_rules(self):
        from databases.connectors import _mysql_identifier, _sqlserver_identifier

        self.assertEqual(_mysql_identifier("a`b"), "`a``b`")
        self.assertEqual(_sqlserver_identifier("a]b"), "[a]]b]")
