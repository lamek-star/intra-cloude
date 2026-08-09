import logging

from django.conf import settings
from django.db import connections
from django.db.utils import OperationalError
from django.http import HttpResponse
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

logger = logging.getLogger(__name__)


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

    return checks, healthy


class HealthzView(APIView):
    """Liveness: process is up and can respond. No dependency checks —
    used by the container runtime/orchestrator to know whether to restart
    the process, not whether it's ready to serve real traffic."""

    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        return Response({"status": "ok"})


class ReadyzView(APIView):
    """Readiness: checks the dependencies a request would actually need
    (control-plane DB, tenant DB connection, Valkey) before the process is
    considered ready to receive traffic (docs/architecture/ARCHITECTURE.md
    Section 9)."""

    permission_classes = [AllowAny]
    authentication_classes = []

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
    authentication_classes = []

    def get(self, request):
        checks, _ = _dependency_checks()
        lines = [
            "# HELP pdc_dependency_up Whether a backend dependency is reachable (1) or not (0).",
            "# TYPE pdc_dependency_up gauge",
        ]
        for name, up in checks.items():
            lines.append(f'pdc_dependency_up{{dependency="{name}"}} {1 if up else 0}')

        return HttpResponse(
            "\n".join(lines) + "\n", content_type="text/plain; version=0.0.4; charset=utf-8"
        )
