# Private Data Cloud

A self-hosted, local-first private organizational platform combining
secure file storage (Drive/S3-like), a no-code relational database builder
(Airtable/Supabase-like), and a controlled application-integration layer —
built to run on an organization's own infrastructure without depending on
AWS, Azure, or GCP.

## Status

**All 12 planned phases (0–11) are complete and verified end-to-end.**
Architecture and threat modeling; infrastructure; authentication/
organizations/permissions; file/object storage; the visual database
builder; CSV import; the spreadsheet-style data explorer; application/
service-account integrations; external database connectors (read-only
connected-mode PostgreSQL); internal sharing; an optional, opt-in
internet-gateway path (TOTP MFA, real ACME TLS, tightened rate limiting);
and monitoring/backup automation (real `pg_dump`/restore-test cycles on
a Celery Beat schedule, Prometheus metrics, a genuinely least-privilege
tenant-database role available as an opt-in hardening step, a real
dependency audit). 229 tests pass against real PostgreSQL, MinIO, and
Celery — not mocks — including cross-organization IDOR/BOLA regression
tests for every tenant-owned resource type in the platform. Every
phase's exit criteria has been confirmed against the actual running
Docker stack, not only the automated suite — including, in the final
phase, driving a real backup through `pg_dump`, restoring it into an
isolated database, and validating the restore, exactly as
`docs/operations/BACKUP_RESTORE.md` specifies. Full phase-by-phase
history — what was built, how it was verified, and every real bug found
along the way — lives in
[docs/architecture/ROADMAP.md](docs/architecture/ROADMAP.md); this section
intentionally stays short rather than growing with every phase. See also
[docs/architecture/DEPENDENCY_VERSIONS.md](docs/architecture/DEPENDENCY_VERSIONS.md)
for dependency/version rationale.

## Start Here

- [docs/architecture/ARCHITECTURE.md](docs/architecture/ARCHITECTURE.md) — system, network, and storage architecture, with diagrams
- [docs/architecture/DATA_MODEL.md](docs/architecture/DATA_MODEL.md) — control-plane entities and relationships
- [docs/security/THREAT_MODEL.md](docs/security/THREAT_MODEL.md) — STRIDE analysis, multi-tenancy/IDOR deep dive
- [docs/security/PERMISSIONS.md](docs/security/PERMISSIONS.md) — capability/permission and role model
- [docs/deployment/LOCAL_DEPLOYMENT.md](docs/deployment/LOCAL_DEPLOYMENT.md) — target local/LAN deployment (Docker Compose)
- [docs/deployment/INTERNET_GATEWAY.md](docs/deployment/INTERNET_GATEWAY.md) — optional internet-facing exposure (opt-in, off by default)
- [docs/operations/BACKUP_RESTORE.md](docs/operations/BACKUP_RESTORE.md) — backup, retention, and disaster recovery strategy
- [docs/architecture/ROADMAP.md](docs/architecture/ROADMAP.md) — phase-by-phase delivery plan
- [docs/architecture/adr/](docs/architecture/adr/README.md) — architecture decision records
- [docs/architecture/DEPENDENCY_VERSIONS.md](docs/architecture/DEPENDENCY_VERSIONS.md) — pinned major versions and why

## Core Principles

1. **Local-first.** No internet dependency required for normal operation.
2. **Control plane / data plane separation.** Django (control plane) never
   is the data; PostgreSQL and S3-compatible object storage (data plane)
   hold it.
3. **Deny by default, enforced server-side.** Tenant isolation is a backend
   invariant, tested explicitly, never a UI-only concern.
4. **No unreviewed dynamic SQL.** Schema/table creation goes through a
   validated, transactional, audited service layer.
5. **Boring technology first.** Docker Compose before Kubernetes; complexity
   is added only when a concrete requirement forces it.

## Repository Structure

```
private-data-cloud/
    apps/
        backend/          # Django + DRF control plane (Phase 1+)
        frontend/          # Next.js/React frontend (Phase 1+)
    infrastructure/
        docker/            # Dockerfiles, build context helpers
        proxy/              # Reverse proxy configuration
        monitoring/          # Prometheus/Grafana/Loki config (Phase 11)
    scripts/               # Operational and dev scripts
    docs/
        architecture/        # ARCHITECTURE.md, DATA_MODEL.md, ROADMAP.md, ADRs
        security/             # THREAT_MODEL.md, PERMISSIONS.md
        deployment/            # LOCAL_DEPLOYMENT.md
        api/                    # API.md (OpenAPI-derived docs, Phase 2+)
        operations/              # BACKUP_RESTORE.md
        development/               # CONTRIBUTING.md
    tests/                   # Cross-cutting/security/E2E tests
    docker-compose.yml       # Service map — built and run end-to-end, verified
    .env.example
    README.md
    CLAUDE.md
```

## Technology Stack (target — see ADRs for rationale)

Backend: Python, Django, Django REST Framework, PostgreSQL, psycopg,
Celery, Valkey (Redis-protocol-compatible broker/cache — see ADR-0011).
Frontend: TypeScript, React, Next.js.
Storage: S3-compatible abstraction (MinIO locally, AWS S3 or other
compatible providers later).
Infrastructure: Docker + Docker Compose, reverse proxy with TLS, isolated
container networks, environment-driven configuration.

## Development Process

This project is built phase-by-phase per
[docs/architecture/ROADMAP.md](docs/architecture/ROADMAP.md). Each phase is
gated on tests, lint/type checks, a security review pass, and documentation
updates before the next phase begins — see `CLAUDE.md` for the full
engineering process this repository follows.

## License

TBD.
