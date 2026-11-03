"""
Hosted Node.js server apps (ADR-0020): the zip and manifest rules, the lifecycle through the app runner (a
fake here: the test container has no Docker), the app's own scoped credential, and the runner's locked
recipe.
"""

import base64
import io
import json
import tarfile
import threading
from http.server import ThreadingHTTPServer
from unittest.mock import patch
from urllib.request import Request, urlopen

from django.test import SimpleTestCase, override_settings
from django.urls import reverse

from app_runner import recipe
from app_runner.server import Runner, _build_context, make_handler
from applications.models import ApplicationCredential
from applications.services import resolve_credential
from audit.models import AuditEvent
from sites.archive import SiteArchiveError, plan_archive
from sites.models import Site
from sites.tests.test_sites import INDEX, SiteTestBase, make_zip, upload
from storage.backends import get_client

SERVER = b"require('http').createServer((q, s) => s.end('hi')).listen(process.env.PORT)"
APP = {"intraforge.json": b'{"runtime": "node", "entry": "server.js"}', "server.js": SERVER}
RUNNER = {"SITES_RUNNER_URL": "http://runner:8700", "SITES_RUNNER_TOKEN": "t" * 32}


class ManifestTests(SimpleTestCase):
    def _plan(self, files):
        return plan_archive(io.BytesIO(make_zip(files)))[1]

    def test_a_node_app_is_recognised_by_its_manifest(self):
        plan = self._plan(
            {**APP, "node_modules/x/index.js": b"1", "data/seed.sqlite": b"x", ".env": b"SECRET=1"}
        )
        self.assertEqual(plan.manifest, {"runtime": "node", "entry": "server.js"})
        # Any file the code needs, but hidden files (.env) are left out.
        self.assertEqual(
            [f.path for f in plan.files],
            ["data/seed.sqlite", "intraforge.json", "node_modules/x/index.js", "server.js"],
        )

    def test_manifest_refusals(self):
        cases = {
            "other runtime": (
                {"intraforge.json": b'{"runtime": "php", "entry": "a.php"}'},
                '"runtime": "node"',
            ),
            "no entry": ({"intraforge.json": b'{"runtime": "node"}', "a.js": b"1"}, 'needs "entry"'),
            "entry missing": (
                {"intraforge.json": b'{"runtime": "node", "entry": "app.js"}'},
                "not in the zip",
            ),
            "entry escapes": (
                {"intraforge.json": b'{"runtime": "node", "entry": "../x.js"}'},
                'needs "entry"',
            ),
            "not json": ({"intraforge.json": b"{", "a.js": b"1"}, "not valid JSON"),
            "windows program": ({**APP, "tool.exe": b"MZ"}, "Windows programs (.exe)"),
        }
        for label, (files, message) in cases.items():
            with self.subTest(label), self.assertRaisesMessage(SiteArchiveError, message):
                self._plan(files)

    def test_a_website_with_server_code_points_to_the_manifest(self):
        with self.assertRaisesMessage(SiteArchiveError, "intraforge.json"):
            self._plan({"index.html": INDEX, "server.js": SERVER, "app.php": b"<?php"})


@override_settings(**RUNNER)
class ServerAppLifecycleTests(SiteTestBase):
    def setUp(self):
        super().setUp()
        self.calls = []
        self.state = {"state": "running", "log": ""}
        patcher = patch("sites.runner._call", side_effect=self._fake_call)
        patcher.start()
        self.addCleanup(patcher.stop)

    def _fake_call(self, method, path, *, body=None, size=0, headers=None):
        entry = {"method": method, "path": path}
        if body is not None:
            entry["meta"] = json.loads(base64.b64decode(headers["X-Deploy"]))
            with tarfile.open(fileobj=body, mode="r") as tar:
                entry["files"] = sorted(m.name for m in tar.getmembers())
        self.calls.append(entry)
        return dict(self.state)

    def tearDown(self):
        for site in Site.objects.all():
            for version in site.versions.all():
                for path in version.files:
                    get_client().delete(version.storage_prefix + path)

    def _create_app(self, slug="my-app"):
        return self.client.post(
            reverse("site-list-create", args=[self.org_id]),
            {"name": "My app", "slug": slug, "file": upload(APP)},
            format="multipart",
        )

    def test_publishing_a_node_app_deploys_it_with_its_own_credential(self):
        resp = self._create_app()
        self.assertEqual(resp.status_code, 201, resp.data)
        self.assertEqual(resp.data["kind"], "node")
        self.assertEqual(resp.data["runtime_state"], "running")
        deploy = self.calls[0]
        self.assertEqual(deploy["path"], f"/apps/{Site.objects.get().id.hex}/deploy")
        self.assertEqual(deploy["meta"]["entry"], "server.js")
        self.assertEqual(deploy["files"], ["intraforge.json", "server.js"])
        # The app's token is a real credential of its own Application -- which holds no grants yet.
        site = Site.objects.get()
        credential = resolve_credential(deploy["meta"]["env"]["IF_API_TOKEN"])
        self.assertEqual(credential.service_account.application_id, site.application_id)
        self.assertEqual(str(site.application.organization_id), self.org_id)
        self.assertTrue(AuditEvent.objects.filter(action="site.app.deployed").exists())

    def test_a_new_version_replaces_the_credential(self):
        site_id = self._create_app().data["id"]
        first = resolve_credential(self.calls[0]["meta"]["env"]["IF_API_TOKEN"])
        self.client.post(
            reverse("site-version-list-create", args=[site_id]), {"file": upload(APP)}, format="multipart"
        )
        first.refresh_from_db()
        self.assertIsNotNone(first.revoked_at)
        self.assertEqual(
            ApplicationCredential.objects.filter(
                service_account__application_id=Site.objects.get().application_id, revoked_at__isnull=True
            ).count(),
            1,
        )

    def test_its_files_are_never_served_as_a_website(self):
        self._create_app()
        for url in ("/_sites/my-app/", "/_sites/my-app/server.js", "/_sites/my-app/intraforge.json"):
            with self.subTest(url):
                resp = self.client.get(url)
                self.assertEqual(resp.status_code, 503)
                self.assertNotIn(b"createServer", resp.content)

    def test_offline_online_and_delete_go_through_the_runner(self):
        site_id = self._create_app().data["id"]
        site = Site.objects.get()
        hex_id, application_id = site.id.hex, site.application_id
        self.client.patch(reverse("site-detail", args=[site_id]), {"status": "disabled"}, format="json")
        self.client.patch(reverse("site-detail", args=[site_id]), {"status": "active"}, format="json")
        self.assertEqual(self.client.delete(reverse("site-detail", args=[site_id])).status_code, 204)
        self.assertEqual(
            [(c["method"], c["path"]) for c in self.calls[1:]],
            [
                ("POST", f"/apps/{hex_id}/stop"),
                ("POST", f"/apps/{hex_id}/start"),
                ("DELETE", f"/apps/{hex_id}"),
            ],
        )
        # The deleted app's credential no longer works. (Scoped to this app: the test database is reused
        # between runs, and tests that commit for real leave other applications' credentials behind.)
        self.assertFalse(
            ApplicationCredential.objects.filter(
                service_account__application_id=application_id, revoked_at__isnull=True
            ).exists()
        )

    def test_a_runner_failure_is_recorded_not_lost(self):
        from sites import runner

        with patch("sites.runner._call", side_effect=runner.RunnerRefused("build failed: no such file")):
            resp = self._create_app()
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.data["runtime_state"], "failed")
        self.assertIn("build failed", resp.data["runtime_log"])
        self.assertTrue(AuditEvent.objects.filter(action="site.app.failed", result="error").exists())

    @override_settings(SITES_RUNNER_URL="", SITES_RUNNER_TOKEN="")
    def test_without_a_runner_node_apps_are_refused_up_front(self):
        resp = self._create_app()
        self.assertEqual(resp.status_code, 400)
        self.assertIn("not available on this installation", resp.data["detail"])
        self.assertFalse(Site.objects.exists())


class RecipeTests(SimpleTestCase):
    META = {
        "site": "a" * 32,
        "slug": "shop",
        "version": "b" * 32,
        "entry": "dist/server.js",
        "env": {"IF_API_URL": "http://intraforge:8080/api/v1/", "IF_API_TOKEN": "tok"},
    }

    def test_the_container_is_locked_down_whatever_the_request(self):
        meta = recipe.check_deploy(self.META)
        cfg = recipe.container_config(meta, image="img", memory_mb=256, nano_cpus=500_000_000, project="p")
        host = cfg["HostConfig"]
        self.assertEqual(cfg["Cmd"], ["node", "dist/server.js"])
        self.assertEqual(cfg["User"], "1000:1000")
        self.assertTrue(host["ReadonlyRootfs"])
        self.assertEqual(host["CapDrop"], ["ALL"])
        self.assertIn("no-new-privileges:true", host["SecurityOpt"])
        self.assertFalse(host["Privileged"])
        self.assertEqual(host["Memory"], 256 * 1024 * 1024)
        self.assertEqual(host["NetworkMode"], f"ifapp-{'a' * 32}")
        self.assertEqual(host["PortBindings"], {})
        self.assertNotIn("Binds", host)
        self.assertTrue(recipe.network_config(meta, "p")["Internal"])

    def test_requests_cannot_choose_anything_else(self):
        bad = {
            "entry with a command": {**self.META, "entry": "server.js; rm -rf /"},
            "entry outside": {**self.META, "entry": "../x.js"},
            "other env": {**self.META, "env": {"NODE_OPTIONS": "--require /x"}},
            "bad site": {**self.META, "site": "../../etc"},
            "bad slug": {**self.META, "slug": "Shop!"},
        }
        for label, meta in bad.items():
            with self.subTest(label), self.assertRaises(recipe.RecipeError):
                recipe.check_deploy(meta)

    def test_the_route_strips_the_prefix(self):
        text = recipe.route(recipe.check_deploy(self.META))
        self.assertIn("uri strip_prefix /shop", text)
        self.assertIn(f"reverse_proxy ifapp-{'a' * 32}:3000", text)

    def test_the_upload_is_repacked_and_refuses_unsafe_members(self):
        def tar_of(members):
            buf = io.BytesIO()
            with tarfile.open(fileobj=buf, mode="w") as tar:
                for name, data, kind in members:
                    info = tarfile.TarInfo(name)
                    info.type = kind
                    info.size = len(data)
                    tar.addfile(info, io.BytesIO(data))
            buf.seek(0)
            return buf

        out = io.BytesIO()
        _build_context(out, tar_of([("server.js", b"x", tarfile.REGTYPE)]), recipe.dockerfile("rt"))
        out.seek(0)
        with tarfile.open(fileobj=out) as tar:
            self.assertEqual(tar.getnames(), ["Dockerfile", "app/server.js"])
        for name, kind in (
            ("../evil.js", tarfile.REGTYPE),
            ("/etc/x", tarfile.REGTYPE),
            ("l", tarfile.SYMTYPE),
        ):
            with self.subTest(name), self.assertRaises(recipe.RecipeError):
                _build_context(io.BytesIO(), tar_of([(name, b"", kind)]), b"")


class RunnerApiTests(SimpleTestCase):
    def test_every_operation_needs_the_token(self):
        class FakeDocker:
            def inspect(self, name):
                return None

        runner = Runner(
            FakeDocker(), project="p", routes_dir=".", runtime_image="rt", memory_mb=1, nano_cpus=1
        )
        server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(runner, "s" * 32))
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.shutdown)
        base = f"http://127.0.0.1:{server.server_address[1]}"

        def get(path, token=None):
            req = Request(base + path, headers={"Authorization": f"Bearer {token}"} if token else {})
            try:
                with urlopen(req) as resp:  # noqa: S310 (local test server)
                    return resp.status, json.loads(resp.read())
            except Exception as exc:  # noqa: BLE001
                return exc.code, None

        site = "c" * 32
        self.assertEqual(get("/healthz")[0], 200)
        self.assertEqual(get(f"/apps/{site}")[0], 401)
        self.assertEqual(get(f"/apps/{site}", "wrong")[0], 401)
        self.assertEqual(get(f"/apps/{site}", "s" * 32), (200, {"state": "missing", "log": ""}))
        self.assertEqual(get("/apps/../../etc", "s" * 32)[0], 404)
