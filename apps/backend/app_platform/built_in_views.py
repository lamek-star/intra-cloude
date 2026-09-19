"""Built-in application gallery and one-click install (see built_in_apps.py)."""

from rest_framework.response import Response

from workspaces.views import get_member_project

from . import built_in_apps
from .serializers import InstanceSerializer
from .views import FoundationView


class BuiltInAppList(FoundationView):
    """What this deployment offers a customer -- QUALIFIED applications only,
    unless SHOW_UNQUALIFIED_BUILT_IN_APPS is on. Human sessions only."""

    def get(self, request):
        return Response({"results": built_in_apps.listing()})


class BuiltInAppInstall(FoundationView):
    """Install one built-in application into a project the caller is a member of.
    Authorization is unchanged: every underlying service checks its own capability."""

    def post(self, request, project_id, key):
        project = get_member_project(request.user, project_id)
        label = request.data.get("label") if isinstance(request.data, dict) else None
        instance = built_in_apps.install(request.user, project, key, label)
        return Response(InstanceSerializer(instance).data, status=201)
