# ADR-0001: Separate Control Plane (Django) from Data Plane (PostgreSQL + Object Storage)

Status: Accepted
Date: 2026-08-07

## Decision

Django owns metadata, identity, authorization, and orchestration only. It
never stores large binary blobs in its own database, and it never acts as
the durable, canonical store for tenant relational rows beyond the schema
catalog. Tenant relational data lives in dedicated PostgreSQL
schemas/instances; file blobs live in S3-compatible object storage.

## Context

The platform must support both large file storage and user-created
relational databases, at organizational scale, while remaining
self-hostable and simple to operate. A tempting shortcut is to let Django's
own database also hold file bytes and/or all tenant table rows directly.

## Alternatives Considered

1. Store files as BLOBs in the Django database.
2. Store all tenant relational data directly in Django-managed tables keyed
   by `organization_id`.
3. (Chosen) Strict control/data plane separation: Django orchestrates and
   authorizes; PostgreSQL (separate schemas/instances) and object storage
   hold the actual data.

## Advantages (of the chosen approach)

- Independent scaling: object storage and tenant Postgres can grow (more
  disks, more instances) without touching the control-plane database.
- Backup/restore granularity: control-plane, tenant data, and blobs can be
  backed up and restored on different schedules/targets appropriate to
  their size and change rate.
- Matches the master prompt's explicit architectural mandate (Section 2).
- Avoids Django ORM/connection-pool pressure from massive blob or row
  volume that has nothing to do with control-plane concerns.

## Disadvantages

- More moving parts than a single database for everything.
- Requires a real service layer for tenant DDL/DML instead of plain Django
  models for user data — more upfront engineering.
- Consistency between the control-plane catalog and actual tenant schema
  state must be actively maintained (same-transaction writes, reconciliation
  tooling).

## Security Considerations

- Reduces blast radius: a bug that dumps the control-plane database does
  not automatically dump every tenant's business data table content (though
  it would dump metadata about it).
- Requires careful transactional discipline so catalog and real schema
  never silently diverge in a way that hides unauthorized objects.

## Operational Considerations

- Three storage systems to operate (control PG, tenant PG, object storage)
  instead of one; documented explicitly in LOCAL_DEPLOYMENT.md and
  BACKUP_RESTORE.md.
- Health checks and monitoring must cover all three independently.

## Final Recommendation

Adopt strict separation as specified. This is treated as a load-bearing,
non-negotiable architectural rule per the master prompt, not merely a
preference.
