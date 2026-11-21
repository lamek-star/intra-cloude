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

from system import features

from . import quotas
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
        # Developer switched off (system/features.py): no application credential works, whatever it names.
        if not features.is_enabled(features.WEBSITES_DEVELOPER):
            raise AuthenticationFailed("Application access is switched off on this installation.")

        try:
            credential = resolve_credential(token)
        except InvalidCredential as exc:
            raise AuthenticationFailed("Invalid or expired credential.") from exc

        application = credential.service_account.application
        try:
            quotas.count_and_check(application.id, application.daily_request_limit)
        except quotas.DailyLimitReached:
            # DRF clears request.auth when authentication raises; this keeps the refused request in the
            # application's request log (applications/middleware.py), so the owner sees why it stopped.
            request._request.quota_refused_credential = credential
            raise
        return credential.service_account.identity_user, credential

    def authenticate_header(self, request):
        return self.keyword
