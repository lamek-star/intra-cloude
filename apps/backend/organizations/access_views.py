"""HTTP layer for access requests (ADR-0026); the rules are in organizations/access.py."""

from django.http import Http404
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from service_apps.models import ServiceApp
from service_apps.deployments import get_deployment
from service_apps.types import get_type
from system import features

from . import access
from .services import get_member_organization


def requestable_app(app_id) -> ServiceApp:
    """An installed, enabled application whose type is switched on -- the same rule as its sign-in page."""
    app = (
        ServiceApp.objects.select_related("organization")
        .filter(pk=app_id, enabled=True, removed_at__isnull=True)
        .first()
    )
    if app is None or get_deployment(app.deployment) is None or not features.app_type_enabled(app.app_type):
        raise Http404
    return app


def base_url(request) -> str:
    return f"{request.scheme}://{request.get_host()}"


def _error(exc: access.AccessError) -> Response:
    return Response({"detail": str(exc)}, status=exc.status)


class AppAccessView(APIView):
    """GET: what an application's Request access page shows (public: only what its sign-in page already shows, plus
    its job names). POST: ask for access -- signed in, for your own account; otherwise as a new person."""

    authentication_classes = [SessionAuthentication]
    permission_classes = [AllowAny]

    def get_throttles(self):
        if self.request.method == "POST":
            self.throttle_scope = "auth"
            return [ScopedRateThrottle()]
        return []

    def get(self, request, app_id):
        app = requestable_app(app_id)
        return Response(
            {
                "product_name": get_type(app.app_type).product_name,
                "display_name": (app.config or {}).get("shopName") or app.display_name,
                "roles": access.requestable_roles(app),
                "accepts_requests": features.may_request_access(),
            }
        )

    def post(self, request, app_id):
        app = requestable_app(app_id)
        data = request.data if isinstance(request.data, dict) else {}
        try:
            if request.user.is_authenticated:
                created = access.request_as_member(user=request.user, app=app, data=data)
                return Response({"detail": access.SAME_ANSWER, "request": access.describe(created)}, status=202)
            return Response({"detail": access.request_as_new_person(app=app, data=data)}, status=202)
        except access.AccessError as exc:
            return _error(exc)


class OrganizationAccessRequestsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, organization_id):
        org = get_member_organization(request.user, organization_id)
        if not access.can_decide(request.user, org):
            return Response(status=403)
        qs = access.for_organization(org, status=request.query_params.get("status"))
        return Response({"results": [access.describe(r) for r in qs[:200]], "email_enabled": _email_enabled()})


class OrganizationAccessRequestDecisionView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, organization_id, request_id, decision):
        org = get_member_organization(request.user, organization_id)
        data = request.data if isinstance(request.data, dict) else {}
        try:
            if decision == "approve":
                result = access.approve(
                    request_id=request_id,
                    organization=org,
                    actor=request.user,
                    role_slug=data.get("role_slug"),
                    note=data.get("note"),
                    base_url=base_url(request),
                )
            elif decision == "reject":
                result = access.reject(
                    request_id=request_id, organization=org, actor=request.user, note=data.get("note")
                )
            elif decision == "link":
                result = access.new_link(
                    request_id=request_id, organization=org, actor=request.user, base_url=base_url(request)
                )
            else:
                raise Http404
        except access.AccessError as exc:
            return _error(exc)
        return Response(result)


def _email_enabled() -> bool:
    from accounts import mail

    return mail.enabled()
