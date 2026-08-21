"""
Real end-to-end analytics tests: a real tenant table, real inserted
rows, real Postgres queries feeding real numpy/scipy computations
through the live API — not mocked statistics.
"""

from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import User
from organizations.models import Membership
from permissions.management.commands.seed_permissions import Command as SeedPermissionsCommand

# quantity vs amount is designed to correlate strongly (amount ~ 10x
# quantity); channel has exactly 2 groups (t-test); region has 3
# (ANOVA); sale_date gives a real, ordered time series.
# (product, region, channel, quantity, amount, sale_date)
_ROW_TUPLES = [
    ("Widget", "north", "online", 10, "100.00", "2026-01-01"),
    ("Widget", "south", "retail", 20, "210.00", "2026-01-02"),
    ("Gadget", "east", "online", 5, "55.00", "2026-01-03"),
    ("Gadget", "north", "retail", 15, "140.00", "2026-01-04"),
    ("Widget", "south", "online", 8, "95.00", "2026-01-05"),
    ("Gadget", "east", "retail", 25, "245.00", "2026-01-06"),
]
_ROW_FIELDS = ["product", "region", "channel", "quantity", "amount", "sale_date"]
ROWS = [dict(zip(_ROW_FIELDS, values, strict=True)) for values in _ROW_TUPLES]


class AnalyticsTestBase(APITestCase):
    databases = {"default", "tenant"}

    def setUp(self):
        SeedPermissionsCommand().handle()
        self.admin = User.objects.create_user(email="analytics-admin@example.com", password="x")
        self.client.force_login(self.admin)

        org = self.client.post(reverse("organization-list-create"), {"name": "Acme"})
        self.org_id = org.data["id"]
        ws = self.client.post(reverse("workspace-list-create", args=[self.org_id]), {"name": "WS"})
        proj = self.client.post(reverse("project-list-create", args=[ws.data["id"]]), {"name": "Proj"})
        self.project_id = proj.data["id"]

        db = self.client.post(
            reverse("tenant-database-list-create", args=[self.project_id]), {"name": "SalesDB"}
        )
        self.tenant_database_id = db.data["id"]

        table = self.client.post(
            reverse("table-list-create", args=[self.tenant_database_id]), {"name": "sales"}
        )
        self.table_id = table.data["id"]

        for name, data_type, extra in [
            ("product", "text", {}),
            ("region", "text", {}),
            ("channel", "text", {}),
            ("quantity", "integer", {}),
            ("amount", "decimal", {"precision": 10, "scale": 2}),
            ("sale_date", "date", {}),
        ]:
            resp = self.client.post(
                reverse("column-create", args=[self.table_id]),
                {"name": name, "data_type": data_type, **extra},
                format="json",
            )
            self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.data)

        for row in ROWS:
            resp = self.client.post(reverse("row-list-create", args=[self.table_id]), row, format="json")
            self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.data)

    def analyze(self, operation, params=None):
        return self.client.post(
            reverse("table-analyze", args=[self.table_id]),
            {"operation": operation, "params": params or {}},
            format="json",
        )


class DescriptiveStatisticsTests(AnalyticsTestBase):
    def test_count_and_distinct_count(self):
        resp = self.analyze("count", {"column": "product"})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["count"], 6)

        resp = self.analyze("distinct_count", {"column": "product"})
        self.assertEqual(resp.data["distinct_count"], 2)

    def test_sum_mean_median_min_max(self):
        self.assertAlmostEqual(self.analyze("sum", {"column": "quantity"}).data["value"], 83)
        self.assertAlmostEqual(self.analyze("mean", {"column": "quantity"}).data["value"], 83 / 6)
        self.assertEqual(self.analyze("min", {"column": "quantity"}).data["value"], 5)
        self.assertEqual(self.analyze("max", {"column": "quantity"}).data["value"], 25)
        median = self.analyze("median", {"column": "quantity"}).data["value"]
        self.assertEqual(median, 12.5)  # sorted: 5,8,10,15,20,25

    def test_stdev_and_variance_are_consistent(self):
        stdev = self.analyze("stdev", {"column": "quantity"}).data["value"]
        variance = self.analyze("variance", {"column": "quantity"}).data["value"]
        self.assertAlmostEqual(stdev**2, variance, places=6)

    def test_percentiles(self):
        resp = self.analyze("percentiles", {"column": "quantity", "percentiles": [0, 50, 100]})
        self.assertEqual(resp.data["percentiles"]["0"], 5)
        self.assertEqual(resp.data["percentiles"]["100"], 25)

    def test_missing_and_null_percentage(self):
        resp = self.analyze("missing", {"column": "quantity"})
        self.assertEqual(resp.data["missing_count"], 0)
        self.assertEqual(resp.data["null_percentage"], 0.0)

    def test_duplicate_count(self):
        resp = self.analyze("duplicate_count", {"column": "product"})
        # 4 of 6 rows share a product value with at least one other row's
        # product ({Widget: 3 rows, Gadget: 3 rows} -> 6 total, 2 distinct)
        self.assertEqual(resp.data["duplicate_rows"], 4)

    def test_frequency_distribution(self):
        resp = self.analyze("frequency_distribution", {"column": "region"})
        counts = {d["value"]: d["count"] for d in resp.data["distribution"]}
        self.assertEqual(counts, {"north": 2, "south": 2, "east": 2})

    def test_outlier_detection(self):
        resp = self.analyze("outlier_detection", {"column": "quantity"})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn("outlier_count", resp.data)

    def test_wrong_column_type_is_rejected_server_side(self):
        # "product" is text — every numeric operation must reject it,
        # not just rely on a client/UI to only ever send the right type.
        resp = self.analyze("mean", {"column": "product"})
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_unknown_operation_is_rejected(self):
        resp = self.analyze("delete_everything")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_missing_required_param_is_a_clean_400_not_a_500(self):
        resp = self.analyze("mean", {})  # no "column"
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)


class StatisticalAnalysisTests(AnalyticsTestBase):
    def test_pearson_correlation_is_strong_and_positive(self):
        resp = self.analyze("pearson_correlation", {"column_x": "quantity", "column_y": "amount"})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertGreater(resp.data["r"], 0.99)  # amount is ~10x quantity by construction
        self.assertIn("does not establish causation", resp.data["interpretation_note"])

    def test_spearman_correlation(self):
        resp = self.analyze("spearman_correlation", {"column_x": "quantity", "column_y": "amount"})
        self.assertGreater(resp.data["rho"], 0.9)

    def test_linear_regression_recovers_the_known_relationship(self):
        resp = self.analyze("linear_regression", {"column_x": "quantity", "column_y": "amount"})
        self.assertAlmostEqual(resp.data["slope"], 10, delta=1)
        self.assertGreater(resp.data["r_squared"], 0.98)

    def test_t_test_between_two_channel_groups(self):
        resp = self.analyze("t_test", {"column": "quantity", "group_column": "channel"})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(sum(resp.data["sample_sizes"]), 6)
        self.assertIn("Welch", resp.data["method"])

    def test_t_test_rejects_a_group_column_with_wrong_group_count(self):
        # "region" has 3 distinct values, not 2 — a two-sample t-test
        # can't run on it.
        resp = self.analyze("t_test", {"column": "quantity", "group_column": "region"})
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_anova_across_three_regions(self):
        resp = self.analyze("anova", {"column": "amount", "group_column": "region"})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(set(resp.data["groups"]), {"north", "south", "east"})

    def test_chi_square_between_two_categorical_columns(self):
        resp = self.analyze("chi_square", {"column_a": "region", "column_b": "channel"})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn("p_value", resp.data)

    def test_time_series_summary(self):
        resp = self.analyze(
            "time_series_summary", {"date_column": "sale_date", "value_column": "amount", "window": 2}
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data["points"]), 6)
        self.assertEqual(resp.data["points"][0]["date"], "2026-01-01")
        self.assertIsNotNone(resp.data["overall_growth_rate_pct"])


class PermissionTests(AnalyticsTestBase):
    def test_member_without_database_read_cannot_analyze(self):
        member = User.objects.create_user(email="analytics-plain@example.com", password="x")
        Membership.objects.create(user=member, organization_id=self.org_id, status=Membership.Status.ACTIVE)
        self.client.force_login(member)
        resp = self.analyze("mean", {"column": "quantity"})
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_viewer_can_analyze_but_not_create_dashboard(self):
        viewer = User.objects.create_user(email="analytics-viewer@example.com", password="x")
        Membership.objects.create(user=viewer, organization_id=self.org_id, status=Membership.Status.ACTIVE)
        from organizations.models import Organization
        from permissions.services import assign_role

        assign_role(user=viewer, role_slug="viewer", organization=Organization.objects.get(id=self.org_id))

        self.client.force_login(viewer)
        self.assertEqual(self.analyze("mean", {"column": "quantity"}).status_code, status.HTTP_200_OK)

        resp = self.client.post(
            reverse("dashboard-list-create", args=[self.tenant_database_id]),
            {"name": "Sales Overview", "widgets": []},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)


class RowCapTests(AnalyticsTestBase):
    @override_settings(ANALYTICS_MAX_ROWS=3)
    def test_truncation_is_reported_not_silent(self):
        resp = self.analyze("mean", {"column": "quantity"})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(resp.data["truncated"])
        self.assertEqual(resp.data["sample_size"], 3)


class ProfileTests(AnalyticsTestBase):
    def test_profile_reports_every_column(self):
        resp = self.client.get(reverse("table-profile", args=[self.table_id]))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["row_count"], 6)
        # 7, not 6: create_table auto-creates an "id" primary key column
        # on top of the 6 explicitly created here, and profiling a table
        # correctly reports every real column, "id" included.
        self.assertEqual(resp.data["column_count"], 7)
        names = {c["name"] for c in resp.data["columns"]}
        self.assertEqual(names, {"id", "product", "region", "channel", "quantity", "amount", "sale_date"})
        quantity_profile = next(c for c in resp.data["columns"] if c["name"] == "quantity")
        self.assertEqual(quantity_profile["min"], 5)
        self.assertEqual(quantity_profile["max"], 25)


class DashboardTests(AnalyticsTestBase):
    def _widgets(self):
        return [
            {
                "title": "Average order quantity",
                "chart_type": "kpi",
                "table_id": self.table_id,
                "operation": "mean",
                "params": {"column": "quantity"},
            },
            {
                "title": "Sales by region",
                "chart_type": "bar",
                "table_id": self.table_id,
                "operation": "frequency_distribution",
                "params": {"column": "region"},
            },
        ]

    def test_create_and_render_dashboard(self):
        create = self.client.post(
            reverse("dashboard-list-create", args=[self.tenant_database_id]),
            {"name": "Sales Overview", "widgets": self._widgets()},
            format="json",
        )
        self.assertEqual(create.status_code, status.HTTP_201_CREATED)
        dashboard_id = create.data["id"]

        render = self.client.get(reverse("dashboard-render", args=[dashboard_id]))
        self.assertEqual(render.status_code, status.HTTP_200_OK)
        self.assertEqual(len(render.data["widgets"]), 2)
        self.assertNotIn("error", render.data["widgets"][0])
        self.assertAlmostEqual(render.data["widgets"][0]["data"]["value"], 83 / 6)

    def test_dashboard_rejects_a_widget_referencing_an_unknown_table(self):
        import uuid

        widgets = self._widgets()
        widgets[0]["table_id"] = str(uuid.uuid4())
        resp = self.client.post(
            reverse("dashboard-list-create", args=[self.tenant_database_id]),
            {"name": "Bad Dashboard", "widgets": widgets},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_render_reflects_a_permission_revoked_after_creation(self):
        """A dashboard is a saved *reference*, not a cached result — a
        resource grant revoked after creation must be enforced on the
        very next render, not just checked once at creation time
        (Section 25 of the master prompt)."""
        create = self.client.post(
            reverse("dashboard-list-create", args=[self.tenant_database_id]),
            {"name": "Sales Overview", "widgets": self._widgets()},
            format="json",
        )
        dashboard_id = create.data["id"]

        from permissions.services import grant_resource_permission

        member = User.objects.create_user(email="analytics-scoped@example.com", password="x")
        Membership.objects.create(user=member, organization_id=self.org_id, status=Membership.Status.ACTIVE)
        grant = grant_resource_permission(
            user=member,
            permission_code="database.read",
            organization_id=self.org_id,
            resource_type="databases.tenant_database",
            resource_id=self.tenant_database_id,
            granted_by=self.admin,
        )

        self.client.force_login(member)
        while_granted = self.client.get(reverse("dashboard-render", args=[dashboard_id]))
        self.assertEqual(while_granted.status_code, status.HTTP_200_OK)
        self.assertNotIn("error", while_granted.data["widgets"][0])

        grant.delete()
        after_revoke = self.client.get(reverse("dashboard-render", args=[dashboard_id]))
        # The dashboard itself is still viewable (they're an org
        # member), but each widget's *data* must now be blocked —
        # proving the permission is re-checked live, not cached from
        # when the dashboard was created.
        self.assertEqual(after_revoke.status_code, status.HTTP_200_OK)
        self.assertIn("error", after_revoke.data["widgets"][0])

    def test_delete_dashboard(self):
        create = self.client.post(
            reverse("dashboard-list-create", args=[self.tenant_database_id]),
            {"name": "Sales Overview", "widgets": []},
            format="json",
        )
        resp = self.client.delete(reverse("dashboard-detail", args=[create.data["id"]]))
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
