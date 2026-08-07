import uuid

REQUEST_ID_HEADER = "X-Request-ID"


class RequestIDMiddleware:
    """Attaches a request ID to every request/response for log and audit
    correlation (docs/architecture/ARCHITECTURE.md Section 9)."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        incoming = request.headers.get(REQUEST_ID_HEADER)
        request.request_id = incoming or str(uuid.uuid4())
        response = self.get_response(request)
        response[REQUEST_ID_HEADER] = request.request_id
        return response
