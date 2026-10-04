# Adding an external application (Sign in with IntraForge)

Practical companion to `docs/INTRAFORGE_OIDC_PROVIDER.md` (architecture/
security model) — this is the "how do I register a new app" guide.

## 1. Register the client

Requires a **Super Administrator** session (`system.admin`,
platform-wide — see `docs/architecture` on `RoleAssignment(organization=
None)`). Registering a client is deliberately not organization-scoped:
any enabled client can authenticate any user on the deployment.

```
POST /api/v1/oauth-clients/
{
  "name": "My External App",
  "redirect_uris": ["https://my-app.example.com/auth/callback"],
  "post_logout_redirect_uris": ["https://my-app.example.com/"]
}
```

Response includes `client_id` and, **exactly once**, `client_secret` —
copy it now; it is never retrievable again (only rotatable:
`POST /api/v1/oauth-clients/{id}/rotate-secret/`, same one-time-display
rule).

For local development, register both `http://localhost:<port>/auth/callback`
and `http://127.0.0.1:<port>/auth/callback` — browsers treat those as
different origins for cookies, so pick whichever your app's dev server
actually binds to and keep it consistent everywhere (its own
`INTRAFORGE_REDIRECT_URI` env var included). The Harmoney Spare Parts dev
client already registers both (see
`oauth_provider/migrations/0002_seed_harmoney_spareparts_client.py`).

## 2. Implement the flow (server-side, in your app)

1. **`GET /auth/login`** (your app) — generate `state`, PKCE
   `code_verifier`/`code_challenge` (S256), and (if using OIDC) `nonce`.
   Store them server-side against this browser (e.g. a short-lived
   HttpOnly cookie) and redirect (top-level navigation, not fetch) to:

   ```
   GET https://<intraforge-host>/oauth/authorize
     ?response_type=code
     &client_id=<your client_id>
     &redirect_uri=<your exact registered redirect_uri>
     &scope=openid profile email
     &state=<state>
     &code_challenge=<code_challenge>
     &code_challenge_method=S256
     &nonce=<nonce>
   ```

2. IntraForge shows its own login/register/onboarding if the browser has
   no session, then redirects back to your `redirect_uri` with
   `?code=...&state=...` (or `?error=...&state=...`).

3. **`GET /auth/callback`** (your app) — validate `state` matches what
   you stored, then server-to-server:

   ```
   POST https://<intraforge-host>/oauth/token
   { "grant_type": "authorization_code", "client_id", "client_secret",
     "code", "redirect_uri", "code_verifier" }
   ```

   returns `{access_token, token_type, expires_in, scope, id_token}`.

4. Verify `id_token` (RS256, against `GET /oauth/jwks.json`): `iss`
   equals the IntraForge issuer, `aud` equals your `client_id`, `exp` not
   passed, `nonce` matches what you sent. Its `sub` claim is the durable
   identifier — map/create your own local user record keyed by it, never
   by email.

5. Create your app's own session (HttpOnly cookie) and redirect to
   wherever the user was headed.

A complete, working reference implementation of both sides lives in the
`intraforge-spareparts-demo` project — see its
`docs/SPARE_PARTS_AUTH_INTEGRATION.md` and `src/auth/`.

## 3. Local TLS trust (development only)

IntraForge's dev proxy uses Caddy's own local CA (`tls internal`) — a
server-side `fetch()` from your app to `/oauth/token`/`/oauth/jwks.json`
will fail certificate verification unless your app's Node process trusts
that CA. Export it once and point `NODE_EXTRA_CA_CERTS` at it:

```
docker cp <proxy-container>://data/caddy/pki/authorities/local/root.crt ./local-ca.crt
NODE_EXTRA_CA_CERTS=$(pwd)/local-ca.crt npm run dev
```

Never disable TLS verification (`NODE_TLS_REJECT_UNAUTHORIZED=0`) instead
— it silently accepts *any* certificate, not just this one CA.

## 4. Managing a client afterward

- **Disable** (without deleting): `PATCH /api/v1/oauth-clients/{id}/
  {"enabled": false}` — refused identically at both `/oauth/authorize`
  and `/oauth/token` from that point on.
- **Rotate secret**: `POST /api/v1/oauth-clients/{id}/rotate-secret/` —
  the old secret stops working immediately; update your app's config
  with the new one before or right after.
- **Change redirect URIs**: `PATCH` with a new `redirect_uris` list —
  takes effect immediately; an in-flight authorization request using a
  now-removed URI will fail cleanly at `/oauth/authorize`.
