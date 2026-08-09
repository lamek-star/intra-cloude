from django.http import Http404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import User
from organizations.services import get_member_organization, get_member_team
from permissions.services import has_permission

from . import services
from .models import ShareGrant
from .serializers import ExternalSharingSettingSerializer, ShareGrantCreateSerializer, ShareGrantSerializer


def _request_id(request) -> str:
    return getattr(request, "request_id", "") or ""


def _handle(fn):
    try:
        return fn(), None
    except services.SharingPermissionDenied:
        return None, Response(status=status.HTTP_403_FORBIDDEN)
    except services.SharingValidationError as exc:
        return None, Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)


class ShareGrantListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, organization_id):
        org = get_member_organization(request.user, organization_id)
        if not has_permission(request.user, "sharing.manage", organization_id=org.id):
            return Response(status=status.HTTP_403_FORBIDDEN)
        shares = ShareGrant.objects.filter(organization=org)
        return Response(ShareGrantSerializer(shares, many=True).data)

    def post(self, request, organization_id):
        org = get_member_organization(request.user, organization_id)
        serializer = ShareGrantCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        target_user = None
        if data["user_id"] is not None:
            try:
                target_user = User.objects.get(id=data["user_id"])
            except User.DoesNotExist as exc:
                raise Http404 from exc

        target_team = None
        if data["team_id"] is not None:
            target_team = get_member_team(request.user, data["team_id"])
            if target_team.organization_id != org.id:
                raise Http404

        result, error = _handle(
            lambda: services.create_share_grant(
                actor=request.user,
                organization=org,
                resource_type=data["resource_type"],
                resource_id=data["resource_id"],
                principal_type=data["principal_type"],
                level=data["level"],
                user=target_user,
                team=target_team,
                expires_at=data["expires_at"],
                request_id=_request_id(request),
            )
        )
        if error:
            return error
        return Response(ShareGrantSerializer(result).data, status=status.HTTP_201_CREATED)


class ShareGrantDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, share_id):
        share = services.get_member_share(request.user, share_id)
        if not has_permission(request.user, "sharing.manage", organization_id=share.organization_id):
            return Response(status=status.HTTP_403_FORBIDDEN)
        return Response(ShareGrantSerializer(share).data)

    def delete(self, request, share_id):
        share = services.get_member_share(request.user, share_id)
        _, error = _handle(
            lambda: services.revoke_share_grant(
                actor=request.user, share=share, request_id=_request_id(request)
            )
        )
        if error:
            return error
        return Response(status=status.HTTP_204_NO_CONTENT)


class ExternalSharingSettingView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, organization_id):
        org = get_member_organization(request.user, organization_id)
        serializer = ExternalSharingSettingSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        result, error = _handle(
            lambda: services.set_external_sharing_enabled(
                actor=request.user,
                organization=org,
                enabled=serializer.validated_data["enabled"],
                request_id=_request_id(request),
            )
        )
        if error:
            return error
        return Response({"external_sharing_enabled": result.external_sharing_enabled})
