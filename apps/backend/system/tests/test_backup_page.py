"""The Backups page's API: the Super Administrator only, never a file path, and "Back up now" queues one
backup per type without starting a second one of a type that is still running."""

from unittest.mock import patch

from django.core.management import call_command
from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import User
from audit.models import AuditEvent
from organizations.services import create_organization
from permissions.services import assign_role
from system.models import BackupRecord


class BackupPageTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_permissions", verbosity=0)
        cls.admin = User.objects.create_user(email="backups-super@example.com")
        assign_role(user=cls.admin, role_slug="super-administrator", organization=None)
        cls.owner = User.objects.create_user(email="backups-org-owner@example.com")
        create_organization(
            name="Shop", created_by=cls.owner
        )  # an organization owner, not the platform's admin

    def setUp(self):
        self.client = APIClient()
        BackupRecord.objects.create(
            backup_type=BackupRecord.BackupType.CONTROL_DB,
            status=BackupRecord.Status.SUCCESS,
            file_path="/backups/control/control-2026-11-12.dump",
            size_bytes=1234,
            verified_restorable=True,
        )

    def test_the_super_administrator_sees_the_backups_without_server_paths(self):
        self.client.force_login(self.admin)
        data = self.client.get("/api/v1/system/backups/").data
        row = data["backups"][0]
        self.assertEqual(
            (row["type"], row["file_name"], row["size_bytes"]),
            ("control_db", "control-2026-11-12.dump", 1234),
        )
        self.assertNotIn("file_path", row)
        self.assertTrue(data["latest"]["control_db"]["verified"])
        self.assertIsNone(data["latest"]["tenant_db"]["last_success"])

    def test_an_organization_owner_cannot_see_or_start_backups(self):
        self.client.force_login(self.owner)
        self.assertEqual(self.client.get("/api/v1/system/backups/").status_code, 403)
        self.assertEqual(self.client.post("/api/v1/system/backups/run/", {}, format="json").status_code, 403)

    def test_back_up_now_queues_each_type_once_and_skips_one_still_running(self):
        BackupRecord.objects.create(
            backup_type=BackupRecord.BackupType.TENANT_DB, status=BackupRecord.Status.RUNNING
        )
        self.client.force_login(self.admin)
        with patch("system.tasks.run_backup_task.delay") as delay:
            r = self.client.post("/api/v1/system/backups/run/", {"type": "all"}, format="json")
        self.assertEqual(r.status_code, 202)
        self.assertEqual(r.data["already_running"], ["tenant_db"])
        self.assertEqual(sorted(c.args[0] for c in delay.call_args_list), sorted(r.data["started"]))
        self.assertNotIn("tenant_db", r.data["started"])
        self.assertTrue(AuditEvent.objects.filter(action="system.backup.request").exists())
        bad = self.client.post("/api/v1/system/backups/run/", {"type": "everything"}, format="json")
        self.assertEqual(bad.status_code, 400)
