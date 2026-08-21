import uuid

from django.conf import settings
from django.db import models


class Dashboard(models.Model):
    """A saved arrangement of analytics widgets (Section 25 of the
    master prompt). Widgets are stored as declarative JSON — {table_id,
    operation, params, chart_type, title, position} — never a saved raw
    query, so `views.py`'s render endpoint can re-validate every
    widget's permissions and re-run its operation against live data
    every time it's viewed, rather than trusting a cached result a
    later-revoked grant should have invalidated."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant_database = models.ForeignKey(
        "databases.TenantDatabase", on_delete=models.CASCADE, related_name="dashboards"
    )
    name = models.CharField(max_length=200)
    widgets = models.JSONField(default=list, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="dashboards_created"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["tenant_database", "name"], name="unique_dashboard_name_per_database"
            ),
        ]
        ordering = ["name"]

    def __str__(self):
        return self.name

    @property
    def organization_id(self):
        return self.tenant_database.organization_id
