# Private Data Cloud

A self-hosted, local-first private organizational platform combining
secure file storage (Drive/S3-like), a no-code relational database builder
(Airtable/Supabase-like), and a controlled application-integration layer —
built to run on an organization's own infrastructure without depending on
AWS, Azure, or GCP.

## Status

**Phase 6 — Data Explorer, complete and verified end-to-end.** Phases 0–5
are done: architecture, infrastructure, authentication/organizations/
permissions, file storage, the visual database builder, and CSV import.
Phase 6 adds spreadsheet-style browsing and editing of the data inside
tables the database builder creates — server-side paginated/filtered/
sorted row listing (hard-capped page size, never "fetch everything"),
row insert/update/delete, and streamed CSV export. 147 tests pass against
real PostgreSQL, MinIO, and Celery — not mocks — including
cross-organization IDOR/BOLA regression tests for every resource type
introduced so far. Every phase's exit criteria has been confirmed against
the actual running Docker stack, not only the automated suite. Full phase
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
