# Reverse Proxy Configuration

Caddy, configured via `Caddyfile` in this directory. TLS termination
(local-CA-issued cert via `tls internal`), security headers, and routing:
`/api/*`, `/healthz`, `/readyz` → backend; everything else → frontend. See
`docs/deployment/LOCAL_DEPLOYMENT.md` Section 6 and
`docs/architecture/ARCHITECTURE.md` Section 4 for the reasoning.

Not yet validated against a running Caddy instance (this development
environment doesn't have Docker/Caddy installed) — run `caddy validate
--config infrastructure/proxy/Caddyfile` as an early Phase 2 step, or let
`docker compose up proxy` surface any config error directly.

Rate limiting is not yet configured here (Caddy needs the `rate_limit`
module, which isn't in the base image) — tracked as Phase 10/11 work when
the platform gains real internet-facing endpoints worth rate-limiting at
the edge; `system.REST_FRAMEWORK` throttle classes already provide
application-level rate limiting in the meantime (see
`apps/backend/config/settings/base.py`).
