from django.urls import reverse
from rest_framework.test import APITestCase

from accounts.models import User
from audit.models import AuditEvent
from permissions.management.commands.seed_permissions import Command as SeedPermissionsCommand


class SchemaChangeAuditTests(APITestCase):
    """Section 9 of the master prompt requires every schema modification
    to end with an audit event; Section 18 lists database/table creation
    as an explicitly auditable action."""

    databases = {"default", "tenant"}

    def setUp(self):
        SeedPermissionsCommand().handle()
        self.admin = User.objects.create_user(email="audit-db@example.com", password="x")
        self.client.force_login(self.admin)
        org = self.client.post(reverse("organization-list-create"), {"name": "Acme"})
        self.org_id = org.data["id"]
        ws = self.client.post(reverse("workspace-list-create", args=[self.org_id]), {"name": "WS"})
        proj = self.client.post(reverse("project-list-create", args=[ws.data["id"]]), {"name": "Proj"})
        self.project_id = proj.data["id"]

    def test_creating_a_database_and_table_is_audited(self):
        db = self.client.post(
            reverse("tenant-database-list-create", args=[self.project_id]), {"name": "AppDB"}
        )
        db_id = db.data["id"]
        self.client.post(reverse("table-list-create", args=[db_id]), {"name": "customers"})

        actions = list(
            AuditEvent.objects.filter(organization_id=self.org_id).values_list("action", flat=True)
        )
        self.assertIn("database.create", actions)
        self.assertIn("database.table.create", actions)

    def test_audit_events_are_visible_via_the_api(self):
        self.client.post(reverse("tenant-database-list-create", args=[self.project_id]), {"name": "AppDB"})

        response = self.client.get(reverse("audit-event-list", args=[self.org_id]))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(any(e["action"] == "database.create" for e in response.data["results"]))

    def test_audit_events_can_be_filtered_by_action(self):
        self.client.post(reverse("tenant-database-list-create", args=[self.project_id]), {"name": "AppDB"})
        self.client.post(reverse("tenant-database-list-create", args=[self.project_id]), {"name": "OtherDB"})

        response = self.client.get(
            reverse("audit-event-list", args=[self.org_id]), {"action": "database.create"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 2)
        self.assertTrue(all(e["action"] == "database.create" for e in response.data["results"]))

        empty = self.client.get(
            reverse("audit-event-list", args=[self.org_id]), {"action": "no.such.action"}
        )
        self.assertEqual(empty.data["count"], 0)

    def test_denied_schema_change_is_audited_as_denied(self):
        member = User.objects.create_user(email="plain-audit@example.com", password="x")
        from organizations.models import Membership

        Membership.objects.create(
            user=member, organization_id=self.org_id, status=Membership.Status.ACTIVE
        )
        self.client.force_login(member)
        self.client.post(reverse("tenant-database-list-create", args=[self.project_id]), {"name": "Nope"})

        denied = AuditEvent.objects.filter(
            organization_id=self.org_id, action="database.create", result=AuditEvent.Result.DENIED
        )
        self.assertTrue(denied.exists())
