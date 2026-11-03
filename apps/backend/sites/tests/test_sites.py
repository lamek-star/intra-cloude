"""
Hosted websites (ADR-0019): the zip check, the version lifecycle against real object storage, the public
serving view's headers and path rules, and tenant isolation (IDOR) between organizations.
"""

import io
import stat
import zipfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import User
from audit.models import AuditEvent
from organizations.models import Membership
from permissions.management.commands.seed_permissions import Command as SeedPermissionsCommand
from permissions.services import assign_role
from sites.archive import SiteArchiveError, plan_archive
from sites.models import Site
from storage.backends import get_client

INDEX = b"<!doctype html><title>Shop</title><h1>Welcome</h1><script src=app.js></script>"


def make_zip(files: dict[str, bytes], *, symlink: str | None = None) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, data in files.items():
            archive.writestr(name, data)
        if symlink:
            info = zipfile.ZipInfo(symlink)
            info.external_attr = (stat.S_IFLNK | 0o777) << 16
            archive.writestr(info, "/etc/passwd")
    return buffer.getvalue()


def upload(files: dict[str, bytes], name="site.zip", **kwargs) -> SimpleUploadedFile:
    return SimpleUploadedFile(name, make_zip(files, **kwargs), content_type="application/zip")


class ArchiveCheckTests(APITestCase):
    def _plan(self, files, **kwargs):
        return plan_archive(io.BytesIO(make_zip(files, **kwargs)))[1]

    def test_a_plain_site_is_accepted_with_types_from_the_extension(self):
        plan = self._plan({"index.html": INDEX, "app.js": b"1", "img/logo.png": b"\x89PNG"})
        self.assertEqual([f.path for f in plan.files], ["app.js", "img/logo.png", "index.html"])
        self.assertEqual({f.path: f.content_type for f in plan.files}["img/logo.png"], "image/png")

    def test_one_top_folder_is_removed(self):
        plan = self._plan({"public_html/index.html": INDEX, "public_html/css/a.css": b"a{}"})
        self.assertEqual([f.path for f in plan.files], ["css/a.css", "index.html"])
        self.assertIn("public_html/", plan.notes[0])

    def test_hidden_and_system_files_are_left_out(self):
        plan = self._plan(
            {"index.html": INDEX, ".htaccess": b"x", "__MACOSX/._index.html": b"x", ".git/HEAD": b"x"}
        )
        self.assertEqual([f.path for f in plan.files], ["index.html"])
        self.assertIn("3 hidden", plan.notes[0])

    def test_refusals(self):
        cases = {
            "server code": ({"index.html": INDEX, "api.php": b"<?php"}, "server code (.php)"),
            "not a website file": ({"index.html": INDEX, "tool.zip": b"x"}, "not website files: .zip"),
            "traversal": ({"index.html": INDEX, "../evil.html": b"x"}, "not a safe file name"),
            "absolute": ({"index.html": INDEX, "/etc/x.html": b"x"}, "absolute path"),
            "drive letter": ({"index.html": INDEX, "C:/x.html": b"x"}, "absolute path"),
            "no index": ({"home.html": INDEX}, "no index.html"),
            "duplicate": ({"index.html": INDEX, "A.css": b"a", "a.css": b"b"}, "appears twice"),
        }
        for label, (files, message) in cases.items():
            with self.subTest(label), self.assertRaisesMessage(SiteArchiveError, message):
                self._plan(files)

    def test_symbolic_links_are_refused(self):
        with self.assertRaisesMessage(SiteArchiveError, "is a link"):
            self._plan({"index.html": INDEX}, symlink="passwd.txt")

    def test_not_a_zip(self):
        with self.assertRaisesMessage(SiteArchiveError, "not a zip"):
            plan_archive(io.BytesIO(b"hello"))

    @override_settings(SITES_MAX_RATIO=10)
    def test_a_zip_bomb_is_refused_from_its_declared_sizes(self):
        with self.assertRaisesMessage(SiteArchiveError, "unpacks to far more"):
            self._plan({"index.html": INDEX, "big.txt": b"0" * (4 * 1024 * 1024)})

    @override_settings(SITES_MAX_TOTAL_BYTES=1000)
    def test_the_total_unpacked_size_is_limited(self):
        with self.assertRaisesMessage(SiteArchiveError, "unpacks to more than"):
            self._plan({"index.html": INDEX, "a.txt": b"x" * 2000})

    @override_settings(SITES_MAX_FILES=2)
    def test_the_file_count_is_limited(self):
        with self.assertRaisesMessage(SiteArchiveError, "more than 2 files"):
            self._plan({"index.html": INDEX, "a.css": b"a", "b.css": b"b"})


class SiteTestBase(APITestCase):
    databases = {"default", "tenant"}

    def setUp(self):
        SeedPermissionsCommand().handle()
        self.admin = User.objects.create_user(email="site-admin@example.com", password="x")
        self.client.force_login(self.admin)
        self.org_id = self.client.post(reverse("organization-list-create"), {"name": "Shop"}).data["id"]

    def _create(self, slug="my-shop", files=None, **extra):
        return self.client.post(
            reverse("site-list-create", args=[self.org_id]),
            {
                "name": "My shop",
                "slug": slug,
                "file": upload(files or {"index.html": INDEX, "app.js": b"go()"}),
                **extra,
            },
            format="multipart",
        )

    def _member(self, email, role=None, org_id=None):
        user = User.objects.create_user(email=email, password="x")
        Membership.objects.create(
            user=user, organization_id=org_id or self.org_id, status=Membership.Status.ACTIVE
        )
        if role:
            from organizations.models import Organization

            assign_role(
                user=user, role_slug=role, organization=Organization.objects.get(id=org_id or self.org_id)
            )
        return user


class SiteLifecycleTests(SiteTestBase):
    def tearDown(self):
        # Leave no objects behind in the shared object storage.
        for site in Site.objects.all():
            for version in site.versions.all():
                for path in version.files:
                    get_client().delete(version.storage_prefix + path)

    def test_create_stores_the_files_and_serves_them(self):
        resp = self._create()
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.data)
        self.assertEqual(resp.data["path"], "/my-shop/")
        self.assertEqual(resp.data["active_version"]["number"], 1)
        self.assertEqual(resp.data["active_version"]["file_count"], 2)
        self.assertTrue(
            AuditEvent.objects.filter(action="site.created", organization_id=self.org_id).exists()
        )

        page = self.client.get("/_sites/my-shop/")
        self.assertEqual(page.status_code, 200)
        self.assertEqual(b"".join(page.streaming_content), INDEX)
        self.assertEqual(page["Content-Type"], "text/html; charset=utf-8")
        script = self.client.get("/_sites/my-shop/app.js")
        self.assertEqual(script["Content-Type"], "text/javascript; charset=utf-8")

    def test_every_response_is_sandboxed_and_sets_no_cookie(self):
        self._create()
        for url in ("/_sites/my-shop/", "/_sites/my-shop/missing.css", "/_sites/my-shop", "/_sites/"):
            with self.subTest(url):
                resp = self.client.get(url)
                self.assertIn("sandbox allow-scripts", resp["Content-Security-Policy"])
                self.assertNotIn("allow-same-origin", resp["Content-Security-Policy"])
                self.assertEqual(resp["X-Content-Type-Options"], "nosniff")
                self.assertEqual(resp.cookies, {})

    def test_paths_redirects_and_not_found(self):
        self._create(files={"index.html": INDEX, "about/index.html": b"about", "404.html": b"lost"})
        self.assertEqual(self.client.get("/_sites/my-shop")["Location"], "/my-shop/")
        self.assertEqual(self.client.get("/_sites/my-shop/about")["Location"], "/my-shop/about/")
        self.assertEqual(b"".join(self.client.get("/_sites/my-shop/about/").streaming_content), b"about")
        missing = self.client.get("/_sites/my-shop/nothing-here")
        self.assertEqual(missing.status_code, 404)
        self.assertEqual(b"".join(missing.streaming_content), b"lost")
        self.assertEqual(self.client.get("/_sites/my-shop/../other/").status_code, 404)
        self.assertEqual(self.client.get("/_sites/no-such-site/").status_code, 404)
        self.assertEqual(self.client.post("/_sites/my-shop/").status_code, 405)

    def test_single_page_app_fallback(self):
        resp = self._create(single_page_app=True)
        self.assertTrue(resp.data["single_page_app"])
        routed = self.client.get("/_sites/my-shop/products/42")
        self.assertEqual(routed.status_code, 200)
        self.assertEqual(b"".join(routed.streaming_content), INDEX)
        # A missing file (with an extension) is still missing.
        self.assertEqual(self.client.get("/_sites/my-shop/missing.js").status_code, 404)

    def test_etag_gives_not_modified(self):
        self._create()
        etag = self.client.get("/_sites/my-shop/")["ETag"]
        self.assertEqual(self.client.get("/_sites/my-shop/", HTTP_IF_NONE_MATCH=etag).status_code, 304)

    def test_versions_switch_back_and_delete(self):
        site_id = self._create().data["id"]
        v2 = self.client.post(
            reverse("site-version-list-create", args=[site_id]),
            {"file": upload({"index.html": b"version two"})},
            format="multipart",
        )
        self.assertEqual(v2.status_code, 201, v2.data)
        self.assertEqual(b"".join(self.client.get("/_sites/my-shop/").streaming_content), b"version two")

        detail = self.client.get(reverse("site-detail", args=[site_id])).data
        v1_id = [v["id"] for v in detail["versions"] if v["number"] == 1][0]
        # The version visitors see cannot be deleted.
        refused = self.client.delete(reverse("site-version-detail", args=[site_id, v2.data["id"]]))
        self.assertEqual(refused.status_code, 400)

        self.client.post(reverse("site-version-activate", args=[site_id, v1_id]))
        self.assertEqual(b"".join(self.client.get("/_sites/my-shop/").streaming_content), INDEX)
        self.assertEqual(
            self.client.delete(reverse("site-version-detail", args=[site_id, v2.data["id"]])).status_code, 204
        )
        keys = {key for key, _ in get_client().list_all_keys() if key.startswith(f"sites/{site_id}/")}
        self.assertEqual(len(keys), 2)  # version 1's two files only

    def test_offline_site_is_not_served_and_delete_removes_everything(self):
        site_id = self._create().data["id"]
        self.client.patch(reverse("site-detail", args=[site_id]), {"status": "disabled"}, format="json")
        self.assertEqual(self.client.get("/_sites/my-shop/").status_code, 404)
        self.assertEqual(self.client.delete(reverse("site-detail", args=[site_id])).status_code, 204)
        self.assertFalse(any(key.startswith(f"sites/{site_id}/") for key, _ in get_client().list_all_keys()))
        self.assertTrue(AuditEvent.objects.filter(action="site.deleted", resource_id=site_id).exists())

    def test_a_refused_zip_stores_nothing(self):
        resp = self._create(files={"index.html": INDEX, "x.php": b"<?php"})
        self.assertEqual(resp.status_code, 400)
        self.assertIn("server code", resp.data["detail"])
        self.assertFalse(Site.objects.exists())

    def test_addresses_are_validated_and_unique(self):
        self.assertEqual(self._create().status_code, 201)
        for slug, message in (("my-shop", "already in use"), ("api", "reserved"), ("Bad Slug", "lower-case")):
            with self.subTest(slug):
                resp = self._create(slug=slug)
                self.assertEqual(resp.status_code, 400)
                self.assertIn(message, resp.data["detail"])


class SitePermissionTests(SiteTestBase):
    def tearDown(self):
        SiteLifecycleTests.tearDown(self)

    def test_a_member_without_a_role_is_refused(self):
        site_id = self._create().data["id"]
        member = self._member("plain@example.com")
        self.client.force_login(member)
        self.assertEqual(self.client.get(reverse("site-list-create", args=[self.org_id])).status_code, 403)
        self.assertEqual(self.client.get(reverse("site-detail", args=[site_id])).status_code, 403)
        self.assertEqual(self.client.delete(reverse("site-detail", args=[site_id])).status_code, 403)

    def test_a_viewer_reads_but_cannot_change(self):
        site_id = self._create().data["id"]
        self.client.force_login(self._member("viewer@example.com", role="viewer"))
        self.assertEqual(self.client.get(reverse("site-detail", args=[site_id])).status_code, 200)
        self.assertEqual(
            self.client.patch(
                reverse("site-detail", args=[site_id]), {"status": "disabled"}, format="json"
            ).status_code,
            403,
        )
        self.assertEqual(self._create(slug="viewer-site").status_code, 403)

    def test_a_developer_publishes(self):
        self.client.force_login(self._member("dev@example.com", role="developer"))
        self.assertEqual(self._create(slug="dev-site").status_code, 201)

    def test_another_organization_cannot_reach_a_site_by_id(self):
        site_id = self._create().data["id"]
        version_id = Site.objects.get(id=site_id).active_version_id
        outsider = User.objects.create_user(email="outsider@example.com", password="x")
        self.client.force_login(outsider)
        other_org = self.client.post(reverse("organization-list-create"), {"name": "Other"}).data["id"]
        # An administrator of their own organization, still nothing of ours.
        self.assertEqual(self.client.get(reverse("site-list-create", args=[self.org_id])).status_code, 404)
        self.assertEqual(self.client.get(reverse("site-list-create", args=[other_org])).data, [])
        for method, url in (
            ("get", reverse("site-detail", args=[site_id])),
            ("patch", reverse("site-detail", args=[site_id])),
            ("delete", reverse("site-detail", args=[site_id])),
            ("get", reverse("site-version-list-create", args=[site_id])),
            ("post", reverse("site-version-activate", args=[site_id, version_id])),
            ("delete", reverse("site-version-detail", args=[site_id, version_id])),
        ):
            with self.subTest(method=method, url=url):
                self.assertEqual(getattr(self.client, method)(url).status_code, 404)
        self.assertTrue(Site.objects.filter(id=site_id).exists())
