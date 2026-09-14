from urllib.parse import quote, urlencode

from django.conf import settings
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from audit import services as audit
from audit.models import AuditEvent
from permissions.services import has_permission

from . import services
from .models import OAuthClient
from .serializers import OAuthClientCreateSerializer, OAuthClientSerializer

SUPPORTED_RESPONSE_TYPES = {"code"}


def _redirect_with_params(base_url: str, params: dict) -> HttpResponseRedirect:
    clean = {k: v for k, v in params.items() if v not in (None, "")}
    return HttpResponseRedirect(f"{base_url}?{urlencode(clean)}")


def _error_page(title: str, detail: str, http_status: int) -> HttpResponse:
    """A plain, safe response for the cases where the redirect_uri itself
    is the thing that failed validation — redirecting the browser
    anywhere in that situation would be exactly the open-redirect this
    endpoint exists to prevent, so this never contains a stack trace or
    any internal detail beyond the one validation fact."""
    return HttpResponse(f"<h1>{title}</h1><p>{detail}</p>", status=http_status, content_type="text/html")


class AuthorizeView(APIView):
    """`GET /oauth/authorize` — RFC 6749 Section 4.1.1 / OIDC Core
    Section 3.1.2.1. Reuses the *existing* session-cookie login/register
    pages verbatim for the "user must authenticate" step (redirecting to
    `/login?next=<this-request>`, which already round-trips through
    `/welcome` for a brand-new user) rather than building a second login
    UI inside the OAuth flow — see docs/INTRAFORGE_OIDC_PROVIDER.md."""

    permission_classes = [AllowAny]

    def get(self, request):
        client_id = request.GET.get("client_id", "")
        redirect_uri = request.GET.get("redirect_uri", "")
        client = services.get_enabled_client(client_id)
        if client is None:
            return _error_page("Unknown application", "This client is not registered or is disabled.", 400)
        if not services.validate_redirect_uri(client, redirect_uri):
            return _error_page(
                "Invalid redirect", "redirect_uri is not registered for this application.", 400
            )

        # redirect_uri is now trusted -- every error from here on is
        # reported to the client via redirect, per spec, instead of
        # rendered in-app.
        state = request.GET.get("state", "")
        response_type = request.GET.get("response_type", "")
        code_challenge = request.GET.get("code_challenge", "")
        code_challenge_method = request.GET.get("code_challenge_method", "")
        nonce = request.GET.get("nonce", "")
        requested_scopes = set(request.GET.get("scope", "").split())

        if response_type not in SUPPORTED_RESPONSE_TYPES:
            return _redirect_with_params(
                redirect_uri, {"error": "unsupported_response_type", "state": state}
            )
        if code_challenge_method != "S256" or not code_challenge:
            return _redirect_with_params(
                redirect_uri, {"error": "invalid_request", "error_description": "PKCE S256 is required.", "state": state}
            )
        if not requested_scopes or not requested_scopes.issubset(services.SUPPORTED_SCOPES):
            return _redirect_with_params(redirect_uri, {"error": "invalid_scope", "state": state})

        if not request.user.is_authenticated:
            login_next = f"{request.path}?{request.META.get('QUERY_STRING', '')}"
            return HttpResponseRedirect(f"/login?next={quote(login_next, safe='')}")

        scope = " ".join(sorted(requested_scopes))
        code = services.issue_authorization_code(
            client=client,
            user=request.user,
            redirect_uri=redirect_uri,
            scope=scope,
            code_challenge=code_challenge,
            code_challenge_method=code_challenge_method,
            nonce=nonce,
        )
        audit.record(
            actor=request.user,
            organization_id=None,
            action="oauth.authorize",
            resource_type="oauth_client",
            resource_id=client.id,
        )
        return _redirect_with_params(redirect_uri, {"code": code, "state": state})


class TokenView(APIView):
    """`POST /oauth/token` — server-to-server (the spare-parts Next.js
    backend, never the browser). Accepts the client credentials in the
    POST body (widely supported alongside HTTP Basic; simpler for a
    fetch()-based caller) rather than requiring Basic auth."""

    permission_classes = [AllowAny]
    # Never DRF's default authenticators (SessionAuthentication -- pointless
    # server-to-server; ServiceAccountAuthentication -- would misparse this
    # endpoint's unrelated `Authorization` semantics, see UserInfoView).
    authentication_classes: list = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"

    def post(self, request):
        data = request.data
        if data.get("grant_type") != "authorization_code":
            return Response(
                {"error": "unsupported_grant_type"}, status=status.HTTP_400_BAD_REQUEST
            )
        try:
            result = services.exchange_authorization_code(
                client_id=data.get("client_id", ""),
                client_secret=data.get("client_secret", ""),
                code=data.get("code", ""),
                redirect_uri=data.get("redirect_uri", ""),
                code_verifier=data.get("code_verifier", ""),
            )
        except services.OAuthError as exc:
            audit.record(
                actor=None,
                organization_id=None,
                action="oauth.token_exchange",
                result=AuditEvent.Result.DENIED,
                context={"error": exc.error},
            )
            return Response(
                {"error": exc.error, "error_description": exc.description}, status=status.HTTP_400_BAD_REQUEST
            )

        body = {
            "access_token": result.access_token,
            "token_type": result.token_type,
            "expires_in": result.expires_in,
            "scope": result.scope,
        }
        if result.id_token:
            body["id_token"] = result.id_token
        audit.record(actor=None, organization_id=None, action="oauth.token_exchange")
        return Response(body)


class UserInfoView(APIView):
    """`GET /oauth/userinfo` — OIDC Core Section 5.3. Bearer-token
    authenticated independently of DRF's configured authentication
    classes (this token is this app's own opaque OAuthAccessToken, not a
    Django session or an ApplicationCredential). `authentication_classes`
    is deliberately empty: DRF's own ServiceAccountAuthentication also
    matches an `Authorization: Bearer <token>` header and would try (and
    fail) to resolve this endpoint's opaque OAuth token as one of ITS
    tokens, turning a clean 401 into a DRF-internal 403."""

    permission_classes = [AllowAny]
    authentication_classes: list = []

    def get(self, request):
        header = request.META.get("HTTP_AUTHORIZATION", "")
        if not header.startswith("Bearer "):
            return Response({"error": "invalid_token"}, status=status.HTTP_401_UNAUTHORIZED)
        access_token = services.resolve_access_token(header[len("Bearer "):].strip())
        if access_token is None:
            return Response({"error": "invalid_token"}, status=status.HTTP_401_UNAUTHORIZED)
        return Response(services.userinfo_claims(access_token.user, access_token.scope))


class RevokeView(APIView):
    """`POST /oauth/revoke` — RFC 7009. Always 200 regardless of whether
    the token existed/was already revoked (Section 2.2: don't let the
    response distinguish an invalid token from a successfully revoked
    one)."""

    permission_classes = [AllowAny]
    authentication_classes: list = []

    def post(self, request):
        token = request.data.get("token", "")
        if token:
            services.revoke_access_token(token)
        return Response(status=status.HTTP_200_OK)


class JWKSView(APIView):
    permission_classes = [AllowAny]
    authentication_classes: list = []

    def get(self, request):
        return JsonResponse(services.jwks())


class OpenIDConfigurationView(APIView):
    permission_classes = [AllowAny]
    authentication_classes: list = []

    def get(self, request):
        issuer = settings.OIDC_ISSUER
        return JsonResponse(
            {
                "issuer": issuer,
                "authorization_endpoint": f"{issuer}/oauth/authorize",
                "token_endpoint": f"{issuer}/oauth/token",
                "userinfo_endpoint": f"{issuer}/oauth/userinfo",
                "revocation_endpoint": f"{issuer}/oauth/revoke",
                "jwks_uri": f"{issuer}/oauth/jwks.json",
                "response_types_supported": ["code"],
                "grant_types_supported": ["authorization_code"],
                "subject_types_supported": ["public"],
                "id_token_signing_alg_values_supported": ["RS256"],
                "scopes_supported": sorted(services.SUPPORTED_SCOPES),
                "token_endpoint_auth_methods_supported": ["client_secret_post"],
                "code_challenge_methods_supported": ["S256"],
                "claims_supported": ["sub", "email", "name", "given_name"],
            }
        )


# --- Admin: OAuth client registration (system.admin, platform-wide) --------


def _require_system_admin(request):
    if not has_permission(request.user, "system.admin", organization_id=None):
        return Response(status=status.HTTP_403_FORBIDDEN)
    return None


class OAuthClientListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        denied = _require_system_admin(request)
        if denied:
            return denied
        clients = OAuthClient.objects.all()
        return Response(OAuthClientSerializer(clients, many=True).data)

    def post(self, request):
        denied = _require_system_admin(request)
        if denied:
            return denied
        serializer = OAuthClientCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        client, secret = services.create_client(
            name=serializer.validated_data["name"],
            redirect_uris=serializer.validated_data["redirect_uris"],
            post_logout_redirect_uris=serializer.validated_data.get("post_logout_redirect_uris", []),
            allowed_origins=serializer.validated_data.get("allowed_origins", []),
            created_by=request.user,
        )
        audit.record(
            actor=request.user, organization_id=None, action="oauth_client.create",
            resource_type="oauth_client", resource_id=client.id,
        )
        body = OAuthClientSerializer(client).data
        body["client_secret"] = secret  # shown exactly once
        return Response(body, status=status.HTTP_201_CREATED)


class OAuthClientDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, client_pk):
        denied = _require_system_admin(request)
        if denied:
            return denied
        client = _get_client_or_404(client_pk)
        if client is None:
            return Response(status=status.HTTP_404_NOT_FOUND)
        return Response(OAuthClientSerializer(client).data)

    def patch(self, request, client_pk):
        denied = _require_system_admin(request)
        if denied:
            return denied
        client = _get_client_or_404(client_pk)
        if client is None:
            return Response(status=status.HTTP_404_NOT_FOUND)
        serializer = OAuthClientSerializer(client, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        audit.record(
            actor=request.user, organization_id=None, action="oauth_client.update",
            resource_type="oauth_client", resource_id=client.id,
        )
        return Response(OAuthClientSerializer(client).data)


class OAuthClientRotateSecretView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, client_pk):
        denied = _require_system_admin(request)
        if denied:
            return denied
        client = _get_client_or_404(client_pk)
        if client is None:
            return Response(status=status.HTTP_404_NOT_FOUND)
        secret = services.rotate_client_secret(client)
        audit.record(
            actor=request.user, organization_id=None, action="oauth_client.rotate_secret",
            resource_type="oauth_client", resource_id=client.id,
        )
        return Response({"client_secret": secret})


def _get_client_or_404(client_pk):
    return OAuthClient.objects.filter(pk=client_pk).first()
