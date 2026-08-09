from django.http import Http404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import User
from permissions.catalog import SYSTEM_ROLES
from permissions.services import assign_role, has_permission

from .models import Membership, Organization
from .serializers import (
    AddMemberSerializer,
    AssignRoleSerializer,
    MembershipSerializer,
    OrganizationCreateSerializer,
    OrganizationSerializer,
)
from .services import create_organization
from .services import get_member_organization as _get_member_organization


class OrganizationListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        orgs = Organization.objects.filter(
            memberships__user=request.user, memberships__status=Membership.Status.ACTIVE
        ).distinct()
        return Response(OrganizationSerializer(orgs, many=True).data)

    def post(self, request):
        serializer = OrganizationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        org = create_organization(name=serializer.validated_data["name"], created_by=request.user)
        return Response(OrganizationSerializer(org).data, status=status.HTTP_201_CREATED)


class OrganizationDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, organization_id):
        org = _get_member_organization(request.user, organization_id)
        return Response(OrganizationSerializer(org).data)


class MembershipListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, organization_id):
        org = _get_member_organization(request.user, organization_id)
        memberships = Membership.objects.filter(organization=org).select_related("user")
        return Response(MembershipSerializer(memberships, many=True).data)

    def post(self, request, organization_id):
        org = _get_member_organization(request.user, organization_id)
        if not has_permission(request.user, "users.manage", organization_id=org.id):
            return Response(status=status.HTTP_403_FORBIDDEN)

        serializer = AddMemberSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            target_user = User.objects.get(email__iexact=serializer.validated_data["email"])
        except User.DoesNotExist:
            return Response(
                {"detail": "No user with that email exists yet."}, status=status.HTTP_404_NOT_FOUND
            )

        membership, created = Membership.objects.get_or_create(
            user=target_user,
            organization=org,
            defaults={"status": Membership.Status.ACTIVE, "invited_by": request.user},
        )
        if not created:
            return Response(
                {"detail": "This user is already a member."}, status=status.HTTP_409_CONFLICT
            )
        return Response(MembershipSerializer(membership).data, status=status.HTTP_201_CREATED)


class MembershipRoleAssignView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, organization_id, membership_id):
        org = _get_member_organization(request.user, organization_id)
        if not has_permission(request.user, "permissions.manage", organization_id=org.id):
            return Response(status=status.HTTP_403_FORBIDDEN)

        try:
            membership = Membership.objects.get(id=membership_id, organization=org)
        except Membership.DoesNotExist as exc:
            raise Http404 from exc

        serializer = AssignRoleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        role_slug = serializer.validated_data["role_slug"]
        if role_slug not in SYSTEM_ROLES:
            return Response({"detail": "Unknown role."}, status=status.HTTP_400_BAD_REQUEST)

        assignment = assign_role(
            user=membership.user, role_slug=role_slug, organization=org, granted_by=request.user
        )
        return Response({"id": assignment.id, "role": role_slug}, status=status.HTTP_201_CREATED)
