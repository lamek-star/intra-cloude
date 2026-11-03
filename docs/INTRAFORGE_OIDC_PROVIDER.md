# IntraForge as an OIDC/OAuth 2.1 provider

Closes the gap `docs/SPARE_PARTS_INTEGRATION_READINESS.md` and
`docs/EXTERNAL_APP_API_CONTRACT.md` both documented as missing: IntraForge
previously had no way for a **separately hosted web application** to let
its own end users sign in with their IntraForge identity. Session-cookie
auth is same-origin only; `applications.Application`/`ServiceAccount`
bearer tokens authenticate a *machine* as itself, never a human end user.
`oauth_provider` (new Django app) adds a standards-based Authorization
Code + PKCE flow, with an OpenID Connect identity layer on top, so an
external app (first slice: the Harmoney Spare Parts website) can
authenticate its own users through IntraForge without IntraForge ever
sharing its password store.

## Why a new app, not an extension of `applications`

`applications.Application` is deliberately a different concept:
it is the identity an integration authenticates **as** (backed by its own
dummy `ServiceAccount` → `User` row, unusable password). An OAuth client
is a *relying party* that authenticates **other, real** users — it is
never itself a `User`. Bolting that onto `Application` would conflate two
unrelated principal types the rest of the authorization system (role
assignments, resource grants, membership lookups) already depends on
staying distinct. See `oauth_provider/models.py`'s own docstring.

## Architecture

```
Spare Parts Website (Next.js)          IntraForge (Django)
  /auth/login  ──────────────────────▶  GET /oauth/authorize
                                          │ not authenticated?
                                          ▼
                                         redirect to /login?next=...
                                         (IntraForge's OWN existing
                                          session login/register/welcome
                                          pages — no second login UI)
                                          │ authenticated
                                          ▼
                                         issue single-use code, redirect
  /auth/callback ◀──────────────────────  back to redirect_uri?code&state
   (server-to-server)
  POST /oauth/token  ────────────────▶  validate PKCE + client secret,
                                         issue access_token (+ id_token)
  verify id_token (JWKS)  ◀───────────  GET /oauth/jwks.json
  create local session
```

The browser only ever does full top-level navigations for
`/oauth/authorize` and the redirect back — never a fetch/XHR, so no CORS
configuration is needed for the protocol itself. `/oauth/token` and
`/oauth/userinfo`/`/oauth/revoke` are server-to-server.

## Endpoints

Unversioned, root-level (like `/healthz`), not under `/api/v1/` — see
`oauth_provider/urls.py`'s own docstring and
`infrastructure/proxy/Caddyfile`'s `@backend` matcher (updated to route
`/oauth/*` and `/.well-known/*` to the backend).

| Endpoint | Method | Notes |
|---|---|---|
| `/oauth/authorize` | GET | Session-cookie authenticated; redirects to `/login?next=...` if not. |
| `/oauth/token` | POST | `grant_type=authorization_code` only. `client_id`/`client_secret`/`code`/`redirect_uri`/`code_verifier` in the JSON body. |
| `/oauth/userinfo` | GET | `Authorization: Bearer <access_token>`. |
| `/oauth/revoke` | POST | RFC 7009; always 200. |
| `/oauth/jwks.json` | GET | RSA public key(s), RS256. |
| `/.well-known/openid-configuration` | GET | Standard OIDC discovery document. |

Admin (versioned, `system.admin` permission required — see below):
`GET/POST /api/v1/oauth-clients/`, `GET/PATCH /api/v1/oauth-clients/{id}/`,
`POST /api/v1/oauth-clients/{id}/rotate-secret/`.

## Client registration

`OAuthClient`: `client_id` (public), `client_secret_hash` (SHA-256 hex of
a server-generated secret — never stored plaintext, same convention as
`ApplicationCredential`), `redirect_uris`/`post_logout_redirect_uris`
(exact-match lists, no wildcards), `enabled`, `requires_consent`
(reserved — see below). Only `application_type: confidential_web` exists
today — a client authenticates with `client_secret` **and** PKCE; a
public/SPA client type (PKCE-only, no secret) is a real future addition,
not built until something needs it.

Registering a client is **platform-wide** (any enabled client can
authenticate any user on the deployment) — gated by `system.admin`
(`permissions/catalog.py`), the same permission already reserved for
platform administration, not an organization-scoped one.

The development registration for the spare-parts project is seeded by
`oauth_provider/migrations/0002_seed_harmoney_spareparts_client.py` — a
real, reviewable migration rather than an ad-hoc admin-API call, so
`docker compose up` produces a working client with no manual step. Its
secret is printed once, at migration time, to `docker compose logs`; if
lost, rotate it via the admin API instead of re-running the migration.

## Authorization Code + PKCE

- PKCE `S256` only — `plain` is never accepted (`services.py:verify_pkce`
  hard-refuses anything but S256), matching this deployment's own
  security requirement, not just the OAuth 2.1 recommendation.
- No implicit flow, no arbitrary redirect URI: `redirect_uri` must
  exactly match one of the client's registered URIs (`https`, or `http`
  for `localhost`/`127.0.0.1` only) before *anything else* is validated —
  an unregistered or malformed `redirect_uri` never gets redirected to at
  all (`AuthorizeView._error_page`), which is the actual open-redirect
  defense; every other validation failure (`invalid_scope`,
  `unsupported_response_type`, missing/weak PKCE) is reported *to* the
  now-trusted `redirect_uri` via `?error=...`, per spec.
- Authorization codes: random (32 bytes), stored only as a SHA-256 hash,
  120-second TTL, single-use (`used_at` set atomically before any token
  is minted), bound to `client` + exact `redirect_uri` + PKCE challenge +
  `user`. A replayed, expired, wrong-client, or wrong-redirect-uri code
  is `invalid_grant` in every case — see
  `oauth_provider/tests/test_oauth_flow.py` for the exhaustive matrix.

## Tokens

- **`access_token`**: opaque (not a JWT), SHA-256-hashed at rest — the
  same shape as `ApplicationCredential`. Deliberately **not** a JWT:
  there is no resource server other than IntraForge's own
  `/oauth/userinfo` that would need to verify it offline. 10-minute TTL,
  **no refresh token** — the spare-parts backend exchanges the code once,
  reads the ID token, and mints its *own* long-lived local session from
  that; it never needs this token again (and best-effort revokes it
  immediately after use — see the spare-parts side's callback). Adding
  refresh-token issuance/rotation/revocation was judged not worth the
  extra attack surface for a token that is used exactly once, per this
  project's own "prefer short-lived access tokens" / "refresh tokens
  only if truly necessary" guidance.
- **`id_token`**: a real signed JWT (RS256) — the one token here with a
  genuine offline-verification need. Claims: `sub` (the user's own
  immutable UUID — **never** email), `email`/`name`/`given_name` (only
  if `email`/`profile` scope was requested), `iss`, `aud` (=`client_id`),
  `iat`, `exp`, `nonce` (echoed back if the client sent one). **No
  organization claim, ever** — see below.

## Signing key / JWKS

`OAuthSigningKey`: a 2048-bit RSA keypair, generated lazily on first use
(both `/oauth/token` and `/oauth/jwks.json` call the same
`get_active_signing_key()`), private half Fernet-encrypted at rest using
the existing `CREDENTIAL_ENCRYPTION_KEY` (same pattern as
`accounts/crypto.py`'s MFA-secret encryption — no new secret to
provision). `/oauth/jwks.json` publishes every key row, not just the
active one, so a token signed just before a rotation remains verifiable;
rotating (creating a new active key, retiring the old one in the DB) is
supported by the model but has no scheduled/automatic trigger yet — a
management command for manual rotation is a reasonable, easy follow-up,
not built in this pass since nothing yet requires it.

## Org-less users

Organization membership plays **no role** in identity here. `sub` is
computed once, from the `User` row's own immutable UUID
(`userinfo_claims`), independent of whether that user has zero, one, or
several organizations — verified directly:
`test_sub_is_unchanged_after_the_user_later_creates_an_organization`
exchanges a code before and after the same user creates an organization
and asserts the `sub` claim is identical. No `org`/`organization`/`org_id`
claim is ever included, for any user — this is deliberate, not an
omission for org-less users specifically: business/organization
authorization is the spare-parts application's own concern, answered
through IntraForge's *existing* org-scoped App Platform/bearer-token
surface (`EXTERNAL_APP_API_CONTRACT.md`), never folded into end-user
identity claims. "Who is this user" and "what may this user do in the
spare-parts application" stay two separate questions on purpose.

## Consent

`OAuthClient.requires_consent` exists but is always `False` today — every
registered client is implicitly first-party/trusted (only an enabled,
registered client can reach `/oauth/authorize` at all). A real consent
screen is a schema-compatible future addition, not built now because
nothing yet needs it.

## Logout

IntraForge itself gained no new logout endpoint — a customer signing out
of the spare-parts site ends *that app's own* local session
(`docs/SPARE_PARTS_AUTH_INTEGRATION.md`); it does not also end their
IntraForge identity session, and IntraForge's own session cookie isn't
reachable from a different origin/app anyway. `post_logout_redirect_uris`
is stored on every `OAuthClient` for a future RP-initiated logout
(`/accounts/auth/logout/` redirecting to a registered post-logout URI)
but nothing calls it yet — deferred, not missing by oversight.

## Security checklist

- [x] PKCE S256 required, `plain` rejected
- [x] Exact-match `redirect_uri`, no wildcard, `javascript:`/`data:`
      rejected at registration time too
- [x] Authorization code: random, hashed at rest, single-use, short-lived,
      bound to client/redirect_uri/PKCE/user
- [x] `client_secret`: random, hashed at rest (never plaintext), never
      exposed after creation/rotation
- [x] `id_token`: real RS256 signature, `iss`/`aud`/`exp`/`nonce`
      verified by the client (spare-parts side) against the published
      JWKS
- [x] `sub` is an immutable UUID, never email
- [x] No org claim invented for org-less (or any) user
- [x] Disabled client refused identically to an unknown one, at both
      `/oauth/authorize` and `/oauth/token`
- [x] `/oauth/userinfo` never runs through the platform's own
      `ServiceAccountAuthentication` (would misparse the same
      `Authorization: Bearer` header as one of *its* tokens — see
      `UserInfoView`'s docstring) — `authentication_classes = []`,
      handled manually
- [ ] Refresh tokens — deliberately not implemented (see Tokens above)
- [ ] Automatic/scheduled key rotation — supported by the model, not yet
      automated
- [ ] RP-initiated (global) logout — deferred, see Logout above

## Tests

`oauth_provider/tests/test_oauth_flow.py` (22 tests) and
`test_admin.py` (8 tests) — see the repo's own test output for the exact
run; summarized in the integration's final report
(`docs/SPARE_PARTS_AUTH_INTEGRATION.md`).
