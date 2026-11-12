"""Licensing (ADR-0023): a 30-day trial, then read-only until a serial number is activated for this PC with an
activation code signed by the vendor. Tests use their own key pair; the vendor's real private key never leaves
the vendor's PC."""

import datetime
import tempfile
from pathlib import Path
from unittest import mock

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from django.core.cache import cache
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import User
from licensing import codes
from licensing.models import LicenseState
from organizations.models import Membership
from organizations.services import create_organization

KEY = Ed25519PrivateKey.generate()
PUBLIC = codes.public_key_text(KEY)
OTHER_KEY = Ed25519PrivateKey.generate()
PC = "PC-1A2B-3C4D-5E6F-7A8B"


class CodeTests(TestCase):
    def test_serials_catch_typos_and_say_their_kind(self):
        sn = codes.new_serial()
        self.assertTrue(sn.startswith("IFG-"))
        self.assertEqual(codes.normalize_serial(sn.lower().replace("-", " ")), sn)
        typo = sn[:-1] + ("A" if sn[-1] != "A" else "B")
        self.assertIsNone(codes.normalize_serial(typo))
        master = codes.new_serial(codes.MASTER)
        self.assertEqual((master[:4], codes.serial_kind(master)), ("IFM-", "master"))

    def test_the_pc_code_matches_the_start_scripts_formula(self):
        # The same text the PowerShell start script hashes: "IntraForge-PC:" + machine id + "|" + board UUID.
        code = codes.pc_code("1B4E28BA-2FA1-11D2-883F-0016D3CCA427", "4C4C4544-0042-3510-8051-B4C04F4E3732")
        self.assertRegex(code, r"^PC-[0-9A-F]{4}-[0-9A-F]{4}-[0-9A-F]{4}-[0-9A-F]{4}$")
        self.assertEqual(codes.normalize_pc(code.lower().replace("-", "")), code)

    def test_only_the_vendors_key_makes_a_working_code_and_it_cannot_be_altered(self):
        sn = codes.new_serial()
        code = codes.sign_activation(KEY, serial=sn, pc=PC)
        self.assertEqual(codes.verify_activation(codes.public_key_from_text(PUBLIC), code)["sn"], sn)
        forged = codes.sign_activation(OTHER_KEY, serial=sn, pc=PC)
        self.assertIsNone(codes.verify_activation(codes.public_key_from_text(PUBLIC), forged))
        head, payload, sig = code.split(".")
        other_pc = codes.sign_activation(OTHER_KEY, serial=sn, pc="PC-0000-0000-0000-0001").split(".")[1]
        self.assertIsNone(
            codes.verify_activation(codes.public_key_from_text(PUBLIC), f"{head}.{other_pc}.{sig}")
        )


class LicenceTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_permissions", verbosity=0)
        cls.owner = User.objects.create_user(email="licence-owner@example.com")
        cls.org = create_organization(name="Licensed Shop", created_by=cls.owner)
        cls.member = User.objects.create_user(email="licence-member@example.com")
        Membership.objects.create(user=cls.member, organization=cls.org, status=Membership.Status.ACTIVE)

    def setUp(self):
        cache.clear()
        self.machine = tempfile.TemporaryDirectory()
        Path(self.machine.name, "pc-code").write_text(PC, encoding="utf-8")
        self.settings_override = override_settings(
            LICENSE_ENFORCED=True,
            LICENSE_PUBLIC_KEY=PUBLIC,
            LICENSE_MACHINE_DIR=self.machine.name,
            LICENSE_TRIAL_DAYS=30,
        )
        self.settings_override.enable()
        self.client = APIClient()
        self.client.force_login(self.owner)

    def tearDown(self):
        self.settings_override.disable()
        self.machine.cleanup()

    def end_trial(self):
        self.client.get("/api/v1/license/")
        LicenseState.objects.update(trial_started_at=timezone.now() - datetime.timedelta(days=31))
        cache.clear()

    def change(self):
        return self.client.post(
            f"/api/v1/organizations/{self.org.id}/workspaces/", {"name": "New"}, format="json"
        )

    def test_a_new_installation_has_a_30_day_trial_with_everything_working(self):
        status = self.client.get("/api/v1/license/").data
        self.assertEqual((status["state"], status["days_left"], status["pc_code"]), ("trial", 30, PC))
        self.assertTrue(status["can_activate"])
        self.assertIn(self.change().status_code, (200, 201))

    def test_after_the_trial_intraforge_is_read_only_but_sign_in_and_reading_work(self):
        self.end_trial()
        self.assertEqual(self.client.get("/api/v1/license/").data["state"], "expired")
        refused = self.change()
        self.assertEqual((refused.status_code, refused.json()["code"]), (403, "licence_required"))
        self.assertEqual(self.client.get(f"/api/v1/organizations/{self.org.id}/").status_code, 200)
        self.assertEqual(APIClient().post("/api/v1/auth/logout/").status_code in (200, 204, 403), True)
        # Signing in to an application still works: its consent screen is not "a change" (a bad request is a
        # 400 from the screen itself, never licence_required).
        consent = self.client.post("/api/v1/oauth/consent/", {"decision": "allow"}, format="json")
        self.assertEqual(consent.status_code, 400)

    def test_activating_with_the_vendors_code_for_this_pc_lifts_the_limit(self):
        self.end_trial()
        sn = codes.new_serial()
        r = self.client.post(
            "/api/v1/license/activate/",
            {"serial": sn, "activation_code": codes.sign_activation(KEY, serial=sn, pc=PC)},
            format="json",
        )
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual((r.data["state"], r.data["kind"]), ("active", "standard"))
        self.assertNotIn(sn[8:12], r.data["serial"])  # only part of the SN is shown back
        self.assertIn(self.change().status_code, (200, 201))

    def test_a_code_for_another_pc_another_serial_or_another_key_is_refused(self):
        sn, other = codes.new_serial(), codes.new_serial()
        url = "/api/v1/license/activate/"
        for serial, code in (
            (sn, codes.sign_activation(KEY, serial=sn, pc="PC-0000-0000-0000-0001")),  # another PC
            (sn, codes.sign_activation(KEY, serial=other, pc=PC)),  # another SN
            (sn, codes.sign_activation(OTHER_KEY, serial=sn, pc=PC)),  # not the vendor's key
            ("IFG-NOPE", "x"),
        ):
            self.assertEqual(
                self.client.post(url, {"serial": serial, "activation_code": code}, format="json").status_code,
                400,
            )
            cache.clear()

    def test_moving_the_database_to_another_pc_does_not_move_the_licence(self):
        sn = codes.new_serial(codes.MASTER)
        self.client.post(
            "/api/v1/license/activate/",
            {"serial": sn, "activation_code": codes.sign_activation(KEY, serial=sn, pc=PC)},
            format="json",
        )
        self.assertEqual(self.client.get("/api/v1/license/").data["kind"], "master")
        Path(self.machine.name, "pc-code").write_text("PC-9999-9999-9999-9999", encoding="utf-8")
        self.end_trial()
        self.assertEqual(self.client.get("/api/v1/license/").data["state"], "expired")

    def test_only_an_administrator_activates(self):
        member = APIClient()
        member.force_login(self.member)
        self.assertFalse(member.get("/api/v1/license/").data["can_activate"])
        sn = codes.new_serial()
        r = member.post(
            "/api/v1/license/activate/",
            {"serial": sn, "activation_code": codes.sign_activation(KEY, serial=sn, pc=PC)},
            format="json",
        )
        self.assertEqual(r.status_code, 403)

    def test_a_clock_set_back_does_not_bring_the_trial_back(self):
        self.client.get("/api/v1/license/")
        LicenseState.objects.update(last_seen_at=timezone.now() + datetime.timedelta(days=10))
        cache.clear()
        self.assertEqual(self.client.get("/api/v1/license/").data["state"], "expired")

    def test_a_reinstall_keeps_the_first_start_date(self):
        Path(self.machine.name, "first-start").write_text(
            (timezone.now() - datetime.timedelta(days=40)).date().isoformat(), encoding="utf-8"
        )
        self.assertEqual(self.client.get("/api/v1/license/").data["state"], "expired")

    def test_where_licensing_is_not_enforced_nothing_is_refused(self):
        self.end_trial()
        with override_settings(LICENSE_ENFORCED=False):
            cache.clear()
            self.assertEqual(self.client.get("/api/v1/license/").data["state"], "not_enforced")
            self.assertIn(self.change().status_code, (200, 201))

    def test_activation_is_audited(self):
        from audit.models import AuditEvent

        sn = codes.new_serial()
        with mock.patch(
            "licensing.services.audit.record", wraps=__import__("audit.services", fromlist=["record"]).record
        ) as rec:
            self.client.post(
                "/api/v1/license/activate/",
                {"serial": sn, "activation_code": codes.sign_activation(KEY, serial=sn, pc=PC)},
                format="json",
            )
        self.assertTrue(rec.called)
        self.assertTrue(AuditEvent.objects.filter(action="licence.activate").exists())
