from django.http import Http404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import User
from audit import services as audit
from permissions.catalog import ADMIN_PERMISSION_CODES, ORGANIZATION_ROLE_SUMMARIES, SYSTEM_ROLES
from permissions.models import RoleAssignment
from permissions.services import PermissionError_, assign_role, has_permission, remove_role

from .models import Membership, Organization, Team
from .serializers import (
    AddMemberSerializer,
    AssignRoleSerializer,
    MembershipSerializer,
    OrganizationCreateSerializer,
    OrganizationSerializer,
    TeamCreateSerializer,
    TeamMemberSerializer,
    TeamSerializer,
)
from .services import add_team_member, create_organization, remove_team_member, service_account_of
from .services import get_member_organization as _get_member_organization
from .services import get_member_team as _get_member_team


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
        memberships = Membership.objects.filter(organization=org).select_related(
            "user", "user__service_account__application"
        )
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
            return Response({"detail": "This user is already a member."}, status=status.HTTP_409_CONFLICT)
        audit.record(
            actor=request.user,
            organization_id=org.id,
            action="organization.member.add",
            resource_type="user",
            resource_id=target_user.id,
        )
        return Response(MembershipSerializer(membership).data, status=status.HTTP_201_CREATED)


def _membership_for_role_change(request, organization_id, membership_id):
    """The organization (caller must be an active member: 404 otherwise) and one of ITS memberships,
    or a 403 Response when the caller may not manage roles there."""
    org = _get_member_organization(request.user, organization_id)
    if not has_permission(request.user, "permissions.manage", organization_id=org.id):
        return org, None, Response(status=status.HTTP_403_FORBIDDEN)
    try:
        membership = Membership.objects.select_related("user").get(id=membership_id, organization=org)
    except Membership.DoesNotExist as exc:
        raise Http404 from exc
    return org, membership, None


class OrganizationRolesView(APIView):
    """The roles this organization can give its members, and who holds which. Only for people who
    may manage roles (permissions.manage): who has which role is not shown to every member."""

    permission_classes = [IsAuthenticated]

    def get(self, request, organization_id):
        org = _get_member_organization(request.user, organization_id)
        if not has_permission(request.user, "permissions.manage", organization_id=org.id):
            return Response(status=status.HTTP_403_FORBIDDEN)
        roles = [
            {
                "slug": slug,
                "name": SYSTEM_ROLES[slug][0],
                "summary": summary,
                "administrative": bool(ADMIN_PERMISSION_CODES & set(SYSTEM_ROLES[slug][1])),
            }
            for slug, summary in ORGANIZATION_ROLE_SUMMARIES.items()
        ]
        memberships = dict(Membership.objects.filter(organization=org).values_list("user_id", "id"))
        assignments = [
            {"membership_id": str(memberships[user_id]), "role_slug": slug}
            for user_id, slug in RoleAssignment.objects.filter(
                organization=org, user_id__in=memberships.keys()
            ).values_list("user_id", "role__slug")
        ]
        return Response({"roles": roles, "assignments": assignments})


class MembershipRoleAssignView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, organization_id, membership_id):
        org, membership, refused = _membership_for_role_change(request, organization_id, membership_id)
        if refused:
            return refused

        account = service_account_of(membership.user)
        if account is not None:
            return Response(
                {
                    "detail": f"This is the sign-in of the application “{account.application.name}”. "
                    "Give it access to specific files or data from the application's page instead."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = AssignRoleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        role_slug = serializer.validated_data["role_slug"]
        if role_slug not in SYSTEM_ROLES:
            return Response({"detail": "Unknown role."}, status=status.HTTP_400_BAD_REQUEST)
        if role_slug not in ORGANIZATION_ROLE_SUMMARIES:
            return Response(
                {"detail": "This role can't be given to an organization member."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        existing = RoleAssignment.objects.filter(
            user=membership.user, role__slug=role_slug, role__organization__isnull=True, organization=org
        ).first()
        if existing is not None:
            return Response({"id": existing.id, "role": role_slug}, status=status.HTTP_200_OK)
        try:
            assignment = assign_role(
                user=membership.user, role_slug=role_slug, organization=org, granted_by=request.user
            )
        except PermissionError_ as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"id": assignment.id, "role": role_slug}, status=status.HTTP_201_CREATED)


class MembershipRoleRemoveView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, organization_id, membership_id, role_slug):
        org, membership, refused = _membership_for_role_change(request, organization_id, membership_id)
        if refused:
            return refused
        try:
            removed = remove_role(
                user=membership.user, role_slug=role_slug, organization=org, removed_by=request.user
            )
        except PermissionError_ as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
        if not removed:
            raise Http404
        return Response(status=status.HTTP_204_NO_CONTENT)


class TeamListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, organization_id):
        org = _get_member_organization(request.user, organization_id)
        teams = Team.objects.filter(organization=org)
        return Response(TeamSerializer(teams, many=True).data)

    def post(self, request, organization_id):
        org = _get_member_organization(request.user, organization_id)
        if not has_permission(request.user, "users.manage", organization_id=org.id):
            return Response(status=status.HTTP_403_FORBIDDEN)

        serializer = TeamCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        name = serializer.validated_data["name"]
        if Team.objects.filter(organization=org, name=name).exists():
            return Response(
                {"detail": "A team with this name already exists."}, status=status.HTTP_409_CONFLICT
            )
        team = Team.objects.create(organization=org, name=name)
        audit.record(
            actor=request.user,
            organization_id=org.id,
            action="organization.team.create",
            resource_type="team",
            resource_id=team.id,
            context={"name": name},
        )
        return Response(TeamSerializer(team).data, status=status.HTTP_201_CREATED)


class TeamMemberListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, team_id):
        team = _get_member_team(request.user, team_id)
        if not has_permission(request.user, "users.manage", organization_id=team.organization_id):
            return Response(status=status.HTTP_403_FORBIDDEN)

        serializer = TeamMemberSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            target_user = User.objects.get(id=serializer.validated_data["user_id"])
        except User.DoesNotExist as exc:
            raise Http404 from exc

        membership = add_team_member(team=team, user=target_user, actor=request.user)
        return Response(MembershipSerializer(membership).data, status=status.HTTP_201_CREATED)


class TeamMemberDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, team_id, user_id):
        team = _get_member_team(request.user, team_id)
        if not has_permission(request.user, "users.manage", organization_id=team.organization_id):
            return Response(status=status.HTTP_403_FORBIDDEN)

        try:
            target_user = User.objects.get(id=user_id)
        except User.DoesNotExist as exc:
            raise Http404 from exc

        remove_team_member(team=team, user=target_user, actor=request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)


class MembershipPasswordResetView(APIView):
    """An administrator gives a staff member a temporary password (shown once) when they forgot theirs:
    users.manage here, and in every other organization the person belongs to
    (accounts.services.can_reset_password). The person is signed out everywhere and must choose their own
    password at the next sign-in."""

    permission_classes = [IsAuthenticated]

    def post(self, request, organization_id, membership_id):
        from accounts import services as account_services

        org = _get_member_organization(request.user, organization_id)
        if not has_permission(request.user, "users.manage", organization_id=org.id):
            return Response(status=status.HTTP_403_FORBIDDEN)
        try:
            membership = Membership.objects.select_related("user").get(id=membership_id, organization=org)
        except Membership.DoesNotExist as exc:
            raise Http404 from exc
        try:
            temporary = account_services.reset_password(
                actor=request.user, target=membership.user, organization_id=org.id
            )
        except account_services.PasswordError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_403_FORBIDDEN)
        return Response({"email": membership.user.email, "temporary_password": temporary})
