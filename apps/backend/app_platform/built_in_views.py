"""Built-in application gallery, one-click install and setup retry (see built_in_apps.py)."""

import uuid

from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from workspaces.views import get_member_project

from . import built_in_apps
from .access import get_owned
from .models import AppInstance
from .serializers import InstanceSerializer
from .views import FoundationView, readable


class BuiltInAppList(FoundationView):
    """What this deployment offers a customer -- QUALIFIED applications only, unless
    SHOW_UNQUALIFIED_BUILT_IN_APPS is on. With `?project=<id>` each entry also lists the
    instances of it in that project the caller may read, and their runtime state.
    Human sessions only."""

    def get(self, request):
        project_id = request.query_params.get("project")
        if project_id is None:
            return Response({"results": built_in_apps.listing()})
        try:
            project_uuid = uuid.UUID(project_id)
        except ValueError as exc:
            raise ValidationError({"project": "Must be a project id."}) from exc
        project = get_member_project(request.user, project_uuid)
        visible = readable(
            project.app_instances.all(),
            request.user,
            project.workspace.organization_id,
            "app_instance",
            "app_instance.read",
        )
        return Response({"results": built_in_apps.listing(visible)})


class BuiltInAppInstall(FoundationView):
    """Install one built-in application into a project the caller is a member of.
    Authorization is unchanged: every underlying service checks its own capability."""

    def post(self, request, project_id, key):
        project = get_member_project(request.user, project_id)
        label = request.data.get("label") if isinstance(request.data, dict) else None
        instance = built_in_apps.install(request.user, project, key, label)
        return Response(InstanceSerializer(instance).data, status=201)


class BuiltInAppRetry(FoundationView):
    """Finish preparing a built-in application whose setup did not complete. Idempotent."""

    def post(self, request, object_id):
        instance = get_owned(AppInstance, object_id, request.user, "organization")
        return Response(InstanceSerializer(built_in_apps.retry_provisioning(request.user, instance)).data)
