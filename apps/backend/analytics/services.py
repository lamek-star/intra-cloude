"""
Permission checks, audit events, and row/column caps around the
analytics operation registry (operations.py) and dashboards. Running
analysis or viewing a dashboard requires `database.read` on the
underlying table (the same read capability the data explorer already
uses — analysis doesn't expose anything reading the raw rows wouldn't);
creating/editing a dashboard requires `dataset.analyze`, since a saved
dashboard is a persisted artifact, not just a read.
"""

from django.http import Http404

from audit import services as audit
from audit.models import AuditEvent
from databases.models import DBTable, TenantDatabase
from databases.services import get_member_table, get_member_tenant_database
from organizations.models import Membership
from permissions.services import has_permission

from .data import AnalyticsValidationError
from .models import Dashboard
from .operations import OPERATIONS
from .profiling import profile_table

RESOURCE_TYPE_TENANT_DATABASE = "databases.tenant_database"


class AnalyticsPermissionDenied(Exception):
    pass


def _resource(table: DBTable):
    return (RESOURCE_TYPE_TENANT_DATABASE, table.tenant_database_id)


def _require_read(actor, table: DBTable, *, action: str) -> None:
    allowed = has_permission(
        actor, "database.read", organization_id=table.organization_id, resource=_resource(table)
    )
    if not allowed:
        audit.record(
            actor=actor,
            organization_id=table.organization_id,
            action=action,
            resource_type="db_table",
            resource_id=table.id,
            result=AuditEvent.Result.DENIED,
        )
        raise AnalyticsPermissionDenied("database.read required")


def run_analysis(*, actor, table: DBTable, operation: str, params: dict) -> dict:
    _require_read(actor, table, action="analytics.run")

    fn = OPERATIONS.get(operation)
    if fn is None:
        raise AnalyticsValidationError(f"unknown operation: {operation!r}")

    try:
        result = fn(table, params or {})
    except (KeyError, TypeError, ValueError) as exc:
        # Operation functions index required params directly
        # (params["column"], etc.) rather than each hand-rolling its own
        # "is this present and the right shape" checks — a missing or
        # malformed param surfaces as one of these, translated here into
        # the one validation-error type callers/views already handle,
        # rather than leaking as an unhandled 500.
        raise AnalyticsValidationError(f"invalid params for {operation!r}: {exc}") from exc

    audit.record(
        actor=actor,
        organization_id=table.organization_id,
        action="analytics.run",
        resource_type="db_table",
        resource_id=table.id,
        context={"operation": operation, "params": params},
    )
    return result


def run_profile(*, actor, table: DBTable) -> dict:
    _require_read(actor, table, action="analytics.profile")
    result = profile_table(table)
    audit.record(
        actor=actor,
        organization_id=table.organization_id,
        action="analytics.profile",
        resource_type="db_table",
        resource_id=table.id,
    )
    return result


def get_member_dashboard(user, dashboard_id) -> Dashboard:
    try:
        return Dashboard.objects.select_related(
            "tenant_database__project__workspace__organization"
        ).get(
            id=dashboard_id,
            tenant_database__project__workspace__organization__memberships__user=user,
            tenant_database__project__workspace__organization__memberships__status=Membership.Status.ACTIVE,
        )
    except Dashboard.DoesNotExist as exc:
        raise Http404 from exc


def _require_analyze(actor, tenant_database: TenantDatabase, *, action: str) -> None:
    if not has_permission(actor, "dataset.analyze", organization_id=tenant_database.organization_id):
        audit.record(
            actor=actor,
            organization_id=tenant_database.organization_id,
            action=action,
            resource_type="tenant_database",
            resource_id=tenant_database.id,
            result=AuditEvent.Result.DENIED,
        )
        raise AnalyticsPermissionDenied("dataset.analyze required")


def _validate_widgets(tenant_database: TenantDatabase, widgets: list[dict]) -> None:
    for widget in widgets:
        if "table_id" not in widget or "operation" not in widget:
            raise AnalyticsValidationError("each widget needs table_id and operation")
        if widget["operation"] not in OPERATIONS:
            raise AnalyticsValidationError(f"unknown operation: {widget['operation']!r}")
        if not DBTable.objects.filter(id=widget["table_id"], tenant_database=tenant_database).exists():
            raise AnalyticsValidationError(
                f"table {widget['table_id']!r} does not belong to this dashboard's database"
            )


def create_dashboard(*, actor, tenant_database: TenantDatabase, name: str, widgets: list[dict]) -> Dashboard:
    _require_analyze(actor, tenant_database, action="analytics.dashboard.create")
    _validate_widgets(tenant_database, widgets)

    dashboard = Dashboard.objects.create(
        tenant_database=tenant_database, name=name, widgets=widgets, created_by=actor
    )
    audit.record(
        actor=actor,
        organization_id=tenant_database.organization_id,
        action="analytics.dashboard.create",
        resource_type="dashboard",
        resource_id=dashboard.id,
        context={"name": name, "widget_count": len(widgets)},
    )
    return dashboard


def update_dashboard(
    *, actor, dashboard: Dashboard, name: str | None, widgets: list[dict] | None
) -> Dashboard:
    _require_analyze(actor, dashboard.tenant_database, action="analytics.dashboard.update")
    if widgets is not None:
        _validate_widgets(dashboard.tenant_database, widgets)
        dashboard.widgets = widgets
    if name is not None:
        dashboard.name = name
    dashboard.save(update_fields=["name", "widgets", "updated_at"])

    audit.record(
        actor=actor,
        organization_id=dashboard.organization_id,
        action="analytics.dashboard.update",
        resource_type="dashboard",
        resource_id=dashboard.id,
    )
    return dashboard


def delete_dashboard(*, actor, dashboard: Dashboard) -> None:
    _require_analyze(actor, dashboard.tenant_database, action="analytics.dashboard.delete")
    dashboard_id = dashboard.id
    org_id = dashboard.organization_id
    dashboard.delete()
    audit.record(
        actor=actor,
        organization_id=org_id,
        action="analytics.dashboard.delete",
        resource_type="dashboard",
        resource_id=dashboard_id,
    )


def render_dashboard(*, actor, dashboard: Dashboard) -> dict:
    """Re-runs every widget's operation against live data, re-checking
    permissions per widget's underlying table — a dashboard can never
    be used to see data a later-revoked grant should now hide, and a
    widget whose table was deleted or is no longer reachable fails
    individually (reported in its own result) rather than aborting the
    whole dashboard."""
    results = []
    for widget in dashboard.widgets:
        widget_result: dict = {
            "title": widget.get("title", ""),
            "chart_type": widget.get("chart_type", "table"),
        }
        try:
            table = get_member_table(actor, widget["table_id"])
            widget_result["data"] = run_analysis(
                actor=actor, table=table, operation=widget["operation"], params=widget.get("params", {})
            )
        except (Http404, AnalyticsPermissionDenied, AnalyticsValidationError) as exc:
            widget_result["error"] = str(exc)
        results.append(widget_result)

    return {"id": str(dashboard.id), "name": dashboard.name, "widgets": results}


__all__ = [
    "AnalyticsPermissionDenied",
    "AnalyticsValidationError",
    "create_dashboard",
    "delete_dashboard",
    "get_member_dashboard",
    "get_member_table",
    "get_member_tenant_database",
    "render_dashboard",
    "run_analysis",
    "run_profile",
    "update_dashboard",
]
