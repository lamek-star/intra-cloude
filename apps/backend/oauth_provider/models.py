"""
OAuth 2.1-style Authorization Code + PKCE, with an OpenID Connect layer on
top — the identity-provider surface for *external* applications (e.g. the
Harmoney Spare Parts website) that need "Sign in with IntraForge", as
distinct from two existing, deliberately different mechanisms:

- `accounts` session-cookie auth: same-origin only, IntraForge's own
  Next.js frontend (docs/EXTERNAL_APP_API_CONTRACT.md's own words: "not
  the recommended mechanism for a separately hosted frontend").
- `applications.Application`/`ServiceAccount`/`ApplicationCredential`:
  a *machine* identity an integration authenticates AS (backed by its
  own dummy `User` row) — the right shape for a backend pulling/pushing
  App Platform records as itself, the wrong shape for "let a real human
  end user sign into a third-party website using their IntraForge
  identity". `OAuthClient` below is a *relying party* that authenticates
  OTHER users; it is never itself a `User`/`ServiceAccount`, so it is
  deliberately its own model rather than an extension of `Application`.

Registering an OAuthClient is a platform-wide capability (any registered,
enabled client can authenticate ANY user on the deployment, not just one
organization's members) — gated by `system.admin`, the same permission
already reserved for platform-wide administration, not an
organization-scoped one.
"""

import uuid

from django.conf import settings
from django.db import models


class OAuthClient(models.Model):
    class ApplicationType(models.TextChoices):
        # Only a server-side, secret-holding relying party is supported
        # today (exactly the spare-parts Next.js backend's shape). A
        # public/SPA client type (no secret, PKCE-only) is a real,
        # separate future addition — deliberately not built until an
        # actual public client needs it, per this project's own
        # "don't build capability nothing calls yet" convention.
        CONFIDENTIAL_WEB = "confidential_web", "Confidential web application"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    client_id = models.CharField(max_length=64, unique=True, editable=False)
    # SHA-256 hex, exactly ApplicationCredential's convention (Section 13
    # of the master prompt: a high-entropy server-generated secret needs
    # collision/lookup resistance, not slow-hash brute-force resistance).
    client_secret_hash = models.CharField(max_length=64)
    application_type = models.CharField(
        max_length=32, choices=ApplicationType.choices, default=ApplicationType.CONFIDENTIAL_WEB
    )
    # Exact-match only, never a prefix/wildcard (see services.py
    # validate_redirect_uri). Stored as a list of strings.
    redirect_uris = models.JSONField(default=list)
    post_logout_redirect_uris = models.JSONField(default=list, blank=True)
    allowed_origins = models.JSONField(default=list, blank=True)
    enabled = models.BooleanField(default=True)
    # Reserved for a future real consent screen (see the module
    # docstring) — every currently-registered client is implicitly
    # trusted/first-party, so this is always False today, but the field
    # exists so introducing consent later doesn't need a schema change.
    requires_consent = models.BooleanField(default=False)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="oauth_clients_created",
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class OAuthAuthorizationCode(models.Model):
    """Single-use, short-lived (services.py: `AUTHORIZATION_CODE_TTL_SECONDS`).
    The plaintext code is returned to the client exactly once, in the
    redirect — only its hash is stored, same rationale as
    ApplicationCredential/the code itself is never sensitive-data-bearing:
    it is a random lookup key, not a signed/encoded claim carrier."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code_hash = models.CharField(max_length=64, unique=True)
    client = models.ForeignKey(OAuthClient, on_delete=models.CASCADE, related_name="authorization_codes")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+")
    redirect_uri = models.CharField(max_length=2048)
    scope = models.CharField(max_length=500, blank=True)
    code_challenge = models.CharField(max_length=128)
    code_challenge_method = models.CharField(max_length=16, default="S256")
    nonce = models.CharField(max_length=255, blank=True)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"authorization code for {self.client} / {self.user}"


class OAuthAccessToken(models.Model):
    """Opaque, server-validated bearer token — the same shape as
    ApplicationCredential rather than a JWT, deliberately: this token is
    looked up and checked (expiry/revocation) on every use, exactly like
    the platform's existing bearer-token mechanism, and there is no
    resource server other than IntraForge's own `/oauth/userinfo/` that
    would need to verify it offline. The `id_token` (models.py has no
    row for it — see services.py `issue_id_token`) is the one token in
    this flow with a real offline-verification need (the spare-parts
    backend must check it without calling back into IntraForge), so it
    alone is a signed JWT. No refresh token is issued: the spare-parts
    backend exchanges the code once, reads `/oauth/userinfo/` (or just
    the ID token) immediately, and mints its OWN long-lived local
    session from that — this access token only needs to survive that one
    round trip, so a short, non-renewable lifetime (see
    ACCESS_TOKEN_TTL_SECONDS) is the deliberately simpler, smaller-attack-
    surface choice over adding refresh-token rotation/revocation."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    token_hash = models.CharField(max_length=64, unique=True)
    client = models.ForeignKey(OAuthClient, on_delete=models.CASCADE, related_name="access_tokens")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+")
    scope = models.CharField(max_length=500, blank=True)
    expires_at = models.DateTimeField()
    revoked_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"access token for {self.client} / {self.user}"


class OAuthSigningKey(models.Model):
    """RSA keypair used to sign `id_token` JWTs (RS256). The private key
    is Fernet-encrypted at rest (oauth_provider/crypto.py, same pattern
    as accounts/crypto.py's MFA-secret encryption, keyed by the existing
    CREDENTIAL_ENCRYPTION_KEY — no new secret to provision). `kid` is
    this row's own id, published in the JWKS alongside the public key so
    a client can select the right key after rotation; `active` marks the
    one key new tokens are signed with, while older, still-`active=False`
    keys remain published (until deliberately deleted) so a JWKS consumer
    can still verify a token issued just before a rotation."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    private_key_encrypted = models.BinaryField()
    public_key_pem = models.TextField()
    algorithm = models.CharField(max_length=16, default="RS256")
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"OIDC signing key {self.id} ({'active' if self.active else 'retired'})"
