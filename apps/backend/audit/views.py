from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from organizations.services import get_member_organization
from permissions.services import has_permission

from .models import AuditEvent
from .serializers import AuditEventSerializer


class AuditEventListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, organization_id):
        org = get_member_organization(request.user, organization_id)
        if not has_permission(request.user, "audit.read", organization_id=org.id):
            return Response(status=status.HTTP_403_FORBIDDEN)

        events = AuditEvent.objects.filter(organization=org)[:200]
        return Response(AuditEventSerializer(events, many=True).data)
