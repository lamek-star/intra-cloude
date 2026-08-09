from django.urls import reverse
from rest_framework.test import APITestCase


class MetricsTests(APITestCase):
    databases = {"default", "tenant"}

    def test_metrics_returns_prometheus_text_with_dependency_gauges(self):
        response = self.client.get(reverse("metrics"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/plain", response["Content-Type"])

        body = response.content.decode()
        self.assertIn("# TYPE pdc_dependency_up gauge", body)
        self.assertIn('pdc_dependency_up{dependency="database:default"} 1', body)
        self.assertIn('pdc_dependency_up{dependency="database:tenant"} 1', body)
        self.assertIn('pdc_dependency_up{dependency="valkey"}', body)

    def test_metrics_requires_no_authentication(self):
        response = self.client.get(reverse("metrics"))
        self.assertNotEqual(response.status_code, 403)
