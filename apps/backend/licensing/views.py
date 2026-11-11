from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from permissions.services import get_user_organization_ids, has_permission

from . import services


def can_activate(user) -> bool:
    """The Super Administrator, or an administrator of any organization here (permissions.manage)."""
    if has_permission(user, "system.admin", organization_id=None):
        return True
    return any(
        has_permission(user, "permissions.manage", organization_id=o) for o in get_user_organization_ids(user)
    )


class LicenceView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({**services.status(), "can_activate": can_activate(request.user)})


class ActivateView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"

    def post(self, request):
        if not can_activate(request.user):
            return Response({"detail": "Only an administrator can activate the licence."}, status=403)
        data = request.data if isinstance(request.data, dict) else {}
        result = services.activate(
            actor=request.user, serial=data.get("serial"), activation_code=data.get("activation_code")
        )
        return Response({**result, "can_activate": True})
