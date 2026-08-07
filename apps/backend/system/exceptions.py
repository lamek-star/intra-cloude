import logging
import uuid

from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

logger = logging.getLogger(__name__)


def structured_exception_handler(exc, context):
    """
    Wraps DRF's default exception handler to guarantee a consistent,
    non-leaking error shape and to log the full exception server-side with
    a request ID, never in the response body (Section 14 of the master
    prompt: never leak stack traces or internal details through the API).
    """
    response = drf_exception_handler(exc, context)

    request = context.get("request")
    request_id = getattr(request, "request_id", None) or str(uuid.uuid4())

    if response is None:
        # Unhandled exception: log full detail server-side, return a generic
        # body. DEBUG=True (dev only) still lets Django's own error page
        # take over before this handler for non-DRF views.
        logger.exception("Unhandled exception", extra={"request_id": request_id})
        return Response(
            {
                "error": {
                    "code": "internal_error",
                    "message": "An unexpected error occurred.",
                    "request_id": request_id,
                }
            },
            status=500,
        )

    response.data = {
        "error": {
            "code": getattr(exc, "default_code", "error"),
            "message": response.data,
            "request_id": request_id,
        }
    }
    return response
