"""Feature groups (system/features.py): chosen in Setup, changed by the Super Administrator, enforced by the server."""

import os
import uuid
from unittest import mock

from django.urls import reverse
from rest_framework.test import APIClient, APITestCase

from accounts.models import User
from audit.models import AuditEvent
from permissions.management.commands.seed_permissions import Command as SeedPermissionsCommand
from permissions.services import assign_role
from service_apps.models import ServiceApp
from service_apps.tests.test_service_apps import ServiceAppTestBase
from sites.models import InternetGateway
from system import features
from system.models import FeatureSettings

ALL = list(features.GROUPS)


def set_groups(*groups):
    FeatureSettings.objects.update_or_create(pk=1, defaults={"enabled": list(groups)})


class ParseTests(APITestCase):
    def test_unset_means_everything_empty_means_nothing_unknown_is_ignored(self):
        self.assertEqual(features.parse(None), ALL)
        self.assertEqual(features.parse(""), [])
        self.assertEqual(features.parse(" files_data , nope,files_data,pay_media"), ["files_data", "pay_media"])

    def test_the_first_read_seeds_from_the_setup_choice_then_the_stored_value_wins(self):
        FeatureSettings.objects.all().delete()
        with mock.patch.dict(os.environ, {features.ENV_VAR: "business_apps,files_data"}):
            self.assertEqual(features.enabled_groups(), {"business_apps", "files_data"})
        with mock.patch.dict(os.environ, {features.ENV_VAR: ""}):
            self.assertEqual(features.enabled_groups(), {"business_apps", "files_data"})

    def test_an_installation_from_before_this_setting_keeps_everything(self):
        FeatureSettings.objects.all().delete()
        with mock.patch.dict(os.environ, {}):
            os.environ.pop(features.ENV_VAR, None)
            self.assertEqual(features.enabled_groups(), set(ALL))


class FeaturesApiTests(APITestCase):
    def setUp(self):
        SeedPermissionsCommand().handle()
        set_groups(*ALL)
        self.admin = User.objects.create_user(email="super@example.test", password="Pw-super-12345")
        assign_role(user=self.admin, role_slug="super-administrator", organization=None)
        self.person = User.objects.create_user(email="person@example.test", password="Pw-person-12345")
        self.url = reverse("system-features")

    def test_anyone_signed_in_can_read_it_nobody_else(self):
        self.assertIn(APIClient().get(self.url).status_code, (401, 403))
        self.client.force_login(self.person)
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual([g["key"] for g in resp.data["groups"]], ALL)
        self.assertTrue(all(g["enabled"] for g in resp.data["groups"]))
        self.assertTrue(resp.data["app_types"]["spare_parts"])

    def test_only_the_super_administrator_changes_it_and_it_is_audited(self):
        self.client.force_login(self.person)
        self.assertEqual(self.client.patch(self.url, {"enabled": ["files_data"]}, format="json").status_code, 403)
        self.assertEqual(features.enabled_groups(), set(ALL))

        self.client.force_login(self.admin)
        resp = self.client.patch(self.url, {"enabled": ["files_data", "business_apps"]}, format="json")
        self.assertEqual(resp.status_code, 200, resp.data)
        self.assertEqual(features.enabled_groups(), {"files_data", "business_apps"})
        self.assertFalse(resp.data["app_types"]["intraforge_pay"])
        event = AuditEvent.objects.get(action="system.features.update")
        self.assertEqual(event.context["after"], ["business_apps", "files_data"])
        self.assertEqual(event.context["before"], ALL)

    def test_unknown_groups_and_bad_bodies_are_refused(self):
        self.client.force_login(self.admin)
        self.assertEqual(self.client.patch(self.url, {"enabled": ["nope"]}, format="json").status_code, 400)
        self.assertEqual(self.client.patch(self.url, {"enabled": "files_data"}, format="json").status_code, 400)
        self.assertEqual(features.enabled_groups(), set(ALL))

    def test_websites_cannot_be_hidden_while_internet_access_is_on(self):
        gate = InternetGateway.current()
        gate.enabled = True
        gate.save()
        self.client.force_login(self.admin)
        resp = self.client.patch(self.url, {"enabled": ["files_data"]}, format="json")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("Internet access is on", str(resp.data))
        self.assertIn("websites_developer", features.enabled_groups())


class EnforcementTests(APITestCase):
    """A switched-off group is refused by the server, not just hidden in the web app."""

    def setUp(self):
        SeedPermissionsCommand().handle()
        set_groups(*ALL)
        self.user = User.objects.create_user(email="owner@example.test", password="Pw-owner-12345")
        self.client.force_login(self.user)

    def assertDisabled(self, resp, group):
        self.assertEqual(resp.status_code, 403, resp.content[:300])
        self.assertEqual(resp.json()["error"]["code"], "feature_disabled")
        self.assertEqual(resp.json()["error"]["group"], group)

    def test_files_and_data_routes_answer_feature_disabled_and_come_back(self):
        bucket = reverse("bucket-detail", kwargs={"bucket_id": uuid.uuid4()})
        self.assertEqual(self.client.get(bucket).status_code, 404)
        set_groups("business_apps", "pay_media", "websites_developer")
        self.assertDisabled(self.client.get(bucket), "files_data")
        set_groups(*ALL)
        self.assertEqual(self.client.get(bucket).status_code, 404, "back as it was")

    def test_developer_routes_oauth_and_hosted_sites_are_refused_when_off(self):
        set_groups("business_apps", "pay_media", "files_data")
        self.assertDisabled(self.client.get("/.well-known/openid-configuration"), "websites_developer")
        self.assertDisabled(self.client.get(reverse("internet-gateway")), "websites_developer")
        self.assertDisabled(self.client.get("/_sites-certificate/?domain=x"), "websites_developer")

    def test_application_credentials_stop_working_when_developer_is_off(self):
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION="Bearer pdc_sk_not-a-real-credential")
        self.assertIn("Invalid or expired credential", str(client.get(reverse("system-version")).content))
        set_groups("business_apps", "pay_media", "files_data")
        resp = client.get(reverse("system-version"))
        self.assertIn(resp.status_code, (401, 403))
        self.assertIn("switched off", str(resp.content))

    def test_movie_shop_and_its_portal_are_refused_when_pay_is_off(self):
        set_groups("business_apps", "websites_developer", "files_data")
        self.assertDisabled(self.client.get(reverse("portal-directory")), "pay_media")

    def test_the_core_stays_whatever_is_off(self):
        set_groups()
        self.assertEqual(self.client.get(reverse("system-version")).status_code, 200)
        self.assertEqual(self.client.get(reverse("system-features")).status_code, 200)
        self.assertEqual(self.client.get(reverse("organization-list-create")).status_code, 200)


class AppTypeTests(ServiceAppTestBase):
    """Business apps off: Spare Parts cannot be installed, listed, opened or kept open; nothing is deleted."""

    def setUp(self):
        super().setUp()
        set_groups(*ALL)

    def test_an_installed_app_is_hidden_while_off_and_comes_back(self):
        app_id = self.install().data["id"]
        self.assertEqual([a["id"] for a in self.client.get("/api/v1/service-apps/").data["results"]], [app_id])

        set_groups("pay_media", "websites_developer", "files_data")
        self.assertEqual(self.client.get("/api/v1/service-apps/").data["results"], [])
        self.assertEqual(self.client.post(f"/api/v1/service-apps/{app_id}/launch/").status_code, 404)
        self.assertEqual(APIClient().get(f"/api/v1/service-apps/{app_id}/sign-in/").status_code, 404)

        set_groups(*ALL)
        listed = self.client.get("/api/v1/service-apps/").data["results"]
        self.assertEqual([a["id"] for a in listed], [app_id], "nothing was deleted")

    def test_cannot_install_or_be_offered_while_off(self):
        set_groups("pay_media", "websites_developer", "files_data")
        self.assertEqual(self.client.get("/api/v1/service-apps/").data["available"], [])
        resp = self.install()
        self.assertEqual(resp.status_code, 403, resp.data)
        self.assertEqual(resp.data["error"]["code"], "feature_disabled")
        self.assertFalse(ServiceApp.objects.exists())

    def test_open_sessions_are_refused_by_introspection_while_off(self):
        app_id = self.install().data["id"]
        _, launch = self.open_as(self.owner, app_id)
        self.assertEqual(launch.status_code, 200)
        token = next(iter(launch.cookies.values())).value
        self.assertEqual(self.introspect(token).status_code, 200)
        set_groups("pay_media", "websites_developer", "files_data")
        self.assertEqual(self.introspect(token).status_code, 401)
        set_groups(*ALL)
        self.assertEqual(self.introspect(token).status_code, 200, "the session itself was never deleted")
