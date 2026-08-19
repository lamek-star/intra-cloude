from django.contrib.auth import authenticate, login, logout
from django.middleware.csrf import get_token
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from audit import services as audit
from audit.models import AuditEvent

from . import services
from .models import User
from .serializers import LoginSerializer, MFACodeSerializer, RegisterSerializer, UserSerializer

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
    authentication_classes = []

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
            return Response(
                {"detail": "Invalid credentials."}, status=status.HTTP_401_UNAUTHORIZED
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
            return Response(
                {"detail": "No MFA login in progress."}, status=status.HTTP_400_BAD_REQUEST
            )

        serializer = MFACodeSerializer(data=request.data)
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
        result = services.start_mfa_enrollment(user=request.user)
        return Response(result, status=status.HTTP_201_CREATED)


class MFAConfirmView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = MFACodeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            services.confirm_mfa_enrollment(user=request.user, code=serializer.validated_data["code"])
        except services.MFAError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(UserSerializer(request.user).data)


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
