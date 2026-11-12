"""Health history and alerts: samples every 5 minutes, an alert after two failures in a row that closes when
the check passes, a "background jobs stopped" alert when no sample came, and the Super Administrator only."""

from datetime import timedelta
from unittest.mock import patch

from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import User
from organizations.services import create_organization
from permissions.services import assign_role
from system import health
from system.models import BackupRecord, HealthAlert, HealthSample

ALL_UP = {"database:default": True, "database:tenant": True, "valkey": True, "object_storage": True}


def fake_deps(**down):
    checks = {**ALL_UP, **{k.replace("__", ":"): False for k in down}}
    return lambda: (checks, all(checks.values()))


class HealthHistoryTests(TestCase):
    def setUp(self):
        BackupRecord.objects.create(
            backup_type=BackupRecord.BackupType.CONTROL_DB,
            status=BackupRecord.Status.SUCCESS,
            completed_at=timezone.now(),
        )

    def take(self, at, **down):
        with patch("system.views._dependency_checks", fake_deps(**down)):
            return health.record(now=at)

    def test_two_failures_in_a_row_open_an_alert_and_a_pass_closes_it(self):
        t = timezone.now()
        self.take(t - timedelta(minutes=10), valkey=True)
        self.assertFalse(HealthAlert.objects.exists())  # one failure is not yet an alert
        self.take(t - timedelta(minutes=5), valkey=True)
        alert = HealthAlert.objects.get()
        self.assertEqual((alert.check_name, alert.closed_at), ("valkey", None))
        self.take(t)
        alert.refresh_from_db()
        self.assertIsNotNone(alert.closed_at)
        data = health.summary(now=t)
        self.assertEqual(data["open_alerts"], 0)
        self.assertEqual({c["check"] for c in data["latest"]["checks"]} >= set(ALL_UP), True)
        [valkey] = [h for h in data["hours"] if h["check"] == "valkey"]
        self.assertEqual(sum(h["failed"] for h in valkey["hours"]), 2)

    def test_an_old_backup_is_a_failing_check_and_samples_are_pruned(self):
        BackupRecord.objects.update(completed_at=timezone.now() - timedelta(days=3))
        sample = self.take(timezone.now())
        self.assertFalse(sample.checks["backups"])
        HealthSample.objects.create(at=timezone.now() - timedelta(days=30), checks={})
        self.take(timezone.now())
        self.assertFalse(HealthSample.objects.filter(at__lt=timezone.now() - timedelta(days=15)).exists())

    def test_no_recent_sample_means_the_background_jobs_stopped(self):
        self.take(timezone.now() - timedelta(hours=1))
        data = health.summary()
        self.assertEqual(data["alerts"][0]["check"], "jobs")
        self.assertEqual(data["open_alerts"], 1)


class HealthPageAccessTests(TestCase):
    def test_the_super_administrator_only(self):
        call_command("seed_permissions", verbosity=0)
        admin = User.objects.create_user(email="health-admin@example.com")
        assign_role(user=admin, role_slug="super-administrator", organization=None)
        owner = User.objects.create_user(email="health-owner@example.com")
        create_organization(name="Shop", created_by=owner)
        client = APIClient()
        client.force_login(owner)
        self.assertEqual(client.get("/api/v1/system/health/").status_code, 403)
        client.force_login(admin)
        self.assertEqual(client.get("/api/v1/system/health/").status_code, 200)
