from django.http import Http404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from organizations.models import Membership
from organizations.services import get_member_organization

from .models import Project, Workspace
from .serializers import (
    ProjectCreateSerializer,
    ProjectSerializer,
    WorkspaceCreateSerializer,
    WorkspaceSerializer,
)


def get_member_workspace(user, workspace_id) -> Workspace:
    """Same pattern as organizations.services.get_member_organization: resolves a
    Workspace only if the requester is an active member of its
    Organization, otherwise 404 — tenant isolation is enforced by the
    query, not a separate permission check bolted on afterward."""
    try:
        return Workspace.objects.select_related("organization").get(
            id=workspace_id,
            organization__memberships__user=user,
            organization__memberships__status=Membership.Status.ACTIVE,
        )
    except Workspace.DoesNotExist as exc:
        raise Http404 from exc


def get_member_project(user, project_id) -> Project:
    try:
        return Project.objects.select_related("workspace__organization").get(
            id=project_id,
            workspace__organization__memberships__user=user,
            workspace__organization__memberships__status=Membership.Status.ACTIVE,
        )
    except Project.DoesNotExist as exc:
        raise Http404 from exc


class WorkspaceListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, organization_id):
        org = get_member_organization(request.user, organization_id)
        workspaces = Workspace.objects.filter(organization=org)
        return Response(WorkspaceSerializer(workspaces, many=True).data)

    def post(self, request, organization_id):
        org = get_member_organization(request.user, organization_id)
        serializer = WorkspaceCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        workspace = Workspace.objects.create(
            organization=org, name=serializer.validated_data["name"], created_by=request.user
        )
        return Response(WorkspaceSerializer(workspace).data, status=status.HTTP_201_CREATED)


class WorkspaceDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, workspace_id):
        workspace = get_member_workspace(request.user, workspace_id)
        return Response(WorkspaceSerializer(workspace).data)


class ProjectListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, workspace_id):
        workspace = get_member_workspace(request.user, workspace_id)
        projects = Project.objects.filter(workspace=workspace)
        return Response(ProjectSerializer(projects, many=True).data)

    def post(self, request, workspace_id):
        workspace = get_member_workspace(request.user, workspace_id)
        serializer = ProjectCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        project = Project.objects.create(
            workspace=workspace, name=serializer.validated_data["name"], created_by=request.user
        )
        return Response(ProjectSerializer(project).data, status=status.HTTP_201_CREATED)


class ProjectDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, project_id):
        project = get_member_project(request.user, project_id)
        return Response(ProjectSerializer(project).data)
