"""Read-only without a licence (ADR-0023): after the trial, without a valid licence, a request that would
change something is refused -- except signing in and out (IntraForge's own, and answering an application's
consent screen), activating the licence, and the internal service API."""

from django.http import JsonResponse

from . import services

SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}
ALWAYS_ALLOWED = ("/api/v1/auth/", "/api/v1/license/", "/api/v1/internal/", "/api/v1/oauth/consent/")


class LicenceMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path
        if (
            request.method not in SAFE_METHODS
            and path.startswith("/api/v1/")
            and not path.startswith(ALWAYS_ALLOWED)
            and services.read_only()
        ):
            return JsonResponse(
                {
                    "detail": (
                        "IntraForge is read-only: the trial has ended. "
                        "Enter your serial number under Licence."
                    ),
                    "code": "licence_required",
                },
                status=403,
            )
        return self.get_response(request)
