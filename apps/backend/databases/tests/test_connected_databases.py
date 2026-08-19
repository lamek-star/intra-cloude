"""
Phase 8 (ADR-0009): connected-mode PostgreSQL integration tests. These
run against a genuinely real, independent psycopg connection to the
same live "tenant" PostgreSQL server Django's own ORM is already using
for this test run — not a mock — proving the connector's own
connect/introspect/query round-trip works over the real network path
inside the Docker test container. A dedicated `public` schema table is
created via a raw cursor as the "external" fixture data, since
TenantDatabase-owned tables all live in per-org `db_<uuid>` schemas the
connector deliberately never touches (connected mode is not platform-
native storage).

Uses APITransactionTestCase, not APITestCase: the connector opens its
own independent physical connection (by design — it's proxying to an
"external" system, not reusing Django's ORM connection), and a separate
connection can never see another transaction's uncommitted rows. Under
the default TestCase, Django wraps each test in an outer transaction
that's rolled back, not committed, so the fixture table/rows created via
`connections["tenant"].cursor()` would be invisible to the connector's
own connection — confirmed by actually running this suite: schema
introspection and row browsing both failed to find fixture data before
switching to APITransactionTestCase, which commits for real.
"""

import uuid

from django.db import connections
from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITransactionTestCase

from accounts.models import User
from databases.connectors import UnsafeHost, assert_host_is_safe
from databases.crypto import decrypt_credential
from databases.models import ConnectedDatabase
from organizations.models import Membership
from permissions.management.commands.seed_permissions import Command as SeedPermissionsCommand


class ConnectedDatabaseTestBase(APITransactionTestCase):
    databases = {"default", "tenant"}

    def setUp(self):
        SeedPermissionsCommand().handle()
        self.admin = User.objects.create_user(email="conn-admin@example.com", password="x")
        self.client.force_login(self.admin)

        org = self.client.post(reverse("organization-list-create"), {"name": "Acme"})
        self.org_id = org.data["id"]
        ws = self.client.post(reverse("workspace-list-create", args=[self.org_id]), {"name": "WS"})
        proj = self.client.post(reverse("project-list-create", args=[ws.data["id"]]), {"name": "Proj"})
        self.project_id = proj.data["id"]

        tenant_settings = connections["tenant"].settings_dict
        self.real_host = tenant_settings["HOST"] or "localhost"
        self.real_port = int(tenant_settings["PORT"] or 5432)
        self.real_database = tenant_settings["NAME"]
        self.real_user = tenant_settings["USER"]
        self.real_password = tenant_settings["PASSWORD"]

        self.table_name = f"conn_fixture_{uuid.uuid4().hex[:8]}"
        with connections["tenant"].cursor() as cursor:
            cursor.execute(f"CREATE TABLE public.{self.table_name} (id integer, label text)")
            cursor.execute(f"INSERT INTO public.{self.table_name} (id, label) VALUES (1, 'a'), (2, 'b')")

    def tearDown(self):
        # APITransactionTestCase's flush doesn't know about a table
        # created via raw SQL outside Django's migration state — drop it
        # explicitly so repeated runs don't leak tables into the "tenant"
        # database.
        with connections["tenant"].cursor() as cursor:
            cursor.execute(f"DROP TABLE IF EXISTS public.{self.table_name}")
        super().tearDown()

    def _payload(self, **overrides):
        payload = {
            "name": "External Warehouse",
            "engine": "postgresql",
            "host": self.real_host,
            "port": self.real_port,
            "database_name": self.real_database,
            "username": self.real_user,
            "password": self.real_password,
            "sslmode": "prefer",
        }
        payload.update(overrides)
        return payload


class ConnectionCreationTests(ConnectedDatabaseTestBase):
    def test_create_tests_connection_and_encrypts_password_at_rest(self):
        resp = self.client.post(
            reverse("connected-database-list-create", args=[self.project_id]), self._payload(), format="json"
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data["status"], ConnectedDatabase.Status.CONNECTED)
        self.assertNotIn("password", resp.data)
        self.assertNotIn("encrypted_password", resp.data)

        stored = ConnectedDatabase.objects.get(id=resp.data["id"])
        raw_bytes = bytes(stored.encrypted_password)
        self.assertNotIn(self.real_password.encode(), raw_bytes)
        self.assertEqual(decrypt_credential(raw_bytes), self.real_password)

    def test_bad_credentials_rejected_and_nothing_persisted(self):
        before = ConnectedDatabase.objects.count()
        resp = self.client.post(
            reverse("connected-database-list-create", args=[self.project_id]),
            self._payload(password="definitely-wrong-password"),
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(ConnectedDatabase.objects.count(), before)
        # The sanitized error never echoes the host/credential detail back.
        self.assertNotIn(self.real_host, resp.data["detail"])

    def test_member_without_connection_manage_is_forbidden(self):
        member = User.objects.create_user(email="conn-plain@example.com", password="x")
        Membership.objects.create(user=member, organization_id=self.org_id, status=Membership.Status.ACTIVE)
        self.client.force_login(member)

        resp = self.client.post(
            reverse("connected-database-list-create", args=[self.project_id]), self._payload(), format="json"
        )
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)


class ConnectionLifecycleTests(ConnectedDatabaseTestBase):
    def setUp(self):
        super().setUp()
        created = self.client.post(
            reverse("connected-database-list-create", args=[self.project_id]), self._payload(), format="json"
        )
        self.connected_database_id = created.data["id"]

    def test_list_and_detail_never_expose_credentials(self):
        listing = self.client.get(reverse("connected-database-list-create", args=[self.project_id]))
        self.assertEqual(listing.status_code, status.HTTP_200_OK)
        self.assertNotIn("password", listing.data[0])
        self.assertNotIn("encrypted_password", listing.data[0])

        detail = self.client.get(reverse("connected-database-detail", args=[self.connected_database_id]))
        self.assertEqual(detail.status_code, status.HTTP_200_OK)
        self.assertNotIn("password", detail.data)

    def test_schema_introspection_returns_real_table_and_columns(self):
        resp = self.client.get(reverse("connected-database-schema", args=[self.connected_database_id]))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        table = next((t for t in resp.data if t["name"] == self.table_name), None)
        self.assertIsNotNone(table)
        column_names = {c["name"] for c in table["columns"]}
        self.assertEqual(column_names, {"id", "label"})

    def test_row_browsing_returns_real_rows_over_an_independent_connection(self):
        resp = self.client.get(
            reverse("connected-database-table-rows", args=[self.connected_database_id, self.table_name])
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["count"], 2)
        labels = {row["label"] for row in resp.data["results"]}
        self.assertEqual(labels, {"a", "b"})

    def test_row_browsing_rejects_a_table_name_absent_from_the_live_schema(self):
        resp = self.client.get(
            reverse("connected-database-table-rows", args=[self.connected_database_id, "not_a_real_table"])
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_retest_updates_status_and_timestamp(self):
        resp = self.client.post(reverse("connected-database-test", args=[self.connected_database_id]))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["status"], ConnectedDatabase.Status.CONNECTED)
        self.assertIsNotNone(resp.data["last_tested_at"])

    def test_retest_against_now_unreachable_host_flips_status_without_leaking_password(self):
        connected_database = ConnectedDatabase.objects.get(id=self.connected_database_id)
        connected_database.host = "192.0.2.1"  # TEST-NET-1 (RFC 5737) — always unreachable
        connected_database.save(update_fields=["host"])

        resp = self.client.post(reverse("connected-database-test", args=[self.connected_database_id]))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["status"], ConnectedDatabase.Status.UNREACHABLE)
        self.assertNotIn(self.real_password, resp.data["last_test_error"])

    def test_delete_removes_the_connection(self):
        resp = self.client.delete(reverse("connected-database-detail", args=[self.connected_database_id]))
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(ConnectedDatabase.objects.filter(id=self.connected_database_id).exists())


class SSRFGuardTests(ConnectedDatabaseTestBase):
    """Section 30 of the master prompt: the connected-database host field
    must not let the backend be used to probe internal infrastructure.
    Link-local (cloud metadata endpoints like 169.254.169.254) is always
    blocked; RFC1918 private ranges and loopback are allowed by default
    (this is a local-first product — a customer's own on-prem PostgreSQL,
    or in this dev/CI setup the tenant DB itself, legitimately lives
    there) but can be locked down via CONNECTED_DATABASE_BLOCK_PRIVATE_NETWORKS
    for a hosted/multi-tenant deployment."""

    def test_link_local_metadata_address_is_always_rejected_at_create_time(self):
        resp = self.client.post(
            reverse("connected-database-list-create", args=[self.project_id]),
            self._payload(host="169.254.169.254"),
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(ConnectedDatabase.objects.filter(host="169.254.169.254").exists())

    def test_link_local_is_rejected_at_connect_time_too_not_only_creation(self):
        with self.assertRaises(UnsafeHost):
            assert_host_is_safe("169.254.169.254")

    def test_private_network_host_allowed_by_default(self):
        # The real tenant DB host in this environment is itself on a
        # private network (or localhost) — proving the default posture
        # doesn't block the product's own primary use case.
        assert_host_is_safe(self.real_host)

    @override_settings(CONNECTED_DATABASE_BLOCK_PRIVATE_NETWORKS=True)
    def test_private_network_host_rejected_when_stricter_mode_enabled(self):
        with self.assertRaises(UnsafeHost):
            assert_host_is_safe("10.0.0.5")

    @override_settings(CONNECTED_DATABASE_BLOCK_PRIVATE_NETWORKS=True)
    def test_loopback_rejected_when_stricter_mode_enabled(self):
        with self.assertRaises(UnsafeHost):
            assert_host_is_safe("127.0.0.1")

    def test_unresolvable_host_is_rejected_not_left_to_the_driver(self):
        with self.assertRaises(UnsafeHost):
            assert_host_is_safe("this-host-does-not-exist.invalid")
