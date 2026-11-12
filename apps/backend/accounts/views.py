from django.contrib.auth import authenticate, login, logout
from django.middleware.csrf import get_token
from rest_framework import status
from rest_framework.authentication import BaseAuthentication
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from audit import services as audit
from audit.models import AuditEvent

from . import passkeys, services
from .models import User
from .serializers import (
    LoginSerializer,
    MFACodeSerializer,
    MFAVerifySerializer,
    PasswordChangeSerializer,
    RegisterSerializer,
    UserSerializer,
)

# Distinct from Django's own SESSION_KEY: a session carrying only this
# key is a "password verified, second factor not yet given" state, not
# an authenticated session — AuthenticationMiddleware doesn't recognize
# it, so no endpoint gated by IsAuthenticated is reachable until
# MFALoginVerifyView completes the real login().
MFA_PENDING_SESSION_KEY = "mfa_pending_user_id"
MFA_PENDING_SESSION_TIMEOUT_SECONDS = 300


class CSRFView(APIView):
    """`GET /auth/csrf/` — a browser SPA hits this once on load so Django
    actually sets the `csrftoken` cookie (it's otherwise only set as a
    side effect of `get_token()` running during some other request, e.g.
    the first authenticated mutation, which is too late — the frontend
    needs the cookie's value *before* it can send the matching
    `X-CSRFToken` header on that very first mutating request)."""

    permission_classes = [AllowAny]
    authentication_classes: list[type[BaseAuthentication]] = []

    def get(self, request):
        get_token(request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class RegisterView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        login(request, user)
        return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)


class LoginView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]
        user = authenticate(
            request,
            username=email,
            password=serializer.validated_data["password"],
        )
        if user is None or not user.is_active:
            audit.record(
                actor=None,
                organization_id=None,
                action="auth.login",
                result=AuditEvent.Result.DENIED,
                context={"email": email},
            )
            return Response({"detail": "Invalid credentials."}, status=status.HTTP_401_UNAUTHORIZED)

        if user.passkey_only:
            # The owner switched password sign-in off for this account (ADR-0019): even the right password
            # is refused.
            audit.record(
                actor=user,
                organization_id=None,
                action="auth.login",
                result=AuditEvent.Result.DENIED,
                context={"reason": "passkey only"},
            )
            return Response(
                {"detail": "This account signs in with a passkey only.", "passkey_only": True},
                status=status.HTTP_403_FORBIDDEN,
            )

        if user.mfa_enabled:
            request.session[MFA_PENDING_SESSION_KEY] = str(user.id)
            request.session.set_expiry(MFA_PENDING_SESSION_TIMEOUT_SECONDS)
            return Response({"mfa_required": True})

        login(request, user)
        audit.record(actor=user, organization_id=None, action="auth.login")
        return Response(UserSerializer(user).data)


class MFALoginVerifyView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"

    def post(self, request):
        pending_id = request.session.get(MFA_PENDING_SESSION_KEY)
        if not pending_id:
            return Response({"detail": "No MFA login in progress."}, status=status.HTTP_400_BAD_REQUEST)

        serializer = MFAVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            user = User.objects.get(id=pending_id, is_active=True)
        except User.DoesNotExist:
            del request.session[MFA_PENDING_SESSION_KEY]
            return Response({"detail": "Invalid credentials."}, status=status.HTTP_401_UNAUTHORIZED)

        if not services.verify_mfa_code(user=user, code=serializer.validated_data["code"]):
            audit.record(
                actor=user, organization_id=None, action="auth.mfa_verify", result=AuditEvent.Result.DENIED
            )
            return Response({"detail": "Invalid code."}, status=status.HTTP_401_UNAUTHORIZED)

        del request.session[MFA_PENDING_SESSION_KEY]
        # The pending step's short limit (MFA_PENDING_SESSION_TIMEOUT_SECONDS) is for the half-signed-in
        # state only; without this, login() carried it over and signed two-step users out minutes later.
        request.session.set_expiry(None)
        login(request, user)
        audit.record(actor=user, organization_id=None, action="auth.login")
        return Response(UserSerializer(user).data)


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        audit.record(actor=request.user, organization_id=None, action="auth.logout")
        logout(request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user).data)


class MFAEnrollView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            result = services.start_mfa_enrollment(user=request.user)
        except services.MFAError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(result, status=status.HTTP_201_CREATED)


class MFAConfirmView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = MFACodeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            codes = services.confirm_mfa_enrollment(user=request.user, code=serializer.validated_data["code"])
        except services.MFAError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        # The recovery codes are in this answer only: they are never shown again.
        return Response({**UserSerializer(request.user).data, "recovery_codes": codes})


class MFADisableView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = MFACodeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            services.disable_mfa(user=request.user, code=serializer.validated_data["code"])
        except services.MFAError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(UserSerializer(request.user).data)


# ---------------------------------------------------------------------------------------- passkeys (ADR-0019)
def _passkey_error(exc: Exception) -> Response:
    return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)


def _text(request, key: str, limit: int = 200) -> str:
    value = request.data.get(key)
    return value[:limit] if isinstance(value, str) else ""


def _credential(request) -> dict:
    value = request.data.get("credential")
    if not isinstance(value, dict):
        raise passkeys.PasskeyError("That is not a passkey answer.")
    return value


class PasskeyListView(APIView):
    """`GET /auth/passkeys/` -- the signed-in user's own passkeys (never anyone else's)."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            rp_id = passkeys.relying_party(request)[0]
        except passkeys.PasskeyError:
            rp_id = None
        return Response(
            {
                "passkey_only": request.user.passkey_only,
                "this_address": rp_id,
                "passkeys": [passkeys.describe(p) for p in request.user.passkeys.all()],
            }
        )


class PasskeyRegisterOptionsView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"

    def post(self, request):
        try:
            options = passkeys.begin_registration(
                request,
                user=request.user,
                password=_text(request, "password"),
                code=_text(request, "code", 6),
                where=_text(request, "where", 20),
            )
        except passkeys.PasskeyError as exc:
            return _passkey_error(exc)
        return Response(options)


class PasskeyRegisterVerifyView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"

    def post(self, request):
        try:
            passkey = passkeys.finish_registration(
                request, user=request.user, credential=_credential(request), name=_text(request, "name", 80)
            )
        except passkeys.PasskeyError as exc:
            return _passkey_error(exc)
        return Response(passkeys.describe(passkey), status=status.HTTP_201_CREATED)


class PasskeyRemoveView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"

    def post(self, request, passkey_id):
        try:
            passkeys.remove_passkey(
                user=request.user,
                passkey_id=passkey_id,
                password=_text(request, "password"),
                code=_text(request, "code", 6),
            )
        except passkeys.PasskeyError as exc:
            return _passkey_error(exc)
        return Response(status=status.HTTP_204_NO_CONTENT)


class PasskeyOnlyView(APIView):
    """`POST /auth/passkeys/only/` with `{"on": true, "password": ...}`, or `{"on": false}` after a fresh
    passkey check in this session."""

    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"

    def post(self, request):
        on = request.data.get("on")
        if not isinstance(on, bool):
            return Response({"detail": "on must be true or false."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            passkeys.set_passkey_only(
                request,
                user=request.user,
                on=on,
                password=_text(request, "password"),
                code=_text(request, "code", 6),
            )
        except passkeys.PasskeyError as exc:
            return _passkey_error(exc)
        return Response(UserSerializer(request.user).data)


class PasskeyCheckOptionsView(APIView):
    """Signed in: a fresh check with one of the user's own passkeys. Signed out: passkey sign-in."""

    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"

    def post(self, request):
        user = request.user if request.user.is_authenticated else None
        try:
            return Response(passkeys.begin_check(request, user=user, where=_text(request, "where", 20)))
        except passkeys.PasskeyError as exc:
            return _passkey_error(exc)


class PasskeyCheckVerifyView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"

    def post(self, request):
        signed_in = request.user if request.user.is_authenticated else None
        try:
            user = passkeys.finish_check(request, credential=_credential(request), user=signed_in)
        except passkeys.PasskeyError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_401_UNAUTHORIZED)
        if signed_in is None:
            # A passkey with user verification is both factors (ADR-0019): no authenticator-code step.
            request.session.pop(MFA_PENDING_SESSION_KEY, None)
            request.session.set_expiry(None)
            login(request, user)
            audit.record(actor=user, organization_id=None, action="auth.login", context={"method": "passkey"})
        else:
            audit.record(actor=user, organization_id=None, action="auth.passkey_check")
        passkeys.mark_checked(request)
        return Response(UserSerializer(user).data)


class MFARecoveryCodesView(APIView):
    """GET: how many recovery codes are left. POST (a current 6-digit code): 10 new ones, the old ones
    gone."""

    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"

    def get(self, request):
        return Response(
            {"left": services.recovery_codes_left(request.user), "enabled": request.user.mfa_enabled}
        )

    def post(self, request):
        serializer = MFACodeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        code = serializer.validated_data["code"]
        if not (code.isdigit() and services.verify_mfa_code(user=request.user, code=code)):
            return Response({"detail": "invalid code"}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"recovery_codes": services.new_recovery_codes(request.user)})


class PasswordChangeView(APIView):
    """The person changes their own password (their current one, then a new one). Their session stays signed
    in."""

    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"

    def post(self, request):
        from django.contrib.auth import update_session_auth_hash

        serializer = PasswordChangeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            services.change_password(
                user=request.user,
                current=serializer.validated_data["current_password"],
                new=serializer.validated_data["new_password"],
            )
        except services.PasswordError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        update_session_auth_hash(request, request.user)
        return Response(UserSerializer(request.user).data)
