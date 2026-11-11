# Hardware Guide

Sizing guidance for running IntraForge (Internal Pilot v0.9) on either
deployment path — Linux/plain Docker Compose
(`docs/deployment/LOCAL_DEPLOYMENT.md`) or Windows/WSL2 appliance
(ADR-0012, `installer/`). Numbers below are measured, not guessed —
see "How these numbers were produced."

## How these numbers were produced (2026-09-06)

`docker stats --no-stream` and `docker system df -v` against the real
`docker-compose.yml` stack (proxy, backend, worker, beat, frontend,
postgres-control, postgres-tenant, object-storage, valkey — 9
containers), captured on this development machine right after a full
320-test backend suite run (so backend/worker read slightly above a
true idle baseline, not below it — a conservative direction for a
sizing guide).

| Container | Memory (measured) |
|---|---|
| backend (gunicorn) | ~500 MB |
| worker (Celery) | ~865 MB |
| beat (Celery scheduler) | ~130 MB |
| frontend (Next.js) | ~40 MB |
| proxy (Caddy) | ~17 MB |
| postgres-control | ~110 MB |
| postgres-tenant | ~75 MB |
| object-storage (MinIO) | ~320 MB |
| valkey | ~12 MB |
| **Total, measured** | **~2.1 GB** |

Container image sizes on disk (`docker system df -v`): backend ~1.3 GB,
frontend ~0.3 GB, postgres ~0.65 GB (shared by both Postgres
containers), MinIO ~0.24 GB, Caddy ~0.09 GB, Valkey ~0.07 GB — roughly
**2.6 GB of images**, before any customer data.

These numbers are for the application containers only — they do not
include Docker Desktop/WSL2's own overhead, the host OS, or customer
data growth in Postgres/MinIO volumes over time.

## Minimum (evaluation / single-user pilot)

- **CPU:** 4 cores (2 physical + hyperthreading acceptable)
- **RAM:** 8 GB total system memory (leaves ~5 GB for Windows + WSL2 +
  Docker Desktop overhead above the ~2.1 GB the stack itself measured
  using)
- **Disk:** 40 GB free, SSD strongly preferred — WSL2's virtual disk
  and Docker's overlay filesystem are both meaningfully slower on
  spinning disks, and Postgres/MinIO are both I/O-sensitive
- **OS:** Windows 11 (WSL2 + virtualization enabled in BIOS/UEFI) or
  Windows 10 21H2+ with WSL2, or any Linux distribution with Docker
  Engine + Compose plugin
- **Network:** none required for normal operation (local-first,
  CLAUDE.md rule 7) — internet only needed once, to pull container
  images, unless using the offline WSL2 rootfs path (ADR-0013)

## Recommended (internal team pilot, multiple concurrent users)

- **CPU:** 8 cores
- **RAM:** 16 GB — gives real headroom for Celery worker concurrency
  under CSV import / analytics / export load (Phase 6/14/13's
  heavier, long-running jobs run here, not in the request/response
  path) and for Postgres's own buffer cache to matter
- **Disk:** 100+ GB SSD/NVMe, sized additionally for expected object
  storage (file uploads) and Postgres data growth — this floor is
  container-only overhead, not a data budget
- **Network:** a real LAN connection if using the LAN-access feature
  (`installer/scripts/Enable-IntraCloudLanAccess.ps1`,
  `docs/implementation/RELEASE_READINESS.md`'s "local/LAN operation"
  section) — plan IP addressing accordingly (mirrored WSL2 networking
  is machine-wide, not IntraForge-specific)

## What actually drives resource usage up

Not scored numerically here (deliberately — this is a pilot on a
single known set of workloads, not a general capacity-planning tool),
but worth knowing:

- **Celery worker concurrency** (`docker-compose.yml`'s worker service)
  is the single biggest lever — CSV bulk-import (`imports`), analytics
  operations over large tables (`analytics`), and `.icp` export/import
  (`exports`) all run here, and each concurrent job holds its own
  Postgres connection and Python process memory for its duration.
- **Postgres** (both control and tenant) grows with schema count
  (one schema per tenant Organization, ADR-0005) and row count —
  sizing the data volume, not the container's own baseline memory, is
  the real long-term disk driver.
- **Object storage (MinIO)** grows directly with uploaded file volume
  — size this independently of everything else in this document, based
  on expected file storage needs.
- **ClamAV** (Phase 12, opt-in malware scanning): if enabled, budget an
  additional ~1-1.5 GB RAM for the `clamav/clamav` container (not
  included in the measured total above, since it's off by default) —
  its virus-definition database is loaded fully into memory.

## Open items

- No load test has been run against concurrent multi-user usage — the
  "recommended" tier above is a reasoned estimate from the measured
  single-session footprint plus normal margin, not a benchmarked
  number. A real concurrency/load test is out of scope for this pass
  and not silently implied by this document.
- Windows/WSL2-specific overhead (Docker Desktop's own VM, WSL2's
  virtual disk) was not separately measured this session — the
  "leaves ~5 GB" minimum-tier math is a reasonable estimate from
  general WSL2/Docker Desktop guidance, not measured on this specific
  stack running inside WSL2 (this session ran the stack via Docker
  Desktop's own engine directly, not the packaged WSL2 appliance).
