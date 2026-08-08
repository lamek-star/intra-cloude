from django.urls import reverse
from rest_framework.test import APITestCase


class HealthzTests(APITestCase):
    def test_healthz_returns_ok_without_authentication(self):
        response = self.client.get(reverse("healthz"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})


class ReadyzTests(APITestCase):
    # /readyz checks both the control-plane ("default") and tenant database
    # connections — Django's test isolation blocks queries to any alias not
    # declared here (confirmed by actually running this once "tenant" was a
    # real, exercised connection in Phase 2).
    databases = {"default", "tenant"}

    def test_readyz_reports_database_status(self):
        response = self.client.get(reverse("readyz"))
        self.assertIn("checks", response.json())
        self.assertIn("database:default", response.json()["checks"])
