# Local Deployment Guide — Private Data Cloud

Status: DRAFT (Phase 1 — the backend/frontend skeletons, `docker-compose.yml`,
and `infrastructure/proxy/Caddyfile` referenced below now exist, but the
full bring-up sequence has not been run end-to-end: this development
environment has no Docker installed. Treat this as a specification to
verify, not yet a confirmed runbook — see
`docs/architecture/DEPENDENCY_VERSIONS.md` for exactly what has and hasn't
been run.)
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
| `worker` | same image as backend, `celery worker` | No | |
| `beat` | same image as backend, `celery beat` | No | |
| `postgres-control` | postgres:18 | No | Control-plane metadata DB |
| `postgres-tenant` | postgres:18 | No | Tenant relational data; may be split into multiple instances later |
| `valkey` | valkey/valkey — see [ADR-0011](../architecture/adr/0011-valkey-over-redis.md) | No | Broker + cache; the `REDIS_URL` env var name is kept for client-library familiarity, but the compose service/image is Valkey |
| `object-storage` | MinIO (S3-compatible) | No (internal only; console gated separately, LAN/VPN only if enabled) | Local S3-compatible backend |

Exact major-version rationale for every dependency above is tracked in
[docs/architecture/DEPENDENCY_VERSIONS.md](../architecture/DEPENDENCY_VERSIONS.md).

No service other than `proxy` publishes a port on the host's non-loopback
interface. `postgres-*`, `valkey`, and `object-storage` are reachable only
on the internal Docker network.

## 4. Bring-Up Sequence (target)

1. Copy `.env.example` to `.env` and fill in secrets (DB passwords, Django
   `SECRET_KEY`, object storage root credentials, credential-encryption
   key). Never commit `.env`.
2. `docker compose build`
3. `docker compose up -d postgres-control postgres-tenant valkey
   object-storage`
4. Wait for health checks to pass (`docker compose ps`).
5. `docker compose run --rm backend python manage.py migrate`
6. `docker compose run --rm backend python manage.py createsuperuser`
   (or a scripted bootstrap command for the first Super Administrator).
7. `docker compose up -d backend worker beat frontend proxy`
8. Visit `https://<host-or-LAN-ip>/` (self-signed or internal CA certificate
   for local-only use; document trust steps separately in Section 6).

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
ARCHITECTURE.md Section 5.

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

## 8. What Is NOT Covered Here Yet

- Kubernetes deployment (explicitly deferred; see ROADMAP.md and
  ADR-0006).
- Public internet exposure / Zero Trust gateway (Phase 10).
- Automated TLS certificate issuance for internet-facing deployments
  (Phase 10; local/LAN uses manual or internal-CA certs).

This document will be replaced with verified, tested commands once Phase 1
infrastructure work actually produces the Dockerfiles and compose file
referenced above.
