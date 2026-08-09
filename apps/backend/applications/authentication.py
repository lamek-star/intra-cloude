"""
Service-account authentication for the API (Section 14 of the master
prompt). A valid `Authorization: Bearer pdc_sk_...` resolves to the
credential's ServiceAccount's `identity_user` — from that point on, every
existing permission check, tenant-scoped lookup, and audit call treats it
exactly like a human user's session, because it *is* the same `User`
model (see applications/models.py:ServiceAccount docstring).
"""

from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed

from .services import InvalidCredential, resolve_credential


class ServiceAccountAuthentication(BaseAuthentication):
    keyword = "Bearer"

    def authenticate(self, request):
        header = request.META.get("HTTP_AUTHORIZATION", "")
        prefix = f"{self.keyword} "
        if not header.startswith(prefix):
            return None
        token = header[len(prefix) :].strip()
        if not token:
            return None

        try:
            credential = resolve_credential(token)
        except InvalidCredential as exc:
            raise AuthenticationFailed("Invalid or expired credential.") from exc

        return credential.service_account.identity_user, credential

    def authenticate_header(self, request):
        return self.keyword
