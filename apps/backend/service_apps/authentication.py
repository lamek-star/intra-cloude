"""Authentication for the internal service-application API (ADR-0018).

A service authenticates with its deployment's service token in `X-IntraForge-Service-Token`. It
acts as that deployment only -- never as a user -- and reaches only its own instance's endpoints.
The proxy refuses /api/v1/internal/ from outside, so these endpoints are reachable only on the
internal Docker network; the token is still required there.
"""

from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.permissions import BasePermission

from .deployments import Deployment, deployment_for_token

HEADER = "HTTP_X_INTRAFORGE_SERVICE_TOKEN"


class ServicePrincipal:
    """The authenticated caller of an internal endpoint: a deployment, not a person."""

    is_authenticated = True
    is_active = True
    is_anonymous = False
    pk = None

    def __init__(self, deployment: Deployment):
        self.deployment = deployment

    def __str__(self):
        return f"service:{self.deployment.key}"


class ServiceTokenAuthentication(BaseAuthentication):
    def authenticate(self, request):
        token = request.META.get(HEADER)
        if not token:
            return None
        deployment = deployment_for_token(token)
        if deployment is None:
            raise AuthenticationFailed("Invalid service token.")
        return (ServicePrincipal(deployment), None)

    def authenticate_header(self, request):
        return "IntraForge-Service"


class IsServicePrincipal(BasePermission):
    def has_permission(self, request, view):
        return isinstance(request.user, ServicePrincipal)
