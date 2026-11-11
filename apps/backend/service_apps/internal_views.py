"""Internal API for service applications (ADR-0018). Reachable only on the internal network (the
proxy refuses /api/v1/internal/), authenticated with the deployment's service token, and scoped to
that deployment's own instance: there is no way to name another instance."""

from django.http import FileResponse
from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.parsers import JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from audit import services as audit

from . import pay_bridge, services, sessions
from .authentication import IsServicePrincipal, ServiceTokenAuthentication
from .models import ServiceApp
from .types import get_type


class _Internal(APIView):
    authentication_classes = [ServiceTokenAuthentication]
    permission_classes = [IsServicePrincipal]
    # Called on nearly every request the service serves; authenticated with a 256-bit secret and
    # unreachable from outside the Docker network, so the per-client throttles do not apply.
    throttle_classes: list = []

    def instance(self, request, *, allow_missing=False) -> ServiceApp | None:
        deployment = request.user.deployment
        app = (
            ServiceApp.objects.select_related("organization")
            .filter(deployment=deployment.key, removed_at__isnull=True)
            .first()
        )
        if app is None and not allow_missing:
            raise NotFound("The application is not installed.")
        return app


class InternalSelfView(_Internal):
    def get(self, request):
        deployment = request.user.deployment
        app = self.instance(request, allow_missing=True)
        if app is None:
            return Response(
                {
                    "installed": False,
                    "deployment": deployment.key,
                    "app_type": deployment.app_type.key,
                    "launch_path": deployment.launch_path,
                }
            )
        return Response(
            {
                "installed": True,
                "enabled": app.enabled,
                "deployment": deployment.key,
                "app_type": app.app_type,
                "launch_path": deployment.launch_path,
                "app": {
                    "id": str(app.id),
                    "display_name": app.display_name,
                    "organization": {"id": str(app.organization_id), "name": app.organization.name},
                },
                "database": {"schema": app.schema_name, "role": deployment.db_role},
                "config": services.config_for_service(app),
                "capabilities": list(get_type(app.app_type).capabilities),
            }
        )


class InternalHeartbeatView(_Internal):
    def post(self, request):
        app = self.instance(request)
        services.heartbeat(app, version=str(request.data.get("version", "")))
        return Response({"ok": True, "enabled": app.enabled})


class InternalIntrospectView(_Internal):
    def post(self, request):
        app = self.instance(request)
        result = sessions.introspect(app, str(request.data.get("token", "")))
        if result is None:
            return Response({"active": False}, status=status.HTTP_401_UNAUTHORIZED)
        return Response(
            {
                "active": True,
                "user": {"id": result.user_id, "email": result.email, "displayName": result.display_name},
                "capabilities": result.capabilities,
                "csrfToken": result.csrf_token,
                "expiresAt": result.expires_at,
                "sessionId": str(result.session_id),
            }
        )


class InternalRevokeView(_Internal):
    def post(self, request):
        app = self.instance(request)
        token = str(request.data.get("token", ""))
        if request.data.get("sign_out") is True:
            user = sessions.sign_out(app, token)
            if user is not None:
                audit.record(
                    actor=user,
                    organization_id=app.organization_id,
                    action="auth.logout",
                    context={"via": "service_app", "service_app": str(app.id)},
                )
        else:
            sessions.revoke(app, token)
        return Response({"ok": True})


class InternalUsersView(_Internal):
    def get(self, request):
        return Response({"results": services.application_users(self.instance(request))})


class InternalAuditView(_Internal):
    def post(self, request):
        app = self.instance(request)
        accepted = services.ingest_audit(app, request.data.get("events"))
        return Response({"accepted": accepted})


class InternalConfigView(_Internal):
    def get(self, request):
        return Response(services.config_for_service(self.instance(request)))

    def patch(self, request):
        app = self.instance(request)
        patch = request.data.get("patch")
        return Response(services.update_config_for_actor(app, request.data.get("actorId"), patch or {}))


class InternalFilesView(_Internal):
    parser_classes = [MultiPartParser]

    def post(self, request):
        app = self.instance(request)
        file_obj = services.store_file(
            app,
            uploaded_file=request.FILES.get("file"),
            kind=str(request.data.get("kind", "")),
            actor_id=request.data.get("actorId"),
        )
        return Response(
            {
                "id": str(file_obj.id),
                "size": file_obj.size,
                "sha256": file_obj.checksum_sha256,
                "mime": file_obj.mime_type,
                "quarantined": file_obj.status == file_obj.Status.QUARANTINED,
            },
            status=status.HTTP_201_CREATED,
        )


class InternalPayRequestsView(_Internal):
    """Ask this shop's IntraForge Pay to take a payment (pay_bridge.py): the caller names the person,
    the amount, what it is for and its own record; IntraForge picks the Pay and checks the person."""

    def post(self, request):
        app = self.instance(request)
        data = request.data if isinstance(request.data, dict) else {}
        result = pay_bridge.create_request(
            app,
            actor_id=data.get("actorId"),
            amount_minor=data.get("amountMinor"),
            reference=data.get("reference"),
            external_id=data.get("externalId"),
        )
        user = result.pop("user")
        audit.record(
            actor=user,
            organization_id=app.organization_id,
            action="service_app.pay_request",
            resource_type="service_app",
            resource_id=result["pay"]["id"],
            context={
                "requested_by": {"id": str(app.id), "type": app.app_type, "name": app.display_name},
                "pay_request_id": result["id"],
                "amount_minor": result["amount_minor"],
                "reference": result["reference"],
            },
        )
        return Response(result, status=status.HTTP_201_CREATED)


class InternalPayRequestDetailView(_Internal):
    def get(self, request, request_id):
        return Response(pay_bridge.request_status(self.instance(request), request_id))


class InternalFileDetailView(_Internal):
    parser_classes = [JSONParser]

    def get(self, request, file_id):
        from storage.backends import get_client

        f = services.app_file(self.instance(request), file_id)
        body = get_client().get_stream(f.object_key)
        response = FileResponse(body, content_type="application/octet-stream")
        response["X-Content-SHA256"] = f.checksum_sha256
        response["Content-Length"] = str(f.size)
        return response

    def delete(self, request, file_id):
        from storage import services as storage

        app = self.instance(request)
        f = services.app_file(app, file_id)
        actor = services._member_user(app, request.data.get("actorId")) or app.created_by
        storage.delete_file(f, actor=actor)
        return Response(status=status.HTTP_204_NO_CONTENT)
