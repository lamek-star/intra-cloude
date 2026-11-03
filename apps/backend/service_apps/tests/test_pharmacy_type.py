"""The Pharmacy application type: its own default-deny capabilities, staff roles and Eritrean defaults."""

from django.conf import settings
from django.test import SimpleTestCase

from permissions.catalog import ORGANIZATION_ROLE_SUMMARIES, PERMISSIONS, SYSTEM_ROLES
from service_apps.types import APP_TYPES, clean_config


class PharmacyTypeTests(SimpleTestCase):
    def test_the_pharmacy_is_its_own_type_with_its_own_capabilities(self):
        pharmacy = APP_TYPES["pharmacy"]
        self.assertTrue(pharmacy.capabilities)
        self.assertTrue(all(c.startswith("pharmacy.") for c in pharmacy.capabilities))
        self.assertEqual(pharmacy.open_capability, "pharmacy.view")
        # No reference catalogue in a pharmacy.
        self.assertFalse(any("catalogue" in c for c in pharmacy.capabilities))
        self.assertEqual(settings.SERVICE_APP_DEPLOYMENTS["pharmacy"]["launch_path"], "/apps/pharmacy/")

    def test_defaults_are_eritrean_and_the_config_schema_is_shared(self):
        config = clean_config(APP_TYPES["pharmacy"], {}, {"shopName": "Asmara Pharmacy"})
        self.assertEqual(config["currency"], "ERN")
        self.assertEqual(config["defaultTaxBp"], 0)
        self.assertEqual(config["shopName"], "Asmara Pharmacy")

    def test_staff_roles_hold_only_pharmacy_capabilities(self):
        for slug in ("pharmacy-manager", "pharmacist", "pharmacy-cashier", "pharmacy-accountant"):
            with self.subTest(slug):
                codes = SYSTEM_ROLES[slug][1]
                self.assertTrue(all(c.startswith("pharmacy.") and c in PERMISSIONS for c in codes))
                self.assertIn(slug, ORGANIZATION_ROLE_SUMMARIES)
        # The cashier sees no costs; the accountant changes nothing.
        self.assertNotIn("pharmacy.cost.read", SYSTEM_ROLES["pharmacy-cashier"][1])
        self.assertFalse(any(c.endswith(".manage") for c in SYSTEM_ROLES["pharmacy-accountant"][1]))
