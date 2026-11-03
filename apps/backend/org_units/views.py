from django.http import Http404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import User
from organizations.services import get_member_organization
from permissions.services import has_permission

from . import services
from .models import OrganizationalUnit
from .serializers import (
    OrganizationalUnitCreateSerializer,
    OrganizationalUnitSerializer,
    OrganizationalUnitTreeSerializer,
    OrganizationalUnitUpdateSerializer,
    UnitMemberAddSerializer,
    UnitMembershipSerializer,
)
from .services import CrossOrganizationError, CycleError, HasChildrenError, get_member_unit


def _resolve_parent(organization, parent_id):
    if parent_id is None:
        return None
    try:
        return OrganizationalUnit.objects.get(id=parent_id, organization=organization)
    except OrganizationalUnit.DoesNotExist as exc:
        raise Http404 from exc


class OrganizationalUnitListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, organization_id):
        org = get_member_organization(request.user, organization_id)
        if not has_permission(request.user, "org_unit.read", organization_id=org.id):
            return Response(status=status.HTTP_403_FORBIDDEN)
        units = OrganizationalUnit.objects.filter(organization=org)
        return Response(OrganizationalUnitSerializer(units, many=True).data)

    def post(self, request, organization_id):
        org = get_member_organization(request.user, organization_id)
        if not has_permission(request.user, "org_unit.manage", organization_id=org.id):
            return Response(status=status.HTTP_403_FORBIDDEN)

        serializer = OrganizationalUnitCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        parent = _resolve_parent(org, serializer.validated_data.get("parent"))
        name = serializer.validated_data["name"]
        if OrganizationalUnit.objects.filter(organization=org, parent=parent, name=name).exists():
            return Response(
                {"detail": "A unit with this name already exists under this parent."},
                status=status.HTTP_409_CONFLICT,
            )
        try:
            unit = services.create_unit(
                organization=org,
                name=serializer.validated_data["name"],
                unit_type=serializer.validated_data["unit_type"],
                parent=parent,
                actor=request.user,
            )
        except CrossOrganizationError:
            return Response(
                {"detail": "Parent unit belongs to a different organization."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(OrganizationalUnitSerializer(unit).data, status=status.HTTP_201_CREATED)


class OrganizationalUnitTreeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, organization_id):
        org = get_member_organization(request.user, organization_id)
        if not has_permission(request.user, "org_unit.read", organization_id=org.id):
            return Response(status=status.HTTP_403_FORBIDDEN)
        roots = OrganizationalUnit.objects.filter(organization=org, parent__isnull=True)
        return Response(OrganizationalUnitTreeSerializer(roots, many=True).data)


class OrganizationalUnitDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, unit_id):
        unit = get_member_unit(request.user, unit_id)
        if not has_permission(request.user, "org_unit.read", organization_id=unit.organization_id):
            return Response(status=status.HTTP_403_FORBIDDEN)
        return Response(OrganizationalUnitSerializer(unit).data)

    def patch(self, request, unit_id):
        unit = get_member_unit(request.user, unit_id)
        if not has_permission(request.user, "org_unit.manage", organization_id=unit.organization_id):
            return Response(status=status.HTTP_403_FORBIDDEN)

        serializer = OrganizationalUnitUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        parent_given = "parent" in request.data
        parent = None
        if parent_given and data.get("parent") is not None:
            parent = _resolve_parent(unit.organization, data["parent"])

        effective_name = data.get("name", unit.name)
        effective_parent = parent if parent_given else unit.parent
        if (
            (data.get("name") is not None or parent_given)
            and OrganizationalUnit.objects.filter(
                organization=unit.organization, parent=effective_parent, name=effective_name
            )
            .exclude(id=unit.id)
            .exists()
        ):
            return Response(
                {"detail": "A unit with this name already exists under this parent."},
                status=status.HTTP_409_CONFLICT,
            )

        try:
            updated = services.update_unit(
                unit=unit,
                actor=request.user,
                name=data.get("name"),
                unit_type=data.get("unit_type"),
                parent=parent,
                parent_given=parent_given,
            )
        except CycleError:
            return Response(
                {"detail": "This would make a unit its own ancestor."}, status=status.HTTP_409_CONFLICT
            )
        except CrossOrganizationError:
            return Response(
                {"detail": "Parent unit belongs to a different organization."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(OrganizationalUnitSerializer(updated).data)

    def delete(self, request, unit_id):
        unit = get_member_unit(request.user, unit_id)
        if not has_permission(request.user, "org_unit.manage", organization_id=unit.organization_id):
            return Response(status=status.HTTP_403_FORBIDDEN)
        try:
            services.delete_unit(unit=unit, actor=request.user)
        except HasChildrenError:
            return Response(
                {"detail": "Delete or move this unit's child units first."},
                status=status.HTTP_409_CONFLICT,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)


class UnitMemberListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, unit_id):
        unit = get_member_unit(request.user, unit_id)
        if not has_permission(request.user, "org_unit.read", organization_id=unit.organization_id):
            return Response(status=status.HTTP_403_FORBIDDEN)
        return Response(UnitMembershipSerializer(unit.memberships.all(), many=True).data)

    def post(self, request, unit_id):
        unit = get_member_unit(request.user, unit_id)
        if not has_permission(
            request.user, "org_unit.membership.manage", organization_id=unit.organization_id
        ):
            return Response(status=status.HTTP_403_FORBIDDEN)

        serializer = UnitMemberAddSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            target_user = User.objects.get(id=serializer.validated_data["user_id"])
        except User.DoesNotExist as exc:
            raise Http404 from exc

        membership = services.add_unit_member(unit=unit, user=target_user, actor=request.user)
        return Response(UnitMembershipSerializer(membership).data, status=status.HTTP_201_CREATED)


class UnitMemberDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, unit_id, user_id):
        unit = get_member_unit(request.user, unit_id)
        if not has_permission(
            request.user, "org_unit.membership.manage", organization_id=unit.organization_id
        ):
            return Response(status=status.HTTP_403_FORBIDDEN)

        try:
            target_user = User.objects.get(id=user_id)
        except User.DoesNotExist as exc:
            raise Http404 from exc

        services.remove_unit_member(unit=unit, user=target_user, actor=request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)
