"""Runtime preflight endpoints; no physical mutation is exposed here."""

from rest_framework.response import Response

from .access import get_owned
from .models import AppInstance
from .runtime_plan import plan_runtime
from .views import FoundationView


class RuntimePlan(FoundationView):
    def get(self, request, object_id):
        instance = get_owned(AppInstance, object_id, request.user, "organization")
        return Response(plan_runtime(request.user, instance))
