# Local Deployment Guide — Private Data Cloud

Status: VERIFIED (Phase 1 — the full bring-up sequence below (build,
migrate, `docker compose up`, request through the proxy over TLS) was
actually run end-to-end on 2026-08-08 and works. See
`docs/architecture/DEPENDENCY_VERSIONS.md` and
`docs/architecture/ROADMAP.md` Phase 1 for the bugs that surfaced and were
fixed along the way — the steps below already reflect the fixes.)
Last updated: 2026-08-08

## 1. Scope

This guide covers running Private Data Cloud on a single private-network
host (a home lab server, an on-prem Linux box, or a local dev machine) using
Docker Compose. It assumes no internet exposure by default.

## 2. Prerequisites

- Linux host (primary target) or Windows with Docker Desktop + WSL2 for
  development. Production deployment should be Linux.
- Docker Engine (current stable) and Docker Compose v2 plugin.
- At minimum two separate physical/logical disks recommended:
  - fast disk (NVMe/SSD) for the control-plane and tenant PostgreSQL data
    directories,
  - larger disk(s) (HDD/SSD, optionally ZFS/RAID) for object storage.
  A single-disk dev setup is fine for local development; production should
  follow Section 4 of ARCHITECTURE.md.
- A `.env` file derived from `.env.example`, populated with locally
  generated secrets (never the example placeholder values).

## 3. Service Map (Docker Compose — target, see `docker-compose.yml`)

| Service | Image basis | Exposed to host? | Notes |
|---|---|---|---|
| `proxy` | Caddy | Yes (LAN interface only, via `PROXY_BIND_ADDRESS`) | TLS termination, routing to `frontend`/`backend` |
| `frontend` | Node 24 / Next.js 16 | No (via proxy only) | |
| `backend` | Python 3.13 / Django 5.2 LTS (gunicorn) | No (via proxy only) | Runs migrations on startup via entrypoint, not automatically in prod without review |
| `worker` | same image as backend (`image: pdc-backend:latest`, shared explicitly), `celery worker` | No | |
| `beat` | same image as backend (same shared tag), `celery beat` | No | |
| `postgres-control` | postgres:18 | No | Control-plane metadata DB |
| `postgres-tenant` | postgres:18 | No | Tenant relational data; may be split into multiple instances later |
| `valkey` | valkey/valkey — see [ADR-0011](../architecture/adr/0011-valkey-over-redis.md) | No | Broker + cache; the `REDIS_URL` env var name is kept for client-library familiarity, but the compose service/image is Valkey |
| `object-storage` | MinIO (S3-compatible) | No (internal only; console gated separately, LAN/VPN only if enabled) | Local S3-compatible backend |

Exact major-version rationale for every dependency above is tracked in
[docs/architecture/DEPENDENCY_VERSIONS.md](../architecture/DEPENDENCY_VERSIONS.md).

No service other than `proxy` publishes a port on the host's non-loopback
interface. `postgres-*`, `valkey`, and `object-storage` are reachable only
on the internal Docker network.

## 4. Bring-Up Sequence (verified — this is exactly what was run)

1. Copy `.env.example` to `.env` and fill in secrets (DB passwords, Django
   `SECRET_KEY`, object storage root credentials, credential-encryption
   key). If reaching the proxy from anywhere other than `localhost`/
   `127.0.0.1`, add that hostname/IP to `PROXY_TLS_HOSTNAMES` too (space-
   separated) — Caddy's internal CA only issues certificates for names
   listed there. Never commit `.env`.
2. `docker compose build`
3. `docker compose up -d postgres-control postgres-tenant valkey
   object-storage`
4. Wait for health checks to pass (`docker compose ps`).
5. `docker compose run --rm backend python manage.py migrate`
6. `docker compose run --rm backend python manage.py seed_permissions`
   (loads the permission catalog and system roles — required before the
   next step, and safe to re-run any time).
7. `docker compose run --rm backend python manage.py
   bootstrap_super_administrator you@example.com` — creates the user (if
   it doesn't exist) and grants the platform-wide Super Administrator
   role. Plain `manage.py createsuperuser` also works to create a bare
   user account, but grants no privilege by itself in this project's
   capability-based permission model (see ADR-0008/permissions/models.py)
   — use `bootstrap_super_administrator` to actually get an operator
   account with platform-wide access.
8. `docker compose up -d backend worker beat frontend proxy`
9. Visit `https://<host-or-LAN-ip>:8443/` — Caddy's internal CA issues a
   locally-trusted-once-imported certificate; browsers will warn until you
   trust that CA root (`docker compose exec proxy cat
   /data/caddy/pki/authorities/local/root.crt` to export it), which is
   expected and fine for local-only use. `curl -k` or an accepted browser
   warning is sufficient to confirm connectivity without importing the CA.

## 5. Storage Volume Layout (target)

```
/srv/pdc/
  pg-control/        # bind mount -> postgres-control data dir (fast disk)
  pg-tenant/          # bind mount -> postgres-tenant data dir (fast disk)
  object-storage/     # bind mount -> MinIO data dir (HDD pool / ZFS dataset)
  backups/            # local staging area before off-host sync
```

Bind mounts (rather than anonymous Docker volumes) are recommended in
production so the operator has explicit control over which physical disk
backs each path, matching the storage hardware assumptions in
ARCHITECTURE.md Section 5. The `backups/` path is real as of Phase 11
(`system/backups.py` writes `pg_dump` output there) — `docker-compose.yml`
mounts it as the named volume `pdc_backups` on `backend`/`worker`/`beat`
by default; bind-mount it explicitly (`docker-compose.override.yml`) to
put it on the disk/pool you actually intend for backups, same pattern as
the other paths here. A named volume alone is not an off-host backup —
see `docs/operations/BACKUP_RESTORE.md` Section 4.

## 6. TLS for Local/LAN Use

- Default: self-signed certificate or an internal CA, trusted manually on
  client machines, terminated at `proxy`.
- Internal service-to-service traffic (backend ↔ postgres/redis/object
  storage) stays on the Docker network without TLS by default in a
  single-host deployment, but this is called out as a documented trade-off,
  not an oversight — multi-host deployments must add TLS or a private
  overlay network (WireGuard) between hosts.

## 7. Environment Configuration

All environment-specific values are supplied via `.env` / container
environment variables, never hardcoded. Categories:

- Django: `SECRET_KEY`, `DEBUG` (must be `False` outside local dev),
  `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`.
- Database: separate connection settings for control-plane vs tenant
  Postgres.
- Valkey (Redis-protocol): connection URL, environment variable name kept
  as `REDIS_URL` for client-library familiarity — see ADR-0011.
- Object storage: endpoint, region (dummy for MinIO), access/secret key,
  bucket naming prefix.
- Secrets: a dedicated symmetric key for encrypting `ConnectedDatabase`
  credentials at rest (distinct from `SECRET_KEY`), sourced from an
  environment variable or a mounted secret file — see
  `docs/operations/BACKUP_RESTORE.md` for how this key itself is backed up
  (losing it makes stored external-DB credentials unrecoverable, by design).
- Optional hardening (Phase 11, not applied by default): run `python
  manage.py provision_tenant_role <role_name>` once against a running
  stack to create a least-privilege tenant-database role (`CONNECT`+
  `CREATE` only, never superuser), then switch `TENANT_DB_USER`/
  `TENANT_DB_PASSWORD` to it and restart `backend`/`worker`/`beat` — see
  `docs/security/THREAT_MODEL.md` TB3.

## 8. What Is NOT Covered Here Yet

- Kubernetes deployment (explicitly deferred; see ROADMAP.md and
  ADR-0006).
- Public internet exposure / Zero Trust gateway, and automated TLS
  certificate issuance for internet-facing deployments — implemented
  (Phase 10) but deliberately kept as a separate guide, not folded into
  this one: see `docs/deployment/INTERNET_GATEWAY.md`. This document
  stays scoped to the LAN-first default.
- Off-host/off-machine backup shipping and object-storage backup tooling
  choice — the platform automates local `pg_dump`/restore-testing
  (Phase 11, `docs/operations/BACKUP_RESTORE.md`), but getting a copy off
  this host is still an operator-configured step.

This document will be replaced with verified, tested commands once Phase 1
infrastructure work actually produces the Dockerfiles and compose file
referenced above.
