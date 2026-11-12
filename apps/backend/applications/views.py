from django.http import Http404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from organizations.models import Membership
from organizations.services import get_member_organization
from permissions.services import (
    PermissionError_,
    grant_resource_permission,
    has_permission,
    revoke_resource_permission,
)

from . import services
from .models import Application, ApplicationCredential
from .serializers import (
    ApplicationCreateSerializer,
    ApplicationCredentialSerializer,
    ApplicationSerializer,
    ResourceGrantCreateSerializer,
    ResourceGrantSerializer,
)


def get_member_application(user, application_id) -> Application:
    try:
        return Application.objects.select_related("organization").get(
            id=application_id,
            organization__memberships__user=user,
            organization__memberships__status=Membership.Status.ACTIVE,
        )
    except Application.DoesNotExist as exc:
        raise Http404 from exc


class ApplicationListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, organization_id):
        org = get_member_organization(request.user, organization_id)
        if not has_permission(request.user, "application.read", organization_id=org.id):
            return Response(status=status.HTTP_403_FORBIDDEN)
        apps = Application.objects.filter(organization=org)
        return Response(ApplicationSerializer(apps, many=True).data)

    def post(self, request, organization_id):
        org = get_member_organization(request.user, organization_id)
        if not has_permission(request.user, "application.create", organization_id=org.id):
            return Response(status=status.HTTP_403_FORBIDDEN)

        serializer = ApplicationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        application = services.register_application(
            organization=org,
            name=serializer.validated_data["name"],
            description=serializer.validated_data["description"],
            owner=request.user,
        )
        return Response(ApplicationSerializer(application).data, status=status.HTTP_201_CREATED)


class ApplicationDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, application_id):
        application = get_member_application(request.user, application_id)
        if not has_permission(request.user, "application.read", organization_id=application.organization_id):
            return Response(status=status.HTTP_403_FORBIDDEN)
        return Response(ApplicationSerializer(application).data)


class ApplicationCredentialListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, application_id):
        application = get_member_application(request.user, application_id)
        if not has_permission(
            request.user, "application.credentials.manage", organization_id=application.organization_id
        ):
            return Response(status=status.HTTP_403_FORBIDDEN)
        credentials = application.service_account.credentials.all()
        return Response(ApplicationCredentialSerializer(credentials, many=True).data)

    def post(self, request, application_id):
        application = get_member_application(request.user, application_id)
        if not has_permission(
            request.user, "application.credentials.manage", organization_id=application.organization_id
        ):
            return Response(status=status.HTTP_403_FORBIDDEN)

        credential, token = services.issue_credential(
            service_account=application.service_account, actor=request.user
        )
        data = ApplicationCredentialSerializer(credential).data
        data["secret"] = token  # shown exactly once (Section 13 of the master prompt)
        return Response(data, status=status.HTTP_201_CREATED)


def _get_member_credential(user, application_id, credential_id) -> ApplicationCredential:
    application = get_member_application(user, application_id)
    try:
        return application.service_account.credentials.get(id=credential_id)
    except ApplicationCredential.DoesNotExist as exc:
        raise Http404 from exc


class ApplicationCredentialRevokeView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, application_id, credential_id):
        credential = _get_member_credential(request.user, application_id, credential_id)
        if not has_permission(
            request.user, "application.credentials.manage", organization_id=credential.organization_id
        ):
            return Response(status=status.HTTP_403_FORBIDDEN)
        services.revoke_credential(credential=credential, actor=request.user)
        return Response(ApplicationCredentialSerializer(credential).data)


class ApplicationCredentialRotateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, application_id, credential_id):
        credential = _get_member_credential(request.user, application_id, credential_id)
        if not has_permission(
            request.user, "application.credentials.manage", organization_id=credential.organization_id
        ):
            return Response(status=status.HTTP_403_FORBIDDEN)
        new_credential, token = services.rotate_credential(credential=credential, actor=request.user)
        data = ApplicationCredentialSerializer(new_credential).data
        data["secret"] = token
        return Response(data, status=status.HTTP_201_CREATED)


class ApplicationResourceGrantListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, application_id):
        application = get_member_application(request.user, application_id)
        if not has_permission(
            request.user, "permissions.manage", organization_id=application.organization_id
        ):
            return Response(status=status.HTTP_403_FORBIDDEN)
        grants = application.service_account.identity_user.resource_grants.filter(
            organization_id=application.organization_id
        )
        return Response(ResourceGrantSerializer(grants, many=True).data)

    def post(self, request, application_id):
        application = get_member_application(request.user, application_id)
        if not has_permission(
            request.user, "permissions.manage", organization_id=application.organization_id
        ):
            return Response(status=status.HTTP_403_FORBIDDEN)

        serializer = ResourceGrantCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            grant = grant_resource_permission(
                user=application.service_account.identity_user,
                permission_code=data["permission_code"],
                organization_id=application.organization_id,
                resource_type=data["resource_type"],
                resource_id=data["resource_id"],
                granted_by=request.user,
                expires_at=data["expires_at"],
            )
        except PermissionError_ as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(ResourceGrantSerializer(grant).data, status=status.HTTP_201_CREATED)


class ApplicationResourceGrantDetailView(APIView):
    """Revokes one of the application's own grants (e.g. taking IntraForge Pay away from a hosted app)."""

    permission_classes = [IsAuthenticated]

    def delete(self, request, application_id, grant_id):
        application = get_member_application(request.user, application_id)
        if not has_permission(
            request.user, "permissions.manage", organization_id=application.organization_id
        ):
            return Response(status=status.HTTP_403_FORBIDDEN)
        grant = application.service_account.identity_user.resource_grants.filter(
            id=grant_id, organization_id=application.organization_id
        ).first()
        if grant is None:
            raise Http404
        revoke_resource_permission(grant=grant, revoked_by=request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)


class ApplicationRequestLogView(APIView):
    """The application's recent requests (application.read): newest first, paginated; ?errors=1 shows only
    the ones that did not succeed (status 400 and above)."""

    permission_classes = [IsAuthenticated]

    def get(self, request, application_id):
        from rest_framework.pagination import LimitOffsetPagination

        from .models import ApiRequestLog

        application = get_member_application(request.user, application_id)
        if not has_permission(request.user, "application.read", organization_id=application.organization_id):
            return Response(status=status.HTTP_403_FORBIDDEN)
        qs = ApiRequestLog.objects.filter(application=application)
        if request.query_params.get("errors") == "1":
            qs = qs.filter(status__gte=400)
        paginator = LimitOffsetPagination()
        page = paginator.paginate_queryset(qs, request, view=self)
        return paginator.get_paginated_response(
            [
                {
                    "id": r.id,
                    "method": r.method,
                    "path": r.path,
                    "status": r.status,
                    "duration_ms": r.duration_ms,
                    "at": r.at.isoformat(),
                    "credential": str(r.credential_id) if r.credential_id else None,
                }
                for r in page
            ]
        )
