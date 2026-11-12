"""Records each request an application makes with its bearer credential (ApiRequestLog), after the response.
DRF authenticates inside the view and sets request.auth on the underlying request, so a request with no
ApplicationCredential (every person's own session) is never recorded. Recording never changes or fails the
response: a write that fails is logged and the response goes out as it was."""

import logging
import time

from django.utils import timezone

logger = logging.getLogger(__name__)


class ApiRequestLogMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        started = time.monotonic()
        response = self.get_response(request)
        from .models import ApiRequestLog, ApplicationCredential

        credential = getattr(request, "auth", None)
        if isinstance(credential, ApplicationCredential):
            try:
                ApiRequestLog.objects.create(
                    application_id=credential.service_account.application_id,
                    credential=credential,
                    method=request.method[:8],
                    path=request.path[:300],
                    status=response.status_code,
                    duration_ms=int((time.monotonic() - started) * 1000),
                    at=timezone.now(),
                )
            except Exception:  # noqa: BLE001 - the log must never break the application's request
                logger.warning("could not record an application request", exc_info=True)
        return response
