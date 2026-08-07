# Architecture Overview — Private Data Cloud

Status: DRAFT (Phase 0)
Last updated: 2026-08-07

## 1. Purpose

Private Data Cloud (PDC) is a self-hosted platform combining file storage
(Drive/S3-like), a no-code relational database builder (Airtable/Supabase-like),
and an application-integration layer, aimed at organizations that want to run
their own infrastructure instead of depending on AWS/Azure/GCP.

This document describes the system as a whole: its major components, how they
communicate, and the principles that constrain future design decisions. It is
intentionally conservative — the goal is a system that can be trusted with
real organizational data, not one that maximizes feature velocity.

## 2. Guiding Principles

1. **Local-first.** The platform must run fully on private infrastructure
   with no outbound internet dependency for normal operation, after images
   and packages are installed.
2. **Control plane / data plane separation.** Django never *is* the data —
   it describes, authorizes, and audits access to data that lives in
   PostgreSQL (relational) and S3-compatible object storage (blobs).
3. **Deny by default.** Every resource access requires an explicit,
   server-side authorization check. The UI is never the authorization
   boundary.
4. **Tenant isolation is a backend invariant**, not a UI convenience.
   Organization A must never be able to reach Organization B's data by
   manipulating identifiers, regardless of what the frontend renders.
5. **No unreviewed dynamic SQL.** Anything that creates schemas/tables from
   user input goes through a validated, whitelisted, transactional service
   layer — never string-concatenated SQL.
6. **Boring technology first.** Docker Compose before Kubernetes, Django
   session/token auth before a full OIDC provider, synchronous code before
   async where load doesn't demand it. Complexity is added when a concrete
   requirement forces it, not speculatively.
7. **Incremental delivery.** The system is built and validated phase by
   phase (see [ROADMAP.md](ROADMAP.md)); later phases must not force a
   redesign of earlier ones.

## 3. High-Level System Architecture

```mermaid
flowchart TB
    subgraph Client["Clients"]
        Browser["Web Browser (Next.js/React SPA)"]
        AppClient["Registered Applications\n(service-account API clients)"]
    end

    subgraph Edge["Edge / Perimeter (LAN by default)"]
        Proxy["Reverse Proxy (TLS termination,\nrate limiting, security headers)"]
    end

    subgraph ControlPlane["Control Plane (Django)"]
        API["Django REST Framework API\n/api/v1/*"]
        Auth["Auth & Session/Token Service"]
        Perm["Permission / Capability Engine"]
        Meta["Metadata Services\n(orgs, workspaces, files, db schemas,\napplications, audit)"]
        Worker["Celery Workers\n(CSV import, thumbnails, backups, scans)"]
        Beat["Celery Beat\n(scheduled jobs)"]
    end

    subgraph DataPlane["Data Plane"]
        PG_Control[("Control-Plane PostgreSQL\n(metadata: users, orgs, permissions,\nfile index, schema catalog, audit)")]
        PG_Tenant[("Tenant PostgreSQL\n(user-created relational data,\nrow-level org scoping)")]
        Redis[("Redis\n(broker + cache + rate limiting)")]
        Object[("S3-compatible Object Storage\n(MinIO locally / AWS S3 later)")]
    end

    subgraph External["Optional External Connections (Phase 8+)"]
        ExtDB[("Customer-owned external\nPostgreSQL/MySQL databases")]
    end

    Browser -->|HTTPS| Proxy
    AppClient -->|HTTPS + service credentials| Proxy
    Proxy --> API
    API --> Auth
    API --> Perm
    API --> Meta
    Meta --> PG_Control
    Meta -->|via connector, validated DDL/DML| PG_Tenant
    API -->|presigned URLs / streamed proxy| Object
    API -->|enqueue| Redis
    Redis --> Worker
    Redis --> Beat
    Worker --> PG_Control
    Worker --> PG_Tenant
    Worker --> Object
    Meta -.->|encrypted credentials, connector interface| ExtDB
```

Key point: the browser and registered applications **never** talk to
PostgreSQL, Redis, or object storage directly. Everything is mediated by the
Django API, which enforces authorization and produces audit records.

## 4. Network Architecture

```mermaid
flowchart LR
    subgraph Internet["Internet (disabled by default)"]
        Ext["External users / partner apps"]
    end

    subgraph DMZ["Perimeter Network"]
        FW["Firewall"]
        RP["TLS Reverse Proxy /\nZero Trust Gateway"]
    end

    subgraph AppNet["Application Network (internal Docker network)"]
        Web["Frontend (Next.js)"]
        Api["Backend API (Django/DRF)"]
        Wrk["Celery Workers + Beat"]
    end

    subgraph DataNet["Data Network (internal-only, no ingress from AppNet's public side)"]
        Pg[("PostgreSQL (control + tenant)")]
        Rd[("Redis")]
        Obj[("Object Storage (MinIO)")]
    end

    subgraph MgmtNet["Management Network (LAN-only, MFA-gated)"]
        Admin["Admin/DB tooling,\nmonitoring dashboards"]
    end

    Ext -.disabled by default.-> FW
    FW --> RP
    RP --> Web
    RP --> Api
    Api --> Wrk
    Api --> Pg
    Api --> Rd
    Api --> Obj
    Wrk --> Pg
    Wrk --> Rd
    Wrk --> Obj
    Admin -.LAN/VPN only.-> Pg
    Admin -.LAN/VPN only.-> Obj
    Admin -.LAN/VPN only.-> Api
```

Rules:

- Only the reverse proxy is reachable from outside the host/LAN edge.
- PostgreSQL, Redis, object storage admin console, and the Docker socket are
  bound to the internal Docker network only — never published to the host's
  public interface.
- Management/monitoring tooling sits on a separate network segment reachable
  only from the LAN or an administrative VPN, with MFA for admin accounts.
- Internet exposure (Phase 10) inserts a Zero Trust gateway / TLS proxy in
  front of the same application network; it does not change the internal
  topology.

## 5. Storage Architecture

```mermaid
flowchart TB
    subgraph Hardware["Physical / Virtual Storage"]
        NVMe["NVMe/SSD — system + control-plane DB"]
        SSD2["Dedicated SSD/NVMe — tenant PostgreSQL data disk"]
        HDDPool["HDD Pool (ZFS/RAID) — object storage"]
        Backup["Secondary backup server / NAS\n(offsite or off-host)"]
    end

    subgraph Volumes["Docker-managed Persistent Volumes"]
        VPGControl["pg_control_data"]
        VPGTenant["pg_tenant_data"]
        VObj["minio_data"]
        VRedis["redis_data (cache only, non-critical)"]
    end

    NVMe --> VPGControl
    SSD2 --> VPGTenant
    HDDPool --> VObj
    VPGControl -->|pg_dump / WAL archiving| Backup
    VPGTenant -->|pg_dump / WAL archiving| Backup
    VObj -->|object sync / snapshot| Backup
    VRedis -.non-durable, rebuildable.-> VRedis
```

Notes:

- RAID/ZFS provides redundancy against disk failure, not protection against
  accidental deletion, corruption, or ransomware — backups are a distinct,
  independently tested process (see
  [BACKUP_RESTORE.md](../operations/BACKUP_RESTORE.md)).
- Redis holds only rebuildable state (broker queue, cache, rate-limit
  counters) and is not part of the durability guarantee.
- Object storage uses content-addressed or UUID-based keys generated
  server-side; the physical filesystem path is never exposed to clients.

## 6. Authorization Model (Overview)

```mermaid
flowchart TB
    User["User / Service Account"]
    Role["Role\n(named bundle of permissions,\nscoped to an Organization)"]
    Perm["Permission / Capability\n(e.g. storage.read, database.schema.manage)"]
    ResourceGrant["Resource-level Grant\n(optional: restrict a permission to\nspecific projects/buckets/databases)"]
    Resource["Resource\n(file, folder, database, table, application)"]
    Org["Organization"]

    User -->|member of| Org
    User -->|assigned| Role
    Role -->|grants| Perm
    User -->|may hold, for narrower access| ResourceGrant
    ResourceGrant -->|scopes| Perm
    ResourceGrant -->|targets| Resource
    Resource -->|owned by| Org
    Perm -->|checked against| Resource

    classDef enforce fill:#fdd,stroke:#900;
    class Perm,ResourceGrant enforce
```

Every authorization decision is: *"Does this actor have this permission,
either organization-wide via a Role or specifically via a Resource Grant, on
a resource owned by an Organization the actor belongs to?"* This is
evaluated server-side, in a single shared service (see
[PERMISSIONS.md](../security/PERMISSIONS.md)), never duplicated ad hoc in
individual views.

## 7. Component Responsibilities

| Component | Responsibility | Must NOT do |
|---|---|---|
| Next.js/React frontend | Presentation, UX, optimistic UI, client-side validation for UX only | Be trusted for authorization; hold long-lived secrets |
| Django/DRF API | Authn, authz, validation, orchestration, audit, presigned URL issuance | Store large blobs in DB rows; act as a filesystem proxy for arbitrary paths |
| Celery workers | CSV import, async jobs, backups, malware-scan hooks, thumbnailing | Perform unaudited privileged operations |
| Control-plane PostgreSQL | Users, orgs, permissions, file index, schema catalog, jobs, audit | Store tenant business data rows |
| Tenant PostgreSQL | User-created database schemas/tables/rows | Be reachable directly by browsers or external apps |
| Object storage (S3-compatible) | Durable blob storage for uploaded files | Be reachable directly by browsers without a presigned URL |
| Redis | Celery broker, cache, rate limiting | Be a system of record for anything durable |
| Reverse proxy | TLS termination, routing, basic rate limiting, security headers | Perform business authorization |

## 8. Data Plane: One Tenant Postgres, Row-Scoped — Rationale

See [ADR-0005](adr/0005-tenant-database-isolation-strategy.md) for the full
analysis. Summary: user-created databases/tables live inside one or more
dedicated "tenant" PostgreSQL clusters, isolated from each **other**
organization at the schema level (`org_<uuid>` schema per organization),
while the control plane enforces which organization/user may touch which
schema. This avoids both the operational cost of "one Postgres instance per
tenant" and the weak isolation of "one shared schema keyed by `org_id`
column alone."

## 9. Cross-Cutting Concerns

- **Audit logging**: every mutating control-plane operation and every schema
  change emits an audit event before the transaction commits successfully
  (see [Section 18 of the master prompt] and audit module design in
  DATA_MODEL.md).
- **Idempotency / request IDs**: every API request is tagged with a request
  ID, propagated to logs, audit records, and error responses.
- **Observability**: structured JSON logs, `/healthz` (liveness),
  `/readyz` (dependency checks: DB, Redis, object storage), Celery queue
  depth metrics — see ROADMAP Phase 11.
- **Configuration**: all environment-specific values via environment
  variables (`.env`, never committed); see `.env.example`.

## 10. What This Document Deliberately Does Not Cover

- Exact Django app boundaries and models → [DATA_MODEL.md](DATA_MODEL.md)
- Threats and mitigations → [THREAT_MODEL.md](../security/THREAT_MODEL.md)
- Concrete role/permission list → [PERMISSIONS.md](../security/PERMISSIONS.md)
- How to actually stand this up locally → [LOCAL_DEPLOYMENT.md](../deployment/LOCAL_DEPLOYMENT.md)
- Phase sequencing → [ROADMAP.md](ROADMAP.md)
