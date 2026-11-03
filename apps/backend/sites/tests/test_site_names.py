"""
A site's own name on the shop network (ADR-0020 decision 3): which names are allowed (never IntraForge's own
or one under it), serving by name through the proxy's header, the on-demand certificate check, and a Node.js
app's routes following its name.
"""

import json
import os
import tempfile
from unittest.mock import patch

from django.test import SimpleTestCase, override_settings
from django.urls import reverse

from app_runner import recipe
from app_runner.server import Runner
from audit.models import AuditEvent
from sites.models import Site
from sites.tests.test_server_apps import APP, RUNNER
from sites.tests.test_sites import INDEX, SiteTestBase, upload
from storage.backends import get_client


@override_settings(
    ALLOWED_HOSTS=["testserver", "localhost", "127.0.0.1", "backend", "shop-pc", "192.168.1.20"]
)
class SiteNameTests(SiteTestBase):
    def tearDown(self):
        for site in Site.objects.all():
            for version in site.versions.all():
                for path in version.files:
                    get_client().delete(version.storage_prefix + path)

    def _name(self, site_id, hostname):
        return self.client.patch(
            reverse("site-detail", args=[site_id]), {"hostname": hostname}, format="json"
        )

    def test_a_site_answers_under_its_own_name(self):
        site_id = self._create().data["id"]
        resp = self._name(site_id, "MyShop.LAN")
        self.assertEqual(resp.status_code, 200, resp.data)
        self.assertEqual(resp.data["hostname"], "myshop.lan")
        page = self.client.get("/_sites/_host/", HTTP_X_INTRAFORGE_SITE_HOST="myshop.lan:8445")
        self.assertEqual(b"".join(page.streaming_content), INDEX)
        self.assertIn("sandbox", page["Content-Security-Policy"])
        # Another name, or no name, gets nothing.
        self.assertEqual(
            self.client.get("/_sites/_host/", HTTP_X_INTRAFORGE_SITE_HOST="other.lan").status_code, 404
        )
        self.assertEqual(self.client.get("/_sites/_host/").status_code, 404)
        self.assertTrue(AuditEvent.objects.filter(action="site.hostname.changed").exists())

    def test_intraforge_names_and_bad_names_are_refused(self):
        site_id = self._create().data["id"]
        for name, message in (
            ("shop-pc", "a name with a dot"),
            ("app.shop-pc", "IntraForge's own name"),
            ("x.localhost", "IntraForge's own name"),
            ("192.168.1.30", "a name with a dot"),
            ("my shop.lan", "a name with a dot"),
            ("a.b", "a name with a dot"),
        ):
            with self.subTest(name):
                resp = self._name(site_id, name)
                self.assertEqual(resp.status_code, 400)
                self.assertIn(message, resp.data["detail"])

    def test_a_name_belongs_to_one_site_and_can_be_removed(self):
        first = self._create(slug="first").data["id"]
        second = self._create(slug="second").data["id"]
        self.assertEqual(self._name(first, "shop.lan").status_code, 200)
        self.assertIn("already used", self._name(second, "shop.lan").data["detail"])
        self.assertEqual(self._name(first, "").data["hostname"], None)
        self.assertEqual(self._name(second, "shop.lan").status_code, 200)

    def test_the_certificate_check_knows_only_online_site_names(self):
        site_id = self._create().data["id"]
        self._name(site_id, "shop.lan")
        self.assertEqual(self.client.get("/_sites-certificate/?domain=shop.lan").status_code, 200)
        self.assertEqual(self.client.get("/_sites-certificate/?domain=evil.example").status_code, 404)
        self.client.patch(reverse("site-detail", args=[site_id]), {"status": "disabled"}, format="json")
        self.assertEqual(self.client.get("/_sites-certificate/?domain=shop.lan").status_code, 404)

    @override_settings(**RUNNER)
    def test_a_node_apps_routes_follow_its_name(self):
        calls = []

        def fake(method, path, *, body=None, size=0, headers=None):
            calls.append((method, path, headers or {}))
            return {"state": "running", "log": ""}

        with patch("sites.runner._call", side_effect=fake):
            site_id = self.client.post(
                reverse("site-list-create", args=[self.org_id]),
                {"name": "App", "slug": "app", "file": upload(APP)},
                format="multipart",
            ).data["id"]
            self._name(site_id, "app.lan")
        method, path, headers = calls[-1]
        self.assertEqual((method, path), ("POST", f"/apps/{Site.objects.get().id.hex}/route"))
        import base64

        self.assertEqual(json.loads(base64.b64decode(headers["X-Route"]))["hostname"], "app.lan")


class RunnerRouteFileTests(SimpleTestCase):
    def test_route_files_follow_the_name_and_survive_a_restart(self):
        class FakeDocker:
            running = True

            def inspect(self, name):
                return {
                    "State": {"Running": self.running},
                    "Config": {"Labels": {"intraforge.app.slug": "app"}},
                    "RestartCount": 0,
                }

            def containers(self, label):
                return [{"Id": "proxy", "Labels": {"com.docker.compose.service": "proxy"}}]

            def network(self, name):
                return {"Containers": {"proxy": {}}}

            def exec(self, container, cmd):
                return 0

            def start(self, name):
                pass

            def stop(self, name):
                pass

        with tempfile.TemporaryDirectory() as routes:
            runner = Runner(
                FakeDocker(), project="p", routes_dir=routes, runtime_image="rt", memory_mb=1, nano_cpus=1
            )
            site = "d" * 32
            runner.set_route(recipe.check_route({"site": site, "slug": "app", "hostname": "app.lan"}))
            self.assertEqual(sorted(os.listdir(routes)), [f"{site}.caddy", f"{site}.host", f"{site}.json"])
            with open(os.path.join(routes, f"{site}.host"), encoding="utf-8") as fh:
                self.assertIn("host app.lan", fh.read())
            # Stopped: routes removed, what they were made from kept; started again: the name comes back.
            runner.stop(site)
            self.assertEqual(os.listdir(routes), [f"{site}.json"])
            runner.start(site)
            self.assertIn(f"{site}.host", os.listdir(routes))
            # Name removed: the own-name route goes.
            runner.set_route(recipe.check_route({"site": site, "slug": "app", "hostname": ""}))
            self.assertNotIn(f"{site}.host", os.listdir(routes))

    def test_bad_names_never_reach_a_route(self):
        for bad in ("app.lan\nimport /etc/passwd", "x", "a b.lan", "../x.lan"):
            with self.subTest(bad), self.assertRaises(recipe.RecipeError):
                recipe.check_route({"site": "d" * 32, "slug": "app", "hostname": bad})
