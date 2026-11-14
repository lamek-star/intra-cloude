# Chapter 1 — Architecture — The containers

Topic for: software engineers. Source: IntraForge Engineering Handbook, Chapter 1 — Architecture.

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
