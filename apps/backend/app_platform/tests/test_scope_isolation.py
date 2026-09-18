"""Phase 7 Step 4 ("export/reporting isolation"): proves that a Phase 7
module-scoped or unit-scoped grant -- both narrower than the whole-
database access analytics/exports/imports have always required -- cannot
be used to reach analytics or exports on the underlying tenant database.

This isn't fixing a discovered leak: inspecting every permission check in
analytics/services.py, exports/services.py, and imports/services.py found
that each one either takes no `resource` argument at all (export.manage,
dataset.analyze, dataset.import are role-wide only, never satisfiable by
any ResourceGrant) or checks resource_type="databases.tenant_database"
exclusively -- a namespace Phase 7's own resource_type ("app_model") and
its separate UnitScopedGrant table never intersect with, by construction.
These tests exist to prove that holds against the real running code, not
just the reading of it -- and to catch a regression if it ever stops
holding."""

from django.core.management import call_command
from django.db import connections
from django.test import TransactionTestCase
from django.urls import reverse
from psycopg import sql
from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import User
from app_platform import instances, provisioning, templates
from app_platform.runtime_plan import plan_runtime
from app_platform.tests.test_foundation import project_for
from app_platform.tests.test_org_unit_reference_field import org_unit_reference_sample
from databases.models import DBTable
from org_units.models import OrganizationalUnit
from organizations.models import Membership
from organizations.services import create_organization


class ScopeIsolationTestBase(TransactionTestCase):
    databases = {"default", "tenant"}

    def setUp(self):
        call_command("seed_permissions", verbosity=0)
        self.owner = User.objects.create_user(email="isolation-owner@example.com")
        self.org = create_organization(name="Scope Isolation Org", created_by=self.owner)
        self.project = project_for(self.owner, self.org)
        template = templates.create_template(
            self.owner, self.org, {"label": "App", "draft": org_unit_reference_sample()}
        )
        version = templates.publish_template(self.owner, template)
        self.instance = instances.install(
            self.owner, self.project, {"label": "Runtime", "template_version": str(version.id)}
        )
        self.task = self.instance.models.get(key="task")

        self.plan = plan_runtime(self.owner, self.instance)
        provisioning.reserve(self.owner, self.instance, self.plan["fingerprint"])
        self.receipt = provisioning.execute(self.instance.id, self.owner)
        self.table = DBTable.objects.get(pk=self.receipt.bindings["models"][str(self.task.id)])
        self.tenant_database_id = self.table.tenant_database_id

        self.unit = OrganizationalUnit.objects.create(
            organization=self.org, name="Unit A", unit_type="branch", created_by=self.owner
        )
        self.member = User.objects.create_user(email="isolation-member@example.com")
        Membership.objects.create(user=self.member, organization=self.org, status=Membership.Status.ACTIVE)

        self.owner_client = APIClient()
        self.owner_client.force_authenticate(self.owner)
        self.member_client = APIClient()
        self.member_client.force_authenticate(self.member)

    def tearDown(self):
        with connections["tenant"].cursor() as cursor:
            cursor.execute(
                sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE").format(sql.Identifier(self.plan["schema_name"]))
            )
        super().tearDown()

    def _grant_module_scope(self, level="write"):
        # Sharing (Phase 9) is how module scope is granted -- see
        # sharing/tests/test_sharing.py::AppModelScopeSharingTests.
        resp = self.owner_client.post(
            reverse("share-grant-list-create", args=[self.org.id]),
            {
                "resource_type": "app_model",
                "resource_id": str(self.task.id),
                "principal_type": "user",
                "user_id": str(self.member.id),
                "level": level,
            },
            format="json",
        )
        assert resp.status_code == status.HTTP_201_CREATED, resp.data

    def _grant_unit_scope(self, level="write"):
        resp = self.owner_client.post(
            f"/api/v1/app-models/{self.task.id}/unit-grants/",
            {"user_id": str(self.member.id), "unit_id": str(self.unit.id), "level": level},
            format="json",
        )
        assert resp.status_code == status.HTTP_201_CREATED, resp.data


class ModuleScopeDoesNotReachAnalyticsOrExports(ScopeIsolationTestBase):
    def setUp(self):
        super().setUp()
        self._grant_module_scope()

    def test_module_scope_still_grants_record_access(self):
        # Sanity check the grant is real before proving it doesn't reach
        # further than it should.
        resp = self.member_client.get(f"/api/v1/app-models/{self.task.id}/records/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_module_scope_does_not_grant_table_analysis(self):
        resp = self.member_client.post(
            reverse("table-analyze", args=[self.table.id]),
            {"operation": "count", "params": {}},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_module_scope_does_not_grant_dashboard_creation(self):
        resp = self.member_client.post(
            reverse("dashboard-list-create", args=[self.tenant_database_id]),
            {"name": "Leak check", "widgets": []},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_module_scope_does_not_grant_org_export(self):
        resp = self.member_client.post(
            reverse("export-job-list-create", args=[self.org.id]), {}, format="json"
        )
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_module_scope_does_not_grant_csv_row_export(self):
        resp = self.member_client.get(reverse("row-export", args=[self.table.id]))
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)


class UnitScopeDoesNotReachAnalyticsOrExports(ScopeIsolationTestBase):
    def setUp(self):
        super().setUp()
        self._grant_unit_scope()

    def test_unit_scope_does_not_grant_table_analysis(self):
        resp = self.member_client.post(
            reverse("table-analyze", args=[self.table.id]),
            {"operation": "count", "params": {}},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_unit_scope_does_not_grant_dashboard_creation(self):
        resp = self.member_client.post(
            reverse("dashboard-list-create", args=[self.tenant_database_id]),
            {"name": "Leak check", "widgets": []},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_unit_scope_does_not_grant_org_export(self):
        resp = self.member_client.post(
            reverse("export-job-list-create", args=[self.org.id]), {}, format="json"
        )
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_unit_scope_does_not_grant_csv_row_export(self):
        resp = self.member_client.get(reverse("row-export", args=[self.table.id]))
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)
