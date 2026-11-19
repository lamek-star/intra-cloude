"""Organization-wide views of what applications did with their credentials, built only from ApiRequestLog
(method, path, status, duration, time -- never a query string, body or header). Used by the Developer section's
API Logs and Usage tabs. The caller checks membership and application.read first."""

from datetime import timedelta

from django.conf import settings
from django.db.models import Avg, Count, Max, Q
from django.db.models.functions import TruncDate
from django.utils import timezone

from .models import ApiRequestLog, Application

MAX_USAGE_DAYS = 30
METHODS = {"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"}


def org_request_log(organization_id, *, application_id=None, errors_only=False, method=None):
    """Every application's requests in one organization, newest first (a queryset to paginate)."""
    qs = ApiRequestLog.objects.filter(application__organization_id=organization_id).select_related("application")
    if application_id is not None:
        qs = qs.filter(application_id=application_id)
    if errors_only:
        qs = qs.filter(status__gte=400)
    if method in METHODS:
        qs = qs.filter(method=method)
    return qs


def request_row(r: ApiRequestLog) -> dict:
    return {
        "id": r.id,
        "application": str(r.application_id),
        "application_name": r.application.name,
        "method": r.method,
        "path": r.path,
        "status": r.status,
        "duration_ms": r.duration_ms,
        "at": r.at.isoformat(),
        "credential": str(r.credential_id) if r.credential_id else None,
    }


def clamp_days(raw) -> int:
    """1..min(30, the log's retention): asking for more than is kept would show a false drop to zero."""
    try:
        days = int(raw)
    except (TypeError, ValueError):
        days = 7
    return max(1, min(days, MAX_USAGE_DAYS, settings.API_REQUEST_LOG_DAYS))


def org_usage(organization_id, days: int, now=None) -> dict:
    """Per application and per day over the last `days` days: requests, errors (status >= 400), average and
    slowest duration, last request. Every application of the organization is listed, also with no requests."""
    now = now or timezone.now()
    since = now - timedelta(days=days)
    window = ApiRequestLog.objects.filter(application__organization_id=organization_id, at__gte=since)
    errors = Count("id", filter=Q(status__gte=400))
    per_app = {
        row["application_id"]: row
        for row in window.values("application_id").annotate(
            requests=Count("id"), errors=errors, avg_ms=Avg("duration_ms"), max_ms=Max("duration_ms"), last_at=Max("at")
        )
    }
    applications = []
    for app in Application.objects.filter(organization_id=organization_id).order_by("name"):
        row = per_app.get(app.id, {})
        applications.append(
            {
                "id": str(app.id),
                "name": app.name,
                "requests": row.get("requests", 0),
                "errors": row.get("errors", 0),
                "avg_ms": round(row["avg_ms"]) if row.get("avg_ms") is not None else None,
                "max_ms": row.get("max_ms"),
                "last_at": row["last_at"].isoformat() if row.get("last_at") else None,
            }
        )
    daily = [
        {"date": row["day"].isoformat(), "requests": row["requests"], "errors": row["errors"]}
        for row in window.annotate(day=TruncDate("at"))
        .values("day")
        .annotate(requests=Count("id"), errors=errors)
        .order_by("day")
    ]
    return {
        "days": days,
        "since": since.isoformat(),
        "retention_days": settings.API_REQUEST_LOG_DAYS,
        "totals": {
            "requests": sum(a["requests"] for a in applications),
            "errors": sum(a["errors"] for a in applications),
        },
        "applications": applications,
        "daily": daily,
    }
