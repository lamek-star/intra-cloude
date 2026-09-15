from django.core.cache import cache
from django.urls import reverse
from rest_framework.test import APITestCase

from accounts.models import User
from oauth_provider import services
from oauth_provider.models import OAuthClient
from permissions.management.commands.seed_permissions import Command as SeedPermissionsCommand
from permissions.services import assign_role


def seed():
    SeedPermissionsCommand().handle()


class OAuthClientAdminTests(APITestCase):
    """Registering an OAuth client is a platform-wide capability (any
    registered client can authenticate ANY user on the deployment) --
    gated by `system.admin`, never an organization-scoped permission."""

    def setUp(self):
        cache.clear()
        seed()
        self.admin = User.objects.create_user(email="root@example.com", password="x")
        assign_role(user=self.admin, role_slug="super-administrator", organization=None)
        self.plain_user = User.objects.create_user(email="plain@example.com", password="x")

    def test_plain_authenticated_user_cannot_create_a_client(self):
        self.client.force_login(self.plain_user)
        response = self.client.post(
            reverse("oauth-client-list-create"),
            {"name": "Sneaky App", "redirect_uris": ["https://example.com/callback"]},
            format="json",
        )
        self.assertEqual(response.status_code, 403)
        self.assertFalse(OAuthClient.objects.filter(name="Sneaky App").exists())

    def test_anonymous_cannot_list_clients(self):
        response = self.client.get(reverse("oauth-client-list-create"))
        self.assertEqual(response.status_code, 403)

    def test_super_administrator_can_create_a_client_and_secret_is_shown_exactly_once(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("oauth-client-list-create"),
            {"name": "Harmoney Spare Parts", "redirect_uris": ["https://spareparts.example.com/auth/callback"]},
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertIn("client_secret", response.data)
        self.assertIn("client_id", response.data)
        client_id = response.data["id"]

        detail = self.client.get(reverse("oauth-client-detail", args=[client_id]))
        self.assertEqual(detail.status_code, 200)
        self.assertNotIn("client_secret", detail.data)
        self.assertNotIn("client_secret_hash", detail.data)

    def test_creating_a_client_with_no_redirect_uri_is_rejected(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("oauth-client-list-create"), {"name": "No URIs", "redirect_uris": []}, format="json"
        )
        self.assertEqual(response.status_code, 400)

    def test_javascript_scheme_redirect_uri_is_rejected_at_registration(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("oauth-client-list-create"),
            {"name": "Bad App", "redirect_uris": ["javascript:alert(1)"]},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_admin_can_disable_a_client(self):
        client, _ = services.create_client(name="Toggle Me", redirect_uris=["https://x.example.com/cb"])
        self.client.force_login(self.admin)
        response = self.client.patch(reverse("oauth-client-detail", args=[client.id]), {"enabled": False}, format="json")
        self.assertEqual(response.status_code, 200)
        client.refresh_from_db()
        self.assertFalse(client.enabled)

    def test_admin_can_rotate_the_secret_and_the_old_one_stops_working(self):
        client, old_secret = services.create_client(name="Rotate Me", redirect_uris=["https://x.example.com/cb"])
        self.assertTrue(services.verify_client_secret(client, old_secret))

        self.client.force_login(self.admin)
        response = self.client.post(reverse("oauth-client-rotate-secret", args=[client.id]))
        self.assertEqual(response.status_code, 200)
        new_secret = response.data["client_secret"]
        self.assertNotEqual(new_secret, old_secret)

        client.refresh_from_db()
        self.assertFalse(services.verify_client_secret(client, old_secret))
        self.assertTrue(services.verify_client_secret(client, new_secret))

    def test_plain_user_cannot_disable_or_rotate(self):
        client, _ = services.create_client(name="Protected", redirect_uris=["https://x.example.com/cb"])
        self.client.force_login(self.plain_user)
        self.assertEqual(
            self.client.patch(reverse("oauth-client-detail", args=[client.id]), {"enabled": False}, format="json").status_code,
            403,
        )
        self.assertEqual(
            self.client.post(reverse("oauth-client-rotate-secret", args=[client.id])).status_code, 403
        )
