# Chapter 1 — Architecture

## The big picture

```
 Shop staff (browser)      Customers' phones (portal)      Other programs (bearer token)
         |  https://localhost:8443 or https://<shop name>:8443        |
         v                                                             v
 +-------------------------------------------------------------------------------+
 | proxy (Caddy 2): HTTPS, security headers, routing by path; :8445 hosted sites |
 +---+-------------------+-----------------------+-------------------------------+
     | pages             | /api/* /healthz       | /apps/pay-1, /apps/spare-parts, /apps/pharmacy
     v                   v                       v
 +----------+   +-------------------+   +------------------------------------+
 | frontend |   | backend (Django,  |   | service applications (own images): |
 | Next.js  |   | gunicorn)         |<--| Pay (FastAPI), Spare Parts and     |
 +----------+   +----+---------+----+   | Pharmacy (Next.js) — internal API  |
                     |         |        +------------------------------------+
        +------------+    +----+------------------+--------------+
        v                 v                       v              v
 +--------------+  +----------------+       +--------+     +-----------+    +--------------+
 | postgres-    |  | postgres-      |       | valkey |     | object-   |    | worker, beat |
 | control      |  | tenant         |       | cache, |     | storage   |    | (Celery)     |
 | the catalog  |  | business data, |       | queue  |     | (MinIO)   |    | runner (apps)|
 +--------------+  | schema per org |       +--------+     +-----------+    +--------------+
                   +----------------+
```

Everything runs as Docker containers on one machine, on a private Docker network **with no route to the internet**.
Only the proxy publishes ports, and by default only on the loopback address (`127.0.0.1` and `::1`); opening it to the
shop network is a deliberate step (Control Center > Shop network, `Set-IntraForgeNetwork.ps1`).

## The containers

| Service | Image | Role |
|---|---|---|
| `proxy` | `caddy:2-alpine` | The only published port: 8443 (IntraForge), 8445 (hosted sites), 8446/8080 internal helpers. Refuses `/api/v1/internal/` from outside. |
| `frontend` | `intraforge-shop-frontend` | The Next.js screens, rendered in the browser against the API. |
| `backend` | `intraforge-shop-backend` | Django + DRF: every rule, permission check and write. |
| `worker` | same image | Celery worker: imports, exports, restores, backups, webhook deliveries, provisioning. |
| `beat` | same image | Celery Beat: nightly backups, weekly restore tests, health checks every 5 minutes. |
| `runner` | same image (`python -m app_runner`) | Starts hosted Node.js apps in locked containers; the backend talks to it by token, never to Docker itself. |
| `postgres-control` | `postgres:18` | The control plane: users, organizations, roles, grants, app definitions, audit, backups, licence. |
| `postgres-tenant` | `postgres:18` | The data plane: one schema per organization for tables people build and installed apps' records; one schema per service-app instance. |
| `valkey` | `valkey/valkey:9-alpine` | Cache (shared rate-limit counters) and the Celery queue. |
| `object-storage` | `minio/minio` | Every file: uploads, versions, covers, backups' file parts, hosted-site files. |
| `pay-1` … `pay-3` | `intraforge-shop-pay` | IntraForge Pay deployments (one per Pay instance). |
| `spareparts`, `pharmacy` | own images | The standalone shop applications, served under `/apps/...`. |
| `names` (profile `names`) | `coredns/coredns` | Answers the shop's names (`myshop.lan`, `movies.lan`) on the shop network. |

## The two planes (ADR-0001, ADR-0005)

Django is the **control plane**: it *describes, authorizes and audits* access to data. It never stores large files and
is never the store for business data. The **data plane** is PostgreSQL (tenant database) and object storage.

- **postgres-control** holds the catalog — who exists, what they may do, which resources exist and where.
- **postgres-tenant** holds business data. Each organization gets its own PostgreSQL schema, so one organization's
  tables are physically separate from another's, not rows filtered by an `organization_id`.
- **Object storage** holds files; Django keeps only their metadata (`FileObject`, `FileVersion`).

`config/db_routers.py` keeps Django's own models on the control database; tenant tables are reached through explicit,
quoted SQL (`databases/rows.py`, `app_platform/records.py`) on the tenant connection.

## How a request travels

1. The browser calls `https://localhost:8443/api/v1/...`. Caddy terminates HTTPS and forwards `/api/*` to
   `backend:8000`.
2. Django's middleware runs in order: security headers, a request id (`system.middleware.RequestIDMiddleware`),
   sessions, CSRF, authentication, **`PasswordChangeMiddleware`** (a person whose password was reset may do nothing
   until they choose a new one), **`LicenceMiddleware`** (read-only without a licence), **`ApiRequestLogMiddleware`**
   (records requests made with an application's token).
3. DRF authenticates the caller: a session cookie for people, `Authorization: Bearer pdc_sk_…` for applications.
4. The view is thin: it parses input with a serializer and calls a **service function**.
5. The service resolves the resource **inside the caller's organization** (a foreign id answers 404, not 403, so it
   does not reveal that it exists), checks the **capability** with `permissions.services.has_permission`, does the work
   in a transaction and writes an **audit event**.
6. Slow work is handed to Celery (`worker`) through Valkey; the screen polls the job.

## The rules the design never breaks

1. **Control plane and data plane stay separate** (ADR-0001).
2. **Tenant isolation is a backend invariant.** Every tenant resource carries its organization; every request is checked
   on the server. New resource types ship only with tests proving Organization A cannot reach B's data by id.
3. **No unreviewed dynamic SQL.** Identifiers from users are validated (`databases/identifiers.py`) and quoted with
   `psycopg.sql.Identifier`; DDL runs in a transaction, after a permission check, with an audit event.
4. **Capabilities, never role names** (ADR-0008). Code asks "does this person hold `inventory.sell` here?", never
   "is this an admin?".
5. **Schema per organization** (ADR-0005).
6. **Boring technology first.** Docker Compose, not Kubernetes (ADR-0006). No new datastore, identity provider or
   orchestrator without a new ADR.
7. **Local-first.** Nothing needs the internet. Internet exposure (hosted sites through a Cloudflare Tunnel) is off by
   default and only the Super Administrator can switch it on.

## Architecture decision records

| ADR | Decision |
|---|---|
| 0001 | Control plane (Django) separate from data plane (PostgreSQL + object storage) |
| 0002 | Django + DRF in small bounded apps |
| 0003 | Django-native authentication first, OIDC-ready |
| 0004 | S3-compatible object storage, MinIO locally |
| 0005 | Schema-per-organization tenant isolation |
| 0006 | Docker Compose first, Kubernetes deferred |
| 0007 | TypeScript + React, Next.js |
| 0008 | Capability-based authorization |
| 0009 | External databases: connected (read-only) vs imported modes |
| 0010 / 0011 | Celery for background jobs; Valkey instead of Redis (licence) |
| 0012 / 0013 | Windows deployment (WSL2 appliance route) and Docker Engine in the rootfs — the earlier MSI route |
| 0014 / 0015 | App Platform: immutable template versions, independent instances; resumable runtime provisioning |
| 0016 | Tenant operation journal and quantity ledgers (the database decides stock) |
| 0017 | Business-operation authority over stock (sell / receive / adjust / transfer) |
| 0018 | Service applications on IntraForge storage, identity and audit |
| 0019 | Passkeys (WebAuthn) |
| 0021 | Shop names on the LAN (CoreDNS) |
| 0022 | Movie Shop and the media agent |
| 0023 | Licensing: trial, serial number, activation code |
| 0024 | MySQL and SQL Server connectors |

Hosted websites and the app runner are described in code as "ADR-0019" and "ADR-0020" decisions, but no ADR file with
those decisions exists (0019 is passkeys). See Chapter 9.
