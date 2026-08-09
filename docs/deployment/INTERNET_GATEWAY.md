# Optional Secure Internet Gateway — Private Data Cloud

Status: Phase 10 — opt-in, off by default; the default deployment
described in [LOCAL_DEPLOYMENT.md](LOCAL_DEPLOYMENT.md) is unaffected by
anything in this document unless you deliberately follow it.
Last updated: 2026-08-09

## 1. Scope and Philosophy

This platform is local-first (CLAUDE.md "Non-Negotiable Architectural
Rules" #7): no internet dependency for normal operation, and external
exposure is opt-in. This document covers the add-on path for
organizations that *do* want to reach the platform from outside their
LAN/VPN — it is explicitly **an add-on to the existing network
architecture, not a redesign of it** (docs/architecture/ROADMAP.md
Phase 10). Nothing about how `backend`, `worker`, `beat`,
`postgres-control`, `postgres-tenant`, `valkey`, or `object-storage`
trust each other on the internal Docker network changes — they are not
reachable from the internet before this, and they are not reachable
from the internet after this either. The only thing that changes is how
the single already-internet-facing component (`proxy`) is configured,
plus two authentication-hardening behaviors in the backend.

**Zero Trust framing**: don't trust the network perimeter as a security
boundary. Every request the backend serves is still authenticated and
authorized exactly as it is today (session cookie or bearer token,
`permissions.services.has_permission` on every fine-grained action,
per-organization tenant isolation) — internet exposure doesn't introduce
a new, weaker code path. What it does add is: a real publicly-trusted
TLS certificate (a browser can't be expected to trust a LAN-only
internal CA), tighter rate limiting on the unauthenticated
login/register/MFA-verify endpoints, and mandatory MFA before any *new*
administrative role grant.

## 2. What Actually Changes

| Area | LAN/default | Internet gateway mode |
|---|---|---|
| TLS issuance | Caddy's internal CA (`tls internal`) — trusted only by clients that import its root, appropriate for same-machine/LAN access | Real ACME (Let's Encrypt) via ordinary domain validation — see `infrastructure/proxy/Caddyfile.internet-gateway` |
| `proxy` port binding | `PROXY_BIND_ADDRESS` (defaults to `127.0.0.1`) — a LAN IP at most | A real public IP/domain; still only the `proxy` service, nothing else |
| Auth endpoint rate limiting | A dedicated `10/minute` `"auth"` throttle scope on `/auth/login/`, `/auth/register/`, and `/auth/mfa/verify/` (`accounts/views.py`, `config/settings/base.py`), tighter than the general `anon`/`user` DRF throttles — these are the endpoints a credential-stuffing/brute-force attempt would actually hit, so this is always on, not gated behind the feature flag | Same — internet exposure is exactly when this matters most, but there's no reason to leave brute-force protection off by default for LAN deployments either |
| Administrative role grants | No MFA requirement | `permissions.services.assign_role` refuses to grant a role carrying `permissions.manage` or `system.admin` to a user without `mfa_enabled=True` — **only** when one *already-authenticated* actor grants the role to *another* user; a user's own org-creation self-bootstrap and CLI (`bootstrap_super_administrator`, an operator with server access, trusted out-of-band) are both exempt, or gateway mode would deadlock a brand-new user out of ever creating their first organization |

Internal service-to-service trust (backend ↔ postgres-control/postgres-
tenant/valkey/object-storage, worker ↔ same) is **not gated by any of
this** — it was never exposed to the internet and remains exactly as
described in ARCHITECTURE.md Section 4.

## 3. Enabling Internet Gateway Mode

1. Set `FEATURE_INTERNET_GATEWAY_ENABLED=True` in `.env`. This alone
   only changes the MFA-required-for-new-admin-grants behavior above —
   it does not open any port or change TLS. (The equivalent flag for
   Phase 9's external sharing, `FEATURE_EXTERNAL_SHARING_ENABLED`, is
   independent — enabling one does not enable the other.)
2. Point a real DNS record at the host and set `PROXY_DOMAIN` and
   `PROXY_ACME_EMAIL` in `.env`.
3. Mount `infrastructure/proxy/Caddyfile.internet-gateway` instead of
   the default `infrastructure/proxy/Caddyfile` — e.g. via a
   `docker-compose.override.yml` (not committed; operator-specific):

   ```yaml
   services:
     proxy:
       volumes:
         - ./infrastructure/proxy/Caddyfile.internet-gateway:/etc/caddy/Caddyfile:ro
       ports:
         - "80:80"
         - "443:443"
   ```

   Port 80 must be reachable for the ACME HTTP-01 challenge; Caddy
   handles the redirect to 443 and certificate renewal automatically.
4. Ensure every existing organization administrator enrolls MFA
   (`POST /api/v1/auth/mfa/enroll/` then `/confirm/` — see
   `docs/api/API.md`) — enabling the flag does **not** retroactively
   revoke or restrict access for administrators assigned before it was
   turned on (see the "Known, deliberately documented limitation" note
   in `docs/architecture/ROADMAP.md` Phase 10); it only gates *new*
   grants going forward. Rotating in MFA-enrolled administrators before
   relying on this protection is an operational step, not something the
   platform can force retroactively without risking locking out the
   only admin of a self-hosted deployment.
5. Put a real firewall in front of the host, restricting inbound traffic
   to ports 80/443 only. Nothing else should ever be internet-reachable
   — this was already true before enabling the gateway (LOCAL_DEPLOYMENT.md
   Section 3: "No service other than `proxy` publishes a port on the
   host's non-loopback interface"), and stays true after.

## 4. Optional: IP-Allowlisting Administrative Routes

For deployments that want defense-in-depth beyond MFA (e.g. restrict
`/api/v1/organizations/*/members/*/role/` and similar administrative
endpoints to a known VPN/office IP range even when the rest of the app
is internet-facing), Caddy's `remote_ip` request matcher can gate a
route without any application code changes:

```caddyfile
@admin_routes {
    path /api/v1/organizations/*/members/*/role/*
}
@trusted_admin_network remote_ip 203.0.113.0/24
handle @admin_routes {
    handle @trusted_admin_network {
        reverse_proxy backend:8000
    }
    respond 403
}
```

This is documented as an optional pattern, not shipped as a default —
the specific routes and trusted ranges are deployment-specific, and a
hardcoded example in the shipped Caddyfile would be actively wrong for
most operators (Section 24 of the master prompt: no unreviewed default
that assumes an operator's specific network).

## 5. What This Phase Does Not Do

- No WAF, no DDoS mitigation service — those are the responsibility of
  whatever sits in front of this host (a cloud load balancer, Cloudflare,
  etc.) if the deployment needs them; out of scope for a self-hosted
  reverse proxy.
- No automatic MFA enrollment reminder/nag system — enrollment is a
  manual step an administrator takes (Section 3, step 4).
- No SSO/OIDC — MFA here is TOTP only (`accounts/totp.py`, RFC 6238),
  matching the master prompt's authentication scope for this phase.
