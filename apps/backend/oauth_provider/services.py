"""
Business logic for the Authorization Code + PKCE (+ OIDC) flow. Views
stay thin — every rule the OAuth/OIDC spec and this project's own
security requirements impose lives here, so it is exercised identically
whether called from `views.py` or a test.
"""

from __future__ import annotations

import base64
import hashlib
from dataclasses import dataclass
from urllib.parse import urlsplit

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from django.conf import settings
from django.utils import timezone

from .crypto import decrypt_secret, encrypt_secret, generate_token, hash_token
from .models import OAuthAccessToken, OAuthAuthorizationCode, OAuthClient, OAuthSigningKey

AUTHORIZATION_CODE_TTL_SECONDS = 120
ACCESS_TOKEN_TTL_SECONDS = 600
ID_TOKEN_TTL_SECONDS = 600
SUPPORTED_SCOPES = {"openid", "profile", "email"}
CLIENT_ID_PREFIX = "ifc_"  # "IntraForge Client" — mirrors ApplicationCredential's `pdc_sk_` convention.


class OAuthError(Exception):
    """Carries an OAuth2 `error` code (RFC 6749 Section 5.2/4.1.2.1) plus
    a human description. Views translate this into the correct response
    shape — a JSON body for the token endpoint, a query-string redirect
    for the authorize endpoint once redirect_uri itself is trusted."""

    def __init__(self, error: str, description: str = ""):
        self.error = error
        self.description = description
        super().__init__(f"{error}: {description}")


# --- Redirect URI / client validation -----------------------------------


def validate_redirect_uri(client: OAuthClient, redirect_uri: str) -> bool:
    """Exact match only — never a prefix or wildcard. `javascript:`/
    `data:` and any scheme other than https (or http for localhost, dev
    only) are rejected outright regardless of the registered list, so a
    misconfigured registration can never itself become an open redirect
    or script-injection vector."""
    if not redirect_uri or redirect_uri not in client.redirect_uris:
        return False
    parsed = urlsplit(redirect_uri)
    if parsed.scheme == "https":
        return True
    if parsed.scheme == "http" and parsed.hostname in ("localhost", "127.0.0.1"):
        return True
    return False


def get_enabled_client(client_id: str) -> OAuthClient | None:
    try:
        client = OAuthClient.objects.get(client_id=client_id)
    except OAuthClient.DoesNotExist:
        return None
    return client if client.enabled else None


# --- Client registration (admin) ----------------------------------------


def create_client(
    *, name: str, redirect_uris: list[str], post_logout_redirect_uris: list[str] | None = None,
    allowed_origins: list[str] | None = None, created_by=None,
) -> tuple[OAuthClient, str]:
    """Returns (client, plaintext_secret) — the plaintext is never stored;
    only this call site and rotate_client_secret ever see it."""
    client_id = CLIENT_ID_PREFIX + generate_token(16)
    secret = generate_token(32)
    client = OAuthClient.objects.create(
        name=name,
        client_id=client_id,
        client_secret_hash=hash_token(secret),
        redirect_uris=redirect_uris,
        post_logout_redirect_uris=post_logout_redirect_uris or [],
        allowed_origins=allowed_origins or [],
        created_by=created_by,
    )
    return client, secret


def rotate_client_secret(client: OAuthClient) -> str:
    secret = generate_token(32)
    client.client_secret_hash = hash_token(secret)
    client.save(update_fields=["client_secret_hash", "updated_at"])
    return secret


def verify_client_secret(client: OAuthClient, secret: str) -> bool:
    if not secret:
        return False
    return hash_token(secret) == client.client_secret_hash


# --- PKCE ------------------------------------------------------------------


def compute_s256_challenge(code_verifier: str) -> str:
    digest = hashlib.sha256(code_verifier.encode()).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode()


def verify_pkce(*, code_challenge: str, code_challenge_method: str, code_verifier: str) -> bool:
    if code_challenge_method != "S256":
        # RFC 7636 `plain` is deliberately never accepted (per this
        # project's own security requirement) — the only valid method is
        # S256; anything else is treated as a verification failure, not
        # silently downgraded.
        return False
    if not code_verifier:
        return False
    return compute_s256_challenge(code_verifier) == code_challenge


# --- Authorization code ----------------------------------------------------


def issue_authorization_code(
    *, client: OAuthClient, user, redirect_uri: str, scope: str,
    code_challenge: str, code_challenge_method: str, nonce: str,
) -> str:
    code = generate_token(32)
    OAuthAuthorizationCode.objects.create(
        code_hash=hash_token(code),
        client=client,
        user=user,
        redirect_uri=redirect_uri,
        scope=scope,
        code_challenge=code_challenge,
        code_challenge_method=code_challenge_method,
        nonce=nonce,
        expires_at=timezone.now() + timezone.timedelta(seconds=AUTHORIZATION_CODE_TTL_SECONDS),
    )
    return code


@dataclass
class TokenResponse:
    access_token: str
    token_type: str
    expires_in: int
    scope: str
    id_token: str | None


def exchange_authorization_code(
    *, client_id: str, client_secret: str, code: str, redirect_uri: str, code_verifier: str,
) -> TokenResponse:
    """Every failure mode raises OAuthError with the exact RFC 6749
    error code — deliberately checked in an order that never leaks which
    specific thing was wrong beyond what the spec already exposes (e.g.
    an unknown vs. disabled client both read as `invalid_client`)."""
    client = get_enabled_client(client_id)
    if client is None or not verify_client_secret(client, client_secret):
        raise OAuthError("invalid_client", "Unknown, disabled, or unauthenticated client.")

    code_hash = hash_token(code)
    try:
        auth_code = OAuthAuthorizationCode.objects.select_related("user").get(
            code_hash=code_hash, client=client
        )
    except OAuthAuthorizationCode.DoesNotExist:
        raise OAuthError("invalid_grant", "Unknown authorization code for this client.")

    # Single-use: a code already marked used is treated exactly like one
    # that never existed — replaying a captured code never succeeds, and
    # (RFC 6749 Section 4.1.2) a reused code SHOULD revoke tokens already
    # issued from it; this deployment issues no refresh token to revoke,
    # so `used_at` alone is a complete defense against replay here.
    if auth_code.used_at is not None:
        raise OAuthError("invalid_grant", "Authorization code already used.")
    if auth_code.expires_at < timezone.now():
        raise OAuthError("invalid_grant", "Authorization code expired.")
    if auth_code.redirect_uri != redirect_uri:
        raise OAuthError("invalid_grant", "redirect_uri does not match the authorization request.")
    if not verify_pkce(
        code_challenge=auth_code.code_challenge,
        code_challenge_method=auth_code.code_challenge_method,
        code_verifier=code_verifier,
    ):
        raise OAuthError("invalid_grant", "PKCE verification failed.")

    # Mark used immediately, before minting anything — if token creation
    # somehow failed after this point, the code must still never be
    # exchangeable again.
    auth_code.used_at = timezone.now()
    auth_code.save(update_fields=["used_at"])

    access_token = generate_token(32)
    OAuthAccessToken.objects.create(
        token_hash=hash_token(access_token),
        client=client,
        user=auth_code.user,
        scope=auth_code.scope,
        expires_at=timezone.now() + timezone.timedelta(seconds=ACCESS_TOKEN_TTL_SECONDS),
    )

    id_token = None
    if "openid" in auth_code.scope.split():
        id_token = issue_id_token(client=client, user=auth_code.user, nonce=auth_code.nonce, scope=auth_code.scope)

    return TokenResponse(
        access_token=access_token,
        token_type="Bearer",
        expires_in=ACCESS_TOKEN_TTL_SECONDS,
        scope=auth_code.scope,
        id_token=id_token,
    )


# --- Access tokens -----------------------------------------------------------


def resolve_access_token(token: str) -> OAuthAccessToken | None:
    try:
        access_token = OAuthAccessToken.objects.select_related("user", "client").get(
            token_hash=hash_token(token)
        )
    except OAuthAccessToken.DoesNotExist:
        return None
    if access_token.revoked_at is not None:
        return None
    if access_token.expires_at < timezone.now():
        return None
    return access_token


def revoke_access_token(token: str) -> bool:
    access_token = resolve_access_token(token)
    if access_token is None:
        return False
    access_token.revoked_at = timezone.now()
    access_token.save(update_fields=["revoked_at"])
    return True


# --- Claims ------------------------------------------------------------------


def userinfo_claims(user, scope: str) -> dict:
    """`sub` is always the user's own immutable UUID — never email (the
    module docstring's own explicit requirement: email can change,
    `sub` never does, and this stays stable even if the user later
    creates or joins an organization, since organization membership
    plays no part in identity at all here). No organization claim is
    ever included — for an org-less user there is nothing to omit in
    the first place; for one who later gets an organization, this
    endpoint still doesn't describe org membership, deliberately: that
    is the spare-parts application's own authorization concern, backed
    by IntraForge's ordinary org/App Platform API with its own bearer
    credential, not something to fold into end-user identity claims."""
    scopes = set(scope.split())
    claims: dict = {"sub": str(user.id)}
    if "email" in scopes:
        claims["email"] = user.email
    if "profile" in scopes:
        claims["name"] = user.get_full_name()
        claims["given_name"] = user.first_name
    return claims


# --- OIDC signing key / ID token ---------------------------------------------


def _generate_signing_key() -> OAuthSigningKey:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    public_pem = (
        private_key.public_key()
        .public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        .decode()
    )
    OAuthSigningKey.objects.filter(active=True).update(active=False)
    return OAuthSigningKey.objects.create(
        private_key_encrypted=encrypt_secret(private_pem),
        public_key_pem=public_pem,
        active=True,
    )


def get_active_signing_key() -> OAuthSigningKey:
    key = OAuthSigningKey.objects.filter(active=True).order_by("-created_at").first()
    return key if key is not None else _generate_signing_key()


def _b64url_uint(value: int) -> str:
    length = (value.bit_length() + 7) // 8
    return base64.urlsafe_b64encode(value.to_bytes(length, "big")).rstrip(b"=").decode()


def jwks() -> dict:
    """Every non-superseded key still published (see OAuthSigningKey's
    own docstring on why retired keys are kept, not deleted, at
    rotation time) — a client that cached an id_token signed by the
    previous key can still verify it during this deployment's own
    documented rotation-overlap window. Ensures a key exists (same
    lazy-generation as issue_id_token) so a client that checks discovery/
    JWKS before ever completing a token exchange still sees a real key,
    not an empty set."""
    get_active_signing_key()
    keys = []
    for signing_key in OAuthSigningKey.objects.all():
        public_key = serialization.load_pem_public_key(signing_key.public_key_pem.encode())
        numbers = public_key.public_numbers()
        keys.append(
            {
                "kty": "RSA",
                "use": "sig",
                "alg": signing_key.algorithm,
                "kid": str(signing_key.id),
                "n": _b64url_uint(numbers.n),
                "e": _b64url_uint(numbers.e),
            }
        )
    return {"keys": keys}


def issue_id_token(*, client: OAuthClient, user, nonce: str, scope: str) -> str:
    signing_key = get_active_signing_key()
    private_pem = decrypt_secret(bytes(signing_key.private_key_encrypted))
    now = timezone.now()
    claims = {
        "iss": settings.OIDC_ISSUER,
        "aud": client.client_id,
        "iat": int(now.timestamp()),
        "exp": int((now + timezone.timedelta(seconds=ID_TOKEN_TTL_SECONDS)).timestamp()),
        **userinfo_claims(user, scope),
    }
    if nonce:
        claims["nonce"] = nonce
    return jwt.encode(claims, private_pem, algorithm=signing_key.algorithm, headers={"kid": str(signing_key.id)})
