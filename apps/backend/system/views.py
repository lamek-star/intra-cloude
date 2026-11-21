import logging

from django.conf import settings
from django.db import connections
from django.db.utils import OperationalError
from django.http import HttpResponse
from rest_framework.authentication import BaseAuthentication, SessionAuthentication
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

logger = logging.getLogger(__name__)


class FeaturesView(APIView):
    """Which feature groups are on (system/features.py). Any signed-in person may read it (the web app hides what
    is off); only the Super Administrator (system.admin, platform-wide) may change it. Browser sessions only."""

    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from permissions.services import has_permission

        from . import features

        can_change = has_permission(request.user, "system.admin", organization_id=None)
        return Response({**features.describe(), "can_change": can_change})

    def patch(self, request):
        from permissions.services import has_permission

        from . import features

        if not has_permission(request.user, "system.admin", organization_id=None):
            return Response(
                {"error": {"code": "permission_denied", "message": "Only the Super Administrator can change this."}},
                status=403,
            )
        enabled = request.data.get("enabled") if isinstance(request.data, dict) else None
        if not isinstance(enabled, list) or not all(isinstance(g, str) for g in enabled):
            return Response(
                {"error": {"code": "invalid", "message": "Send the list of feature groups to keep on."}},
                status=400,
            )
        try:
            return Response({**features.set_enabled(request.user, enabled), "can_change": True})
        except ValueError as exc:
            return Response({"error": {"code": "invalid", "message": str(exc)}}, status=400)


def _dependency_checks() -> tuple[dict[str, bool], bool]:
    """Shared by /readyz and /metrics so the two never drift — one is the
    human/orchestrator-facing view of exactly the same checks the other
    exposes as Prometheus gauges."""
    checks: dict[str, bool] = {}
    healthy = True

    for alias in ("default", "tenant"):
        try:
            connections[alias].cursor().execute("SELECT 1")
            checks[f"database:{alias}"] = True
        except OperationalError as exc:
            healthy = False
            checks[f"database:{alias}"] = False
            logger.warning("Dependency check failed for database %s: %s", alias, exc)

    try:
        import redis

        redis.from_url(settings.CELERY_BROKER_URL, socket_connect_timeout=2).ping()
        checks["valkey"] = True
    except Exception as exc:  # noqa: BLE001 - a dependency check must not crash the process
        healthy = False
        checks["valkey"] = False
        logger.warning("Dependency check failed for valkey: %s", exc)

    # Every upload, download and backup of files goes through object storage; without this check
    # the dashboard reported "all checks passing" while files could not be read.
    try:
        from storage.backends import check_object_storage

        check_object_storage()
        checks["object_storage"] = True
    except Exception as exc:  # noqa: BLE001 - a dependency check must not crash the process
        healthy = False
        checks["object_storage"] = False
        logger.warning("Dependency check failed for object storage: %s", exc)

    return checks, healthy


class HealthzView(APIView):
    """Liveness: process is up and can respond. No dependency checks —
    used by the container runtime/orchestrator to know whether to restart
    the process, not whether it's ready to serve real traffic."""

    permission_classes = [AllowAny]
    authentication_classes: list[type[BaseAuthentication]] = []

    def get(self, request):
        return Response({"status": "ok"})


class ReadyzView(APIView):
    """Readiness: checks the dependencies a request would actually need
    (control-plane DB, tenant DB connection, Valkey) before the process is
    considered ready to receive traffic (docs/architecture/ARCHITECTURE.md
    Section 9)."""

    permission_classes = [AllowAny]
    authentication_classes: list[type[BaseAuthentication]] = []

    def get(self, request):
        checks, healthy = _dependency_checks()
        body_checks = {name: ("ok" if up else "unreachable") for name, up in checks.items()}
        status_code = 200 if healthy else 503
        return Response(
            {"status": "ok" if healthy else "unavailable", "checks": body_checks}, status=status_code
        )


class MetricsView(APIView):
    """Prometheus exposition format (Phase 11; docs/architecture/ROADMAP.md).
    Exposes dependency-up gauges computed at scrape time from the same
    checks /readyz runs. Deliberately does not expose request-count/
    latency histograms — those need a registry shared across gunicorn's
    multiple worker processes (e.g. django-prometheus's multiprocess
    mode), which this deployment doesn't have; documented as an Open Item
    rather than silently omitted."""

    permission_classes = [AllowAny]
    authentication_classes: list[type[BaseAuthentication]] = []

    def get(self, request):
        checks, _ = _dependency_checks()
        lines = [
            "# HELP pdc_dependency_up Whether a backend dependency is reachable (1) or not (0).",
            "# TYPE pdc_dependency_up gauge",
        ]
        for name, up in checks.items():
            lines.append(f'pdc_dependency_up{{dependency="{name}"}} {1 if up else 0}')

        return HttpResponse("\n".join(lines) + "\n", content_type="text/plain; version=0.0.4; charset=utf-8")


class VersionView(APIView):
    """The installed IntraForge version (the repo-root VERSION file, as the portable export records
    it), for the web app's footer and welcome tour. Signed-in callers only: an anonymous caller is
    never told the version."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        from exports.manifest import PRODUCT_VERSION

        return Response({"version": PRODUCT_VERSION})
