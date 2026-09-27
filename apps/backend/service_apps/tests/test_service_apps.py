"""Service applications (ADR-0018): registry, provisioning, identity, isolation, internal API."""

import uuid

import psycopg
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connections
from django.test import override_settings
from django.urls import reverse
from psycopg import sql
from rest_framework.test import APIClient, APITestCase, APITransactionTestCase

from accounts.models import User
from audit.models import AuditEvent
from organizations.models import Membership
from permissions.management.commands.seed_permissions import Command as SeedPermissionsCommand
from permissions.services import assign_role, grant_resource_permission
from service_apps import provisioning
from service_apps.models import ServiceApp, ServiceAppSession

TOKEN = "t" * 20 + uuid.uuid4().hex  # 52 characters
DEPLOYMENTS = {
    "spare-parts": {
        "app_type": "spare_parts",
        "token": TOKEN,
        "db_role": "svc_test_spare_parts",
        "db_password": "test-password-" + uuid.uuid4().hex,
        "internal_url": "http://127.0.0.1:9",  # nothing listens: the probe reports "stopped"
        "launch_path": "/apps/spare-parts/",
    }
}
INTERNAL = "/api/v1/internal/service-apps"


def tenant_superuser_connect():
    db = connections["tenant"].settings_dict
    return psycopg.connect(
        host=db["HOST"] or "localhost",
        port=int(db["PORT"] or 5432),
        dbname=db["NAME"],
        user=db["USER"],
        password=db["PASSWORD"],
        autocommit=True,
    )


class ServiceAppHelpers:
    def setUp(self):
        SeedPermissionsCommand().handle()
        self.owner = User.objects.create_user(email="owner@example.test", password="Pw-owner-12345")
        self.client.force_login(self.owner)
        org = self.client.post(reverse("organization-list-create"), {"name": "Harbour Motors"})
        self.org_id = org.data["id"]
        self.service = APIClient()
        self.service.credentials(HTTP_X_INTRAFORGE_SERVICE_TOKEN=TOKEN)

    def tearDown(self):
        for app in ServiceApp.objects.all():
            provisioning.drop_schema(app.schema_name)

    def install(self, name="Harbour Motors Spare Parts", **extra):
        return self.client.post(
            "/api/v1/service-apps/",
            {"deployment": "spare-parts", "organization": self.org_id, "display_name": name, **extra},
            format="json",
        )

    def member(self, email, role_slug=None, org_id=None, status=Membership.Status.ACTIVE):
        user = User.objects.create_user(email=email, password="Pw-member-12345")
        org_id = org_id or self.org_id
        Membership.objects.create(user=user, organization_id=org_id, status=status)
        if role_slug:
            assign_role(
                user=user, role_slug=role_slug, organization=Membership.objects.get(user=user).organization
            )
        return user

    def open_as(self, user, app_id):
        client = APIClient()
        client.force_login(user)
        resp = client.post(f"/api/v1/service-apps/{app_id}/launch/")
        return client, resp

    def introspect(self, token):
        return self.service.post(f"{INTERNAL}/sessions/introspect/", {"token": token}, format="json")


@override_settings(SERVICE_APP_DEPLOYMENTS=DEPLOYMENTS)
class ServiceAppTestBase(ServiceAppHelpers, APITestCase):
    databases = {"default", "tenant"}


@override_settings(SERVICE_APP_DEPLOYMENTS=DEPLOYMENTS)
class CommittedServiceAppTestBase(ServiceAppHelpers, APITransactionTestCase):
    """For tests where another process (pg_dump) must see the data: rows are committed, then flushed."""

    databases = {"default", "tenant"}


class InstallTests(ServiceAppTestBase):
    def test_install_provisions_project_bucket_schema_and_least_privilege_role(self):
        resp = self.install(config={"currency": "aed", "defaultTaxBp": 500})
        self.assertEqual(resp.status_code, 201, resp.data)
        app = ServiceApp.objects.get(pk=resp.data["id"])
        self.assertEqual(app.display_name, "Harbour Motors Spare Parts")
        self.assertEqual(app.config["shopName"], "Harbour Motors Spare Parts")
        self.assertEqual(app.config["currency"], "AED")
        self.assertEqual(app.project.workspace.name, "Applications")
        self.assertEqual(app.bucket.project, app.project)
        self.assertTrue(provisioning.schema_exists(app.schema_name))
        with tenant_superuser_connect() as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT nspowner::regrole::text FROM pg_namespace WHERE nspname = %s", [app.schema_name]
            )
            self.assertEqual(cur.fetchone()[0], "svc_test_spare_parts")
            cur.execute(
                "SELECT rolsuper, rolcreatedb, rolcreaterole FROM pg_roles WHERE rolname = %s",
                ["svc_test_spare_parts"],
            )
            self.assertEqual(cur.fetchone(), (False, False, False))
        actions = set(AuditEvent.objects.filter(organization_id=self.org_id).values_list("action", flat=True))
        self.assertTrue({"service_app.install", "project.create", "storage.bucket.create"} <= actions)

    def test_the_role_can_use_its_schema_but_not_another_organizations(self):
        app = ServiceApp.objects.get(pk=self.install().data["id"])
        with tenant_superuser_connect() as conn, conn.cursor() as cur:
            cur.execute("CREATE SCHEMA IF NOT EXISTS other_org_data")
            cur.execute("CREATE TABLE IF NOT EXISTS other_org_data.secrets (v text)")
        db = connections["tenant"].settings_dict
        try:
            with (
                psycopg.connect(
                    host=db["HOST"] or "localhost",
                    port=int(db["PORT"] or 5432),
                    dbname=db["NAME"],
                    user="svc_test_spare_parts",
                    password=DEPLOYMENTS["spare-parts"]["db_password"],
                    autocommit=True,
                ) as conn,
                conn.cursor() as cur,
            ):
                cur.execute(sql.SQL("CREATE TABLE {}.t (id int)").format(sql.Identifier(app.schema_name)))
                cur.execute(sql.SQL("INSERT INTO {}.t VALUES (1)").format(sql.Identifier(app.schema_name)))
                with self.assertRaises(psycopg.errors.InsufficientPrivilege):
                    cur.execute("SELECT * FROM other_org_data.secrets")
                with self.assertRaises(psycopg.errors.InsufficientPrivilege):
                    cur.execute("CREATE SCHEMA sneaky")
        finally:
            with tenant_superuser_connect() as conn, conn.cursor() as cur:
                cur.execute("DROP SCHEMA IF EXISTS other_org_data CASCADE")

    def test_install_needs_app_instance_manage(self):
        viewer = self.member("viewer@example.test", "viewer")
        client = APIClient()
        client.force_login(viewer)
        resp = client.post(
            "/api/v1/service-apps/",
            {"deployment": "spare-parts", "organization": self.org_id, "display_name": "X"},
            format="json",
        )
        self.assertEqual(resp.status_code, 403)
        self.assertFalse(ServiceApp.objects.exists())

    def test_a_deployment_holds_one_instance_and_unknown_settings_are_refused(self):
        self.assertEqual(self.install().status_code, 201)
        self.assertEqual(self.install(name="Second").status_code, 409)
        bad = self.client.patch(
            f"/api/v1/service-apps/{ServiceApp.objects.get().id}/",
            {"config": {"secretKey": "x"}},
            format="json",
        )
        self.assertEqual(bad.status_code, 400)

    @override_settings(SERVICE_APP_DEPLOYMENTS={})
    def test_nothing_is_installable_without_a_configured_deployment(self):
        self.assertEqual(self.client.get("/api/v1/service-apps/").data["available"], [])
        self.assertEqual(self.install().status_code, 400)


class VisibilityAndIsolationTests(ServiceAppTestBase):
    def setUp(self):
        super().setUp()
        self.app_id = self.install().data["id"]

    def test_listing_shows_the_app_with_live_health_and_flags(self):
        data = self.client.get("/api/v1/service-apps/").data
        item = data["results"][0]
        self.assertEqual(item["display_name"], "Harbour Motors Spare Parts")
        self.assertEqual(item["name"], "Spare Parts")
        self.assertEqual(item["health"]["state"], "stopped")
        self.assertTrue(item["can_open"] and item["can_configure"] and item["can_manage"])
        self.assertEqual(item["launch"]["path"], "/apps/spare-parts/")

    def test_other_organizations_cannot_see_open_or_change_it(self):
        outsider = User.objects.create_user(email="outsider@example.test", password="Pw-outsider-1")
        client = APIClient()
        client.force_login(outsider)
        client.post(reverse("organization-list-create"), {"name": "Other shop"})
        self.assertEqual(client.get("/api/v1/service-apps/").data["results"], [])
        for method, path in [
            ("get", f"/api/v1/service-apps/{self.app_id}/"),
            ("patch", f"/api/v1/service-apps/{self.app_id}/"),
            ("post", f"/api/v1/service-apps/{self.app_id}/launch/"),
            ("delete", f"/api/v1/service-apps/{self.app_id}/"),
            ("get", f"/api/v1/service-apps/{self.app_id}/removal-preview/"),
        ]:
            self.assertEqual(getattr(client, method)(path, {}, format="json").status_code, 404, path)

    def test_a_member_without_spare_parts_capabilities_neither_sees_nor_opens_it(self):
        plain = self.member("plain@example.test", "viewer")
        client, resp = self.open_as(plain, self.app_id)
        self.assertEqual(resp.status_code, 404)
        self.assertEqual(client.get("/api/v1/service-apps/").data["results"], [])

    def test_bearer_credentials_cannot_open_or_install(self):
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION="Bearer not-a-session")
        self.assertIn(client.get("/api/v1/service-apps/").status_code, (401, 403))


class SessionTests(ServiceAppTestBase):
    def setUp(self):
        super().setUp()
        self.app_id = self.install().data["id"]

    def test_open_sets_a_path_scoped_strict_httponly_cookie_and_nothing_in_the_url(self):
        resp = self.client.post(f"/api/v1/service-apps/{self.app_id}/launch/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["url"], "/apps/spare-parts/")
        cookie = resp.cookies["ifapp_spare_parts"]
        self.assertTrue(cookie["httponly"])
        self.assertEqual(cookie["samesite"], "Strict")
        self.assertEqual(cookie["path"], "/apps/spare-parts/")
        stored = ServiceAppSession.objects.get()
        self.assertNotEqual(stored.token_hash, cookie.value)

    def test_introspection_maps_roles_to_exact_capabilities(self):
        sales = self.member("sales@example.test", "spare-parts-sales")
        _, resp = self.open_as(sales, self.app_id)
        data = self.introspect(resp.cookies["ifapp_spare_parts"].value).data
        self.assertTrue(data["active"])
        self.assertEqual(data["user"]["email"], "sales@example.test")
        self.assertIn("spareparts.sales.manage", data["capabilities"])
        self.assertNotIn("spareparts.cost.read", data["capabilities"])
        self.assertNotIn("spareparts.inventory.manage", data["capabilities"])
        self.assertEqual(len(data["csrfToken"]), 64)

    def test_a_grant_on_this_one_instance_is_enough(self):
        staff = self.member("staff@example.test")
        for cap in ("spareparts.view", "spareparts.catalogue.read"):
            grant_resource_permission(
                user=staff,
                permission_code=cap,
                organization_id=self.org_id,
                resource_type="service_app",
                resource_id=self.app_id,
                granted_by=self.owner,
            )
        _, resp = self.open_as(staff, self.app_id)
        self.assertEqual(resp.status_code, 200)
        data = self.introspect(resp.cookies["ifapp_spare_parts"].value).data
        self.assertEqual(data["capabilities"], ["spareparts.catalogue.read", "spareparts.view"])

    def test_logout_disable_suspension_and_password_change_end_the_app_session(self):
        user = self.member("inv@example.test", "spare-parts-inventory")
        client, resp = self.open_as(user, self.app_id)
        token = resp.cookies["ifapp_spare_parts"].value
        self.assertEqual(self.introspect(token).status_code, 200)
        client.post(reverse("auth-logout"))
        self.assertEqual(self.introspect(token).status_code, 401)

        # password change invalidates the IntraForge session hash
        client, resp = self.open_as(user, self.app_id)
        token = resp.cookies["ifapp_spare_parts"].value
        user.set_password("Pw-new-password-9")
        user.save()
        self.assertEqual(self.introspect(token).status_code, 401)

        # suspension of the membership
        user = self.member("inv2@example.test", "spare-parts-inventory")
        _, resp = self.open_as(user, self.app_id)
        token = resp.cookies["ifapp_spare_parts"].value
        Membership.objects.filter(user=user).update(status=Membership.Status.SUSPENDED)
        self.assertEqual(self.introspect(token).status_code, 401)

        # disabling the application
        _, resp = self.open_as(self.owner, self.app_id)
        token = resp.cookies["ifapp_spare_parts"].value
        self.client.patch(f"/api/v1/service-apps/{self.app_id}/", {"enabled": False}, format="json")
        self.assertEqual(self.introspect(token).status_code, 401)

    def test_revoke_and_garbage_tokens(self):
        _, resp = self.open_as(self.owner, self.app_id)
        token = resp.cookies["ifapp_spare_parts"].value
        self.service.post(f"{INTERNAL}/sessions/revoke/", {"token": token}, format="json")
        self.assertEqual(self.introspect(token).status_code, 401)
        for junk in ["", "x", "' OR 1=1 --", "a" * 5000]:
            self.assertEqual(self.introspect(junk).status_code, 401)


class InternalApiTests(ServiceAppTestBase):
    def setUp(self):
        super().setUp()
        self.app_id = self.install().data["id"]

    def test_internal_endpoints_need_the_service_token(self):
        anonymous = APIClient()
        self.assertIn(anonymous.get(f"{INTERNAL}/self/").status_code, (401, 403))
        wrong = APIClient()
        wrong.credentials(HTTP_X_INTRAFORGE_SERVICE_TOKEN="w" * 52)
        self.assertEqual(wrong.get(f"{INTERNAL}/self/").status_code, 401)
        # a signed-in human is not a service
        self.assertIn(self.client.get(f"{INTERNAL}/self/").status_code, (401, 403))

    def test_self_describes_the_instance_without_secrets(self):
        data = self.service.get(f"{INTERNAL}/self/").data
        self.assertTrue(data["installed"])
        self.assertEqual(data["database"]["role"], "svc_test_spare_parts")
        self.assertNotIn("password", str(data).lower())
        self.assertEqual(data["config"]["shopName"], "Harbour Motors Spare Parts")

    def test_audit_relay_is_idempotent_prefixed_and_maps_only_members(self):
        outsider = User.objects.create_user(email="x@example.test", password="Pw-x-12345678")
        event = {
            "id": str(uuid.uuid4()),
            "at": "2026-09-27T10:00:00.000Z",
            "actorId": str(self.owner.id),
            "actorLabel": "Owner",
            "action": "stock.adjust",
            "entityType": "product",
            "entityId": "p1",
            "summary": "Adjusted",
            "metadata": {"quantity": 3},
        }
        foreign = {**event, "id": str(uuid.uuid4()), "actorId": str(outsider.id)}
        for _ in range(2):
            resp = self.service.post(f"{INTERNAL}/audit-events/", {"events": [event, foreign]}, format="json")
            self.assertEqual(resp.status_code, 200)
        rows = AuditEvent.objects.filter(action="spareparts.stock.adjust")
        self.assertEqual(rows.count(), 2)
        self.assertEqual({r.actor_id for r in rows}, {self.owner.id, None})
        self.assertEqual(rows.first().context["application"]["name"], "Harbour Motors Spare Parts")
        bad = self.service.post(
            f"{INTERNAL}/audit-events/", {"events": [{**event, "id": "../x"}]}, format="json"
        )
        self.assertEqual(bad.status_code, 400)

    def test_settings_changed_inside_the_app_are_rechecked_for_the_acting_user(self):
        viewer = self.member("v@example.test", "spare-parts-viewer")
        refused = self.service.patch(
            f"{INTERNAL}/config/", {"actorId": str(viewer.id), "patch": {"phone": "123"}}, format="json"
        )
        self.assertEqual(refused.status_code, 403)
        ok = self.service.patch(
            f"{INTERNAL}/config/",
            {"actorId": str(self.owner.id), "patch": {"phone": "04 123"}},
            format="json",
        )
        self.assertEqual(ok.status_code, 200)
        self.assertEqual(ok.data["phone"], "04 123")

    def test_files_live_in_the_instance_bucket_and_other_files_are_unreachable(self):
        png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
        resp = self.service.post(
            f"{INTERNAL}/files/",
            {
                "file": SimpleUploadedFile("photo.png", png),
                "kind": "PRODUCT_IMAGE",
                "actorId": str(self.owner.id),
            },
            format="multipart",
        )
        self.assertEqual(resp.status_code, 201, resp.data)
        app = ServiceApp.objects.get()
        self.assertTrue(app.bucket.files.filter(pk=resp.data["id"]).exists())
        fetched = self.service.get(f"{INTERNAL}/files/{resp.data['id']}/")
        self.assertEqual(fetched.status_code, 200)
        self.assertEqual(b"".join(fetched.streaming_content), png)
        self.assertEqual(fetched["X-Content-SHA256"], resp.data["sha256"])
        # a file in some other bucket of the same organization is not reachable by id
        ws = self.client.post(reverse("workspace-list-create", args=[self.org_id]), {"name": "W2"})
        proj = self.client.post(reverse("project-list-create", args=[ws.data["id"]]), {"name": "P2"})
        bucket = self.client.post(reverse("bucket-list-create", args=[proj.data["id"]]), {"name": "private"})
        other = self.client.post(
            reverse("file-list-create", args=[bucket.data["id"]]),
            {"file": SimpleUploadedFile("secret.txt", b"secret")},
        )
        self.assertEqual(self.service.get(f"{INTERNAL}/files/{other.data['id']}/").status_code, 404)
        empty = self.service.post(
            f"{INTERNAL}/files/",
            {"file": SimpleUploadedFile("e.png", b""), "kind": "PRODUCT_IMAGE"},
            format="multipart",
        )
        self.assertEqual(empty.status_code, 400)

    def test_heartbeat_records_the_version(self):
        self.service.post(f"{INTERNAL}/heartbeat/", {"version": "1.2.3"}, format="json")
        app = ServiceApp.objects.get()
        self.assertEqual(app.reported_version, "1.2.3")
        self.assertEqual(
            self.client.get("/api/v1/service-apps/").data["results"][0]["health"]["state"], "degraded"
        )


class RemovalTests(ServiceAppTestBase):
    def setUp(self):
        super().setUp()
        self.app_id = self.install().data["id"]

    def test_remove_keeping_data_hides_it_and_reinstate_brings_it_back(self):
        wrong = self.client.delete(
            f"/api/v1/service-apps/{self.app_id}/", {"confirm_name": "nope"}, format="json"
        )
        self.assertEqual(wrong.status_code, 400)
        resp = self.client.delete(
            f"/api/v1/service-apps/{self.app_id}/",
            {"confirm_name": "Harbour Motors Spare Parts"},
            format="json",
        )
        self.assertEqual(resp.data, {"removed": True, "data_deleted": False})
        app = ServiceApp.objects.get()
        self.assertIsNotNone(app.removed_at)
        self.assertTrue(provisioning.schema_exists(app.schema_name))
        self.assertEqual(self.service.get(f"{INTERNAL}/self/").data["installed"], False)
        back = self.client.post(f"/api/v1/service-apps/{self.app_id}/reinstate/")
        self.assertEqual(back.status_code, 200)
        self.assertTrue(self.service.get(f"{INTERNAL}/self/").data["installed"])

    def test_removal_is_limited_to_managers(self):
        manager = self.member("m@example.test", "spare-parts-manager")
        client = APIClient()
        client.force_login(manager)
        resp = client.delete(
            f"/api/v1/service-apps/{self.app_id}/",
            {"confirm_name": "Harbour Motors Spare Parts"},
            format="json",
        )
        self.assertEqual(resp.status_code, 403)

    def test_deleting_data_refuses_when_the_safety_backup_fails(self):
        from unittest import mock

        from system.models import BackupRecord

        failed = mock.Mock(status=BackupRecord.Status.FAILED, id="x")
        with mock.patch("system.backups.run_backup", return_value=failed):
            resp = self.client.delete(
                f"/api/v1/service-apps/{self.app_id}/",
                {"confirm_name": "Harbour Motors Spare Parts", "delete_data": True},
                format="json",
            )
        self.assertEqual(resp.status_code, 400)
        app = ServiceApp.objects.get()
        self.assertTrue(provisioning.schema_exists(app.schema_name))
        self.assertIsNone(app.removed_at)

    def test_deleting_data_takes_a_real_backup_first_then_frees_the_slot(self):
        from system.models import BackupRecord

        schema = ServiceApp.objects.get().schema_name
        before = BackupRecord.objects.count()
        resp = self.client.delete(
            f"/api/v1/service-apps/{self.app_id}/",
            {"confirm_name": "Harbour Motors Spare Parts", "delete_data": True},
            format="json",
        )
        self.assertEqual(resp.status_code, 200, resp.data)
        self.assertTrue(resp.data["data_deleted"])
        self.assertEqual(BackupRecord.objects.count(), before + 2)
        self.assertFalse(provisioning.schema_exists(schema))
        self.assertFalse(ServiceApp.objects.exists())
        self.assertEqual(self.install(name="Fresh start").status_code, 201)
        event = AuditEvent.objects.filter(action="service_app.delete_data").get()
        self.assertEqual(set(event.context["backups"]), {"tenant_db", "object_storage"})


class ControlCenterSupportTests(CommittedServiceAppTestBase):
    """The commands the Windows Control Center calls (it has no IntraForge sign-in of its own)."""

    def setUp(self):
        super().setUp()
        self.app_id = self.install().data["id"]

    def test_list_service_apps_shows_names_and_open_paths_without_secrets(self):
        import json as _json
        from io import StringIO

        from django.core.management import call_command

        out = StringIO()
        call_command("list_service_apps", "--json", stdout=out)
        data = _json.loads(out.getvalue())
        self.assertEqual(data["installed"][0]["display_name"], "Harbour Motors Spare Parts")
        self.assertEqual(data["installed"][0]["open_path"], f"/service-apps/{self.app_id}/open")
        self.assertEqual(data["available"], [])
        self.assertNotIn(DEPLOYMENTS["spare-parts"]["db_password"], out.getvalue())
        self.assertNotIn(TOKEN, out.getvalue())

    def test_a_backup_set_is_inspected_before_restoring(self):
        import os
        import tarfile
        from unittest import mock

        from system import backup_inspection
        from system.backups import run_backup
        from system.models import BackupRecord

        app = ServiceApp.objects.get()
        with tenant_superuser_connect() as conn, conn.cursor() as cur:
            cur.execute(sql.SQL("CREATE TABLE {}.products (id text)").format(sql.Identifier(app.schema_name)))
            cur.execute(
                sql.SQL("INSERT INTO {}.products VALUES ('a'), ('b')").format(sql.Identifier(app.schema_name))
            )
        self.service.post(
            f"{INTERNAL}/files/",
            {
                "file": SimpleUploadedFile("p.png", b"\x89PNG\r\n\x1a\n" + b"\x01" * 32),
                "kind": "PRODUCT_IMAGE",
            },
            format="multipart",
        )
        records = {k: run_backup(k) for k in ("control_db", "tenant_db", "object_storage")}
        for r in records.values():
            self.assertEqual(r.status, BackupRecord.Status.SUCCESS, r.error_message)
        paths = [records[k].file_path for k in ("control_db", "tenant_db", "object_storage")]

        report = backup_inspection.inspect_backup_set(*paths)
        self.assertTrue(report["ok"], report)
        self.assertTrue(report["compatible"])
        [inspected] = report["applications"]
        self.assertEqual(inspected["display_name"], "Harbour Motors Spare Parts")
        self.assertTrue(inspected["data_present"])
        self.assertEqual(inspected["counts"]["products"], 2)
        self.assertGreaterEqual(report["objects"]["verified"], 1)
        self.assertTrue(all(f["valid"] for f in report["files"].values()))

        # a backup from a newer program: refused
        loader_cls = backup_inspection.MigrationLoader

        class OlderProgram(loader_cls):
            def __init__(self, *a, **kw):
                super().__init__(*a, **kw)
                self.disk_migrations.pop(("service_apps", "0001_initial"), None)

        with mock.patch.object(backup_inspection, "MigrationLoader", OlderProgram):
            newer = backup_inspection.inspect_backup_set(*paths)
        self.assertFalse(newer["ok"])
        self.assertFalse(newer["compatible"])
        self.assertIn("NEWER", newer["errors"][0])

        # a damaged stored file: refused (only when unencrypted can it be edited in place)
        objects = records["object_storage"].file_path
        if not objects.endswith(".icb"):
            damaged = objects + ".damaged.tar"
            with tarfile.open(objects) as src, tarfile.open(damaged, "w") as dst:
                for member in src:
                    data = src.extractfile(member).read() if member.isfile() else None
                    if data is not None and member.name != "_manifest.json":
                        data = b"X" + data[1:]
                    dst.addfile(member, None if data is None else __import__("io").BytesIO(data))
            bad = backup_inspection.inspect_backup_set(paths[0], paths[1], damaged)
            self.assertFalse(bad["ok"])
            self.assertIn("checksum", " ".join(bad["errors"]))
            os.remove(damaged)
        # a missing file: refused
        self.assertFalse(backup_inspection.inspect_backup_set(paths[0], paths[1], "/nope")["ok"])

        # an encrypted file with one changed byte: refused with a reason, not a crash
        from django.test import override_settings

        from exports import container
        from system.backups import _DecryptedTempFile

        with _DecryptedTempFile(paths[1]) as plain, open(plain, "rb") as f:
            sealed = bytearray(container.write_container(f.read(), passphrase="k" * 32))
        sealed[len(sealed) // 2] ^= 1
        tampered = paths[1] + ".tampered.icb"
        with open(tampered, "wb") as f:
            f.write(sealed)
        try:
            with override_settings(BACKUP_ENCRYPTION_KEY="k" * 32):
                bad = backup_inspection.inspect_backup_set(paths[0], tampered, paths[2])
            self.assertFalse(bad["ok"])
            self.assertIn("business data backup cannot be read", " ".join(bad["errors"]))
        finally:
            os.remove(tampered)
