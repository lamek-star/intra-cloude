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

    def test_the_super_administrator_sees_every_online_site_that_can_be_published(self):
        # The Super Administrator publishes platform-wide but is usually not a member of the shop's
        # organization, so the gate's status lists the online, unpublished sites to choose from.
        status = self.root_client.get(reverse("internet-gateway")).data
        self.assertEqual([c["site"] for c in status["publishable"]], [self.site_id])
        self.assertEqual(status["publishable"][0]["organization"], "Shop")
        self.client.patch(reverse("site-detail", args=[self.site_id]), {"status": "disabled"}, format="json")
        self.assertEqual(self.root_client.get(reverse("internet-gateway")).data["publishable"], [])
        # Others learn only whether the gate is on.
        self.assertNotIn("publishable", self.client.get(reverse("internet-gateway")).data)

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

    # --- auto-publish ---------------------------------------------------------------------------------------

    def _auto(self, domain="harmongt.uk", client=None, password="Root-password-123"):
        return (client or self.root_client).post(
            reverse("internet-gateway-auto-publish"), {"domain": domain, "password": password}, format="json"
        )

    def _name(self, site_id):
        return Site.objects.get(id=site_id).internet_hostname

    def test_auto_publish_is_the_super_administrators_with_the_password_and_the_gate_on(self):
        self.assertEqual(self._auto(client=self.client).status_code, 403)  # an organization administrator
        self.assertIn("Switch internet access on first", str(self._auto().data))
        self._enable()
        self.assertIn("password is not correct", str(self._auto(password="wrong").data))
        for bad in ("shop.lan", "localhost", "harmongt"):
            with self.subTest(bad):
                self.assertEqual(self._auto(domain=bad).status_code, 400)
        self.assertEqual(InternetGateway.current().auto_domain, "")
        self.assertIsNone(self._name(self.site_id))

    def test_every_online_site_is_published_now_and_later_and_offline_gives_the_name_back(self):
        self._enable()
        offline = self._create(slug="closed-shop").data["id"]
        self.client.patch(reverse("site-detail", args=[offline]), {"status": "disabled"}, format="json")

        resp = self._auto()
        self.assertEqual(resp.status_code, 200, resp.data)
        self.assertEqual(resp.data["auto_domain"], "harmongt.uk")
        self.assertEqual(self._name(self.site_id), "my-shop.harmongt.uk")
        self.assertIsNone(self._name(offline))  # offline sites are not published
        self.assertTrue(Site.objects.get(id=self.site_id).internet_auto)
        self.assertEqual(b"".join(self._visit("my-shop.harmongt.uk").streaming_content), INDEX)

        # A site created afterwards is published at once, with nobody pressing anything.
        later = self._create(slug="menu").data["id"]
        self.assertEqual(self._name(later), "menu.harmongt.uk")
        # Taking it offline gives the name back; online again takes it again.
        self.client.patch(reverse("site-detail", args=[later]), {"status": "disabled"}, format="json")
        self.assertIsNone(self._name(later))
        self.assertEqual(self._visit("menu.harmongt.uk").status_code, 404)
        self.client.patch(reverse("site-detail", args=[later]), {"status": "active"}, format="json")
        self.assertEqual(self._name(later), "menu.harmongt.uk")

        events = AuditEvent.objects.filter(action="site.internet.published", context__auto=True)
        self.assertEqual(events.count(), 3)
        self.assertTrue(AuditEvent.objects.filter(action="internet.auto_publish.enabled").exists())

    def test_switching_off_takes_back_only_automatic_names(self):
        self._enable()
        self.assertEqual(self._publish().status_code, 200)  # published by hand: www.myshop.com
        other = self._create(slug="menu").data["id"]
        self._auto()
        self.assertEqual(self._name(self.site_id), "www.myshop.com")  # a hand-published name is not replaced
        self.assertEqual(self._name(other), "menu.harmongt.uk")

        resp = self._auto(domain="")
        self.assertEqual(resp.status_code, 200, resp.data)
        self.assertEqual(resp.data["auto_domain"], "")
        self.assertEqual(self._name(self.site_id), "www.myshop.com")
        self.assertIsNone(self._name(other))
        self.assertTrue(AuditEvent.objects.filter(action="internet.auto_publish.disabled").exists())

        # Switching the whole gate off also switches auto-publish off.
        self._auto()
        self.root_client.post(reverse("internet-gateway-disable"))
        self.assertEqual(InternetGateway.current().auto_domain, "")
        self.assertIsNone(self._name(other))

    def test_a_name_already_published_by_hand_is_not_taken_and_the_audit_says_why(self):
        self._enable()
        # By hand, someone published the name auto-publish would give the "menu" site.
        self.assertEqual(self._publish(hostname="menu.harmongt.uk").status_code, 200)
        self._auto()
        menu = self._create(slug="menu").data["id"]
        self.assertIsNone(self._name(menu))
        failed = AuditEvent.objects.get(action="site.internet.auto_failed")
        self.assertEqual(failed.result, "error")
        self.assertEqual(failed.context["internet_hostname"], "menu.harmongt.uk")


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
