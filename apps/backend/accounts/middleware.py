"""After an administrator reset someone's password, that person may do nothing through the API until they
choose their own (accounts.services.reset_password sets must_change_password): only seeing who they are,
changing the password, signing out and the CSRF cookie stay open."""

from django.http import JsonResponse

ALLOWED = ("/api/v1/auth/me/", "/api/v1/auth/password/", "/api/v1/auth/logout/", "/api/v1/auth/csrf/")


class PasswordChangeMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        if (
            user is not None
            and user.is_authenticated
            and getattr(user, "must_change_password", False)
            and request.path.startswith("/api/v1/")
            and not request.path.startswith(ALLOWED)
        ):
            return JsonResponse(
                {"detail": "Choose your own password first.", "code": "password_change_required"}, status=403
            )
        return self.get_response(request)
