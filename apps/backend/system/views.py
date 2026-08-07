import logging

from django.conf import settings
from django.db import connections
from django.db.utils import OperationalError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

logger = logging.getLogger(__name__)


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
        checks = {}
        healthy = True

        for alias in ("default", "tenant"):
            try:
                connections[alias].cursor().execute("SELECT 1")
                checks[f"database:{alias}"] = "ok"
            except OperationalError as exc:
                healthy = False
                checks[f"database:{alias}"] = "unreachable"
                logger.warning("Readiness check failed for database %s: %s", alias, exc)

        try:
            import redis

            redis.from_url(settings.CELERY_BROKER_URL, socket_connect_timeout=2).ping()
            checks["valkey"] = "ok"
        except Exception as exc:  # noqa: BLE001 - readiness check must not crash the process
            healthy = False
            checks["valkey"] = "unreachable"
            logger.warning("Readiness check failed for valkey: %s", exc)

        status_code = 200 if healthy else 503
        return Response({"status": "ok" if healthy else "unavailable", "checks": checks}, status=status_code)
