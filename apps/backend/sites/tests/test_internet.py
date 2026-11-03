"""
The internet gate (ADR-0020 decision 4): off by default; only the Super Administrator, with their password and
two-factor sign-in, switches it on; sites are published one by one and revoked; switching it off revokes all;
only published sites are served through it; the tunnel container is locked down.
"""

from unittest.mock import patch

from django.test import SimpleTestCase, override_settings
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.models import User
from app_runner import recipe
from audit.models import AuditEvent
from permissions.services import assign_role
from sites.models import InternetGateway, Site
from sites.tests.test_server_apps import RUNNER
from sites.tests.test_sites import INDEX, SiteTestBase
from storage.backends import get_client

TOKEN = "eyJhIjoiY2Y" + "A" * 120


@override_settings(**RUNNER)
class InternetGateTests(SiteTestBase):
    def setUp(self):
        super().setUp()
        self.calls = []
        patcher = patch("sites.runner._call", side_effect=self._fake)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.root = User.objects.create_user(email="root@example.test", password="Root-password-123")
        assign_role(user=self.root, role_slug="super-administrator", organization=None)
        self.root.mfa_enabled = True
        self.root.save(update_fields=["mfa_enabled"])
        self.root_client = APIClient()
        self.root_client.force_login(self.root)
        self.site_id = self._create().data["id"]

    def tearDown(self):
        for site in Site.objects.all():
            for version in site.versions.all():
                for path in version.files:
                    get_client().delete(version.storage_prefix + path)

    def _fake(self, method, path, *, body=None, size=0, headers=None):
        self.calls.append((method, path))
        return {"state": "running", "log": ""}

    def _enable(self, client=None, password="Root-password-123", token=TOKEN):
        return (client or self.root_client).post(
            reverse("internet-gateway-enable"), {"token": token, "password": password}, format="json"
        )

    def _publish(self, client=None, hostname="www.myshop.com"):
        return (client or self.root_client).post(
            reverse("site-internet", args=[self.site_id]), {"hostname": hostname}, format="json"
        )

    def _visit(self, host):
        return self.client.get("/_sites/_internet/", HTTP_X_INTRAFORGE_SITE_HOST=host)

    def test_it_is_off_by_default_and_serves_nothing(self):
        self.assertFalse(InternetGateway.current().enabled)
        self.assertEqual(
            self.client.get(reverse("internet-gateway")).data, {"enabled": False, "can_manage": False}
        )
        self.assertEqual(self._visit("www.myshop.com").status_code, 404)

    def test_an_organization_administrator_cannot_touch_it(self):
        # self.client is the organization's creator: organization administrator, not Super Administrator.
        self.assertEqual(self._enable(self.client).status_code, 403)
        self.assertEqual(self._publish(self.client).status_code, 403)
        self.assertEqual(self.client.post(reverse("internet-gateway-disable")).status_code, 403)
        self.assertEqual(self.calls, [])

    def test_switching_on_needs_the_password_two_factor_and_a_token(self):
        self.assertIn("password is not correct", str(self._enable(password="wrong").data))
        self.assertIn("tunnel token", str(self._enable(token="short").data))
        self.root.mfa_enabled = False
        self.root.save(update_fields=["mfa_enabled"])
        self.assertIn("two-factor", str(self._enable().data))
        self.assertFalse(InternetGateway.current().enabled)
        self.assertEqual(self.calls, [])

    def test_publish_serve_revoke_and_switch_off(self):
        self.assertEqual(self._publish().status_code, 400)  # the gate is off
        resp = self._enable()
        self.assertEqual(resp.status_code, 200, resp.data)
        self.assertIn(("POST", "/tunnel/start"), self.calls)
        gate = InternetGateway.current()
        self.assertTrue(gate.enabled)
        self.assertNotIn(TOKEN.encode(), bytes(gate.token_encrypted))  # stored encrypted
        self.assertEqual(self._visit("www.myshop.com").status_code, 404)  # nothing published yet

        for bad in ("myshop.lan", "localhost.com.x1", "shop"):
            with self.subTest(bad):
                self.assertEqual(self._publish(hostname=bad).status_code, 400)
        resp = self._publish()
        self.assertEqual(resp.status_code, 200, resp.data)
        self.assertEqual(resp.data["internet_hostname"], "www.myshop.com")
        page = self._visit("www.myshop.com")
        self.assertEqual(b"".join(page.streaming_content), INDEX)
        self.assertIn("sandbox", page["Content-Security-Policy"])
        self.assertEqual(self._visit("other.com").status_code, 404)

        self.root_client.delete(reverse("site-internet", args=[self.site_id]))
        self.assertEqual(self._visit("www.myshop.com").status_code, 404)

        self._publish()
        self.root_client.post(reverse("internet-gateway-disable"))
        self.assertIn(("POST", "/tunnel/stop"), self.calls)
        self.assertIsNone(Site.objects.get(id=self.site_id).internet_hostname)
        self.assertIsNone(InternetGateway.current().token_encrypted)
        self.assertEqual(self._visit("www.myshop.com").status_code, 404)
        actions = set(AuditEvent.objects.values_list("action", flat=True))
        self.assertTrue(
            {
                "internet.gateway.enabled",
                "site.internet.published",
                "site.internet.revoked",
                "internet.gateway.disabled",
            }
            <= actions
        )

    def test_an_offline_site_cannot_be_published_and_a_name_is_used_once(self):
        self._enable()
        self.client.patch(reverse("site-detail", args=[self.site_id]), {"status": "disabled"}, format="json")
        self.assertIn("online first", str(self._publish().data))
        self.client.patch(reverse("site-detail", args=[self.site_id]), {"status": "active"}, format="json")
        self.assertEqual(self._publish().status_code, 200)
        other = self._create(slug="other").data["id"]
        resp = self.root_client.post(
            reverse("site-internet", args=[other]), {"hostname": "www.myshop.com"}, format="json"
        )
        self.assertIn("already published", str(resp.data))


class TunnelRecipeTests(SimpleTestCase):
    def test_the_tunnel_container_is_locked_down(self):
        cfg = recipe.tunnel_config(
            TOKEN, image="cloudflare/cloudflared:2026.10.0", network="p_edge", project="p"
        )
        host = cfg["HostConfig"]
        self.assertEqual(cfg["Cmd"], ["tunnel", "--no-autoupdate", "run"])
        self.assertEqual(host["NetworkMode"], "p_edge")
        self.assertTrue(host["ReadonlyRootfs"])
        self.assertEqual(host["CapDrop"], ["ALL"])
        self.assertEqual(host["PortBindings"], {})
        self.assertNotIn("Binds", host)

    def test_a_bad_token_never_reaches_docker(self):
        for bad in ("short", "a" * 80 + "\n--config /x", "a b" * 40):
            with self.subTest(bad), self.assertRaises(recipe.RecipeError):
                recipe.tunnel_config(bad, image="i", network="n", project="p")
