from unittest.mock import patch

from botocore.exceptions import EndpointConnectionError
from django.test import override_settings
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

    def test_readyz_reports_object_storage_against_the_real_store(self):
        response = self.client.get(reverse("readyz"))
        self.assertEqual(response.json()["checks"]["object_storage"], "ok")

    def test_unreachable_object_storage_makes_readyz_unavailable(self):
        down = EndpointConnectionError(endpoint_url="http://object-storage:9000")
        with patch("storage.backends.check_object_storage", side_effect=down):
            response = self.client.get(reverse("readyz"))
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["checks"]["object_storage"], "unreachable")

    def test_a_missing_bucket_still_counts_as_reachable(self):
        # The store answered; the bucket is created on first upload. A probe must not create it.
        with override_settings(OBJECT_STORAGE_BUCKET_PREFIX="readyz-probe-never-created"):
            response = self.client.get(reverse("readyz"))
        self.assertEqual(response.json()["checks"]["object_storage"], "ok")

    def test_metrics_exposes_object_storage_gauge(self):
        response = self.client.get(reverse("metrics"))
        self.assertIn('pdc_dependency_up{dependency="object_storage"} 1', response.content.decode())
