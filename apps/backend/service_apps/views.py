"""Public API: the Apps registry, settings, removal and "Open" (human sessions only)."""

import json
import urllib.error
import urllib.request

from django.conf import settings
from django.http import Http404
from django.utils import timezone
from rest_framework import status
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from . import services, sessions
from .deployments import get_deployment
from .models import ServiceApp
from .types import get_type, public_config

PROBE_TIMEOUT_SECONDS = 2.0


def probe(app: ServiceApp) -> dict:
    """Live readiness of the service, not "a container exists": its own health endpoint must answer
    within the timeout. Combined with the last heartbeat to tell Degraded from Stopped."""
    deployment = get_deployment(app.deployment)
    now = timezone.now()
    if app.removed_at is not None:
        return {"state": "removed", "reachable": False, "checked_at": now.isoformat()}
    if deployment is None:
        return {
            "state": "not_configured",
            "reachable": False,
            "checked_at": now.isoformat(),
            "detail": "This application's service is not part of this installation.",
        }
    if not app.enabled:
        return {"state": "disabled", "reachable": None, "checked_at": now.isoformat()}
    url = f"{deployment.internal_url}{deployment.launch_path}api/v1/health"
    reachable, detail = False, ""
    try:
        with urllib.request.urlopen(url, timeout=PROBE_TIMEOUT_SECONDS) as resp:  # noqa: S310 (fixed internal URL)
            body = json.loads(resp.read(4096) or b"{}")
            reachable = resp.status == 200 and body.get("data", {}).get("status") == "ok"
            detail = body.get("data", {}).get("store", "")
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
        detail = type(exc).__name__
    recent = app.last_seen_at is not None and (now - app.last_seen_at).total_seconds() < 180
    state = "running" if reachable else ("degraded" if recent else "stopped")
    return {
        "state": state,
        "reachable": reachable,
        "checked_at": now.isoformat(),
        "last_seen_at": app.last_seen_at.isoformat() if app.last_seen_at else None,
        "detail": detail,
    }


def represent(user, app: ServiceApp, *, with_health: bool = True) -> dict:
    app_type = get_type(app.app_type)
    deployment = get_deployment(app.deployment)
    can_configure = services.can_configure(user, app)
    return {
        "id": str(app.id),
        "app_type": app.app_type,
        "name": app_type.product_name,
        "display_name": app.display_name,
        "organization": {"id": str(app.organization_id), "name": app.organization.name},
        "version": app.reported_version,
        "enabled": app.enabled,
        "removed": app.removed_at is not None,
        "launch": {
            "path": deployment.launch_path if deployment else None,
            "requires": app_type.open_capability,
        },
        "required_capabilities": list(app_type.capabilities),
        "config": public_config(app_type, app.config) if can_configure else None,
        "health": probe(app) if with_health else None,
        "can_open": services.can_open(user, app),
        "can_configure": can_configure,
        "can_manage": services.can_manage(user, app),
        "created_at": app.created_at.isoformat(),
    }


class _HumanOnly(APIView):
    # Browser sessions only: a bearer credential (applications.ServiceAccount) must never install,
    # configure or open an application on someone's behalf.
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]


class ServiceAppListView(_HumanOnly):
    def get(self, request):
        apps = services.visible_apps(request.user)
        return Response(
            {
                "results": [represent(request.user, a) for a in apps],
                "available": services.installable_deployments(request.user),
            }
        )

    def post(self, request):
        data = request.data if isinstance(request.data, dict) else {}
        app = services.install(
            request.user,
            deployment_key=str(data.get("deployment", "")),
            organization_id=data.get("organization"),
            display_name=str(data.get("display_name", "")),
            config=data.get("config") if isinstance(data.get("config"), dict) else None,
        )
        return Response(represent(request.user, app), status=status.HTTP_201_CREATED)


class ServiceAppDetailView(_HumanOnly):
    def get(self, request, app_id):
        return Response(represent(request.user, services.get_visible_app(request.user, app_id)))

    def patch(self, request, app_id):
        app = services.get_visible_app(request.user, app_id)
        data = request.data if isinstance(request.data, dict) else {}
        app = services.update(
            request.user,
            app,
            display_name=data.get("display_name"),
            config=data.get("config"),
            enabled=data.get("enabled"),
        )
        return Response(represent(request.user, app))

    def delete(self, request, app_id):
        app = services.get_visible_app(request.user, app_id)
        data = request.data if isinstance(request.data, dict) else {}
        result = services.remove(
            request.user,
            app,
            confirm_name=str(data.get("confirm_name", "")),
            delete_data=data.get("delete_data") is True,
        )
        return Response(result)


class ServiceAppRemovalPreviewView(_HumanOnly):
    """What removing would affect (counts only), so the confirmation can say exactly what goes."""

    def get(self, request, app_id):
        from . import provisioning

        app = services.get_visible_app(request.user, app_id)
        if not services.can_manage(request.user, app):
            return Response(status=status.HTTP_403_FORBIDDEN)
        rows = (
            provisioning.schema_summary(app.schema_name, get_type(app.app_type).summary_tables)
            if provisioning.schema_exists(app.schema_name)
            else {}
        )
        return Response(
            {
                "display_name": app.display_name,
                "schema": app.schema_name,
                "rows": rows,
                "files": app.bucket.files.filter(status="active").count(),
                "external_backups_touched": False,
            }
        )


class ServiceAppReinstateView(_HumanOnly):
    def post(self, request, app_id):
        app = services.get_visible_app(request.user, app_id)
        return Response(represent(request.user, services.reinstate(request.user, app)))


class ServiceAppLaunchView(_HumanOnly):
    """ "Open": mints an application session bound to this IntraForge login and sets it as an
    HttpOnly, SameSite=Strict cookie on the application's path. Nothing goes in the URL."""

    def post(self, request, app_id):
        app = services.get_visible_app(request.user, app_id)
        deployment = get_deployment(app.deployment)
        if deployment is None or not services.can_open(request.user, app):
            return Response(status=status.HTTP_403_FORBIDDEN)
        if not request.session.session_key:
            return Response(status=status.HTTP_403_FORBIDDEN)
        token = sessions.mint(app, request.user, request.session.session_key)
        response = Response({"url": deployment.launch_path})
        response.set_cookie(
            sessions.cookie_name(app),
            token,
            max_age=int(settings.SERVICE_APP_SESSION_HOURS) * 3600,
            path=deployment.launch_path,
            secure=settings.SESSION_COOKIE_SECURE,
            httponly=True,
            samesite="Strict",
        )
        return response


class ServiceAppSignInInfoView(APIView):
    """What the sign-in page shows when an application sent someone there ("Sign in to Spare Parts
    -- <shop>"). Public, but only what the application itself already shows before sign-in: its
    product name and shop name. Unknown, disabled or removed instances are a plain 404."""

    authentication_classes: list = []
    permission_classes = [AllowAny]

    def get(self, request, app_id):
        app = ServiceApp.objects.filter(pk=app_id, enabled=True, removed_at__isnull=True).first()
        if app is None or get_deployment(app.deployment) is None:
            raise Http404
        return Response(
            {
                "product_name": get_type(app.app_type).product_name,
                "display_name": (app.config or {}).get("shopName") or app.display_name,
            }
        )
