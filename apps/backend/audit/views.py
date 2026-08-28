from rest_framework import generics
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated

from organizations.services import get_member_organization
from permissions.services import has_permission

from .models import AuditEvent
from .serializers import AuditEventSerializer


class AuditEventListView(generics.ListAPIView):
    """Real filtering/pagination over the organization's full audit
    history — the previous implementation returned only the most recent
    200 events with no way to reach anything older or narrow by action/
    actor/date, which made it useless for an actual incident
    investigation (Section 40 of the master prompt: "provide searchable
    audit views"). Uses the project-wide DEFAULT_PAGINATION_CLASS
    (LimitOffsetPagination) rather than a hardcoded slice."""

    serializer_class = AuditEventSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        org = get_member_organization(self.request.user, self.kwargs["organization_id"])
        if not has_permission(self.request.user, "audit.read", organization_id=org.id):
            raise PermissionDenied()

        queryset = AuditEvent.objects.filter(organization=org)

        params = self.request.query_params
        action = params.get("action")
        if action:
            queryset = queryset.filter(action=action)
        actor_id = params.get("actor")
        if actor_id:
            queryset = queryset.filter(actor_id=actor_id)
        resource_type = params.get("resource_type")
        if resource_type:
            queryset = queryset.filter(resource_type=resource_type)
        resource_id = params.get("resource_id")
        if resource_id:
            queryset = queryset.filter(resource_id=resource_id)
        result = params.get("result")
        if result:
            queryset = queryset.filter(result=result)
        since = params.get("since")
        if since:
            queryset = queryset.filter(timestamp__gte=since)
        until = params.get("until")
        if until:
            queryset = queryset.filter(timestamp__lte=until)
        return queryset
