# Chapter 1 — Architecture — The two planes (ADR-0001, ADR-0005)

Topic for: software engineers. Source: IntraForge Engineering Handbook, Chapter 1 — Architecture.

Django is the **control plane**: it *describes, authorizes and audits* access to data. It never stores large files and
is never the store for business data. The **data plane** is PostgreSQL (tenant database) and object storage.

- **postgres-control** holds the catalog — who exists, what they may do, which resources exist and where.
- **postgres-tenant** holds business data. Each organization gets its own PostgreSQL schema, so one organization's
  tables are physically separate from another's, not rows filtered by an `organization_id`.
- **Object storage** holds files; Django keeps only their metadata (`FileObject`, `FileVersion`).

`config/db_routers.py` keeps Django's own models on the control database; tenant tables are reached through explicit,
quoted SQL (`databases/rows.py`, `app_platform/records.py`) on the tenant connection.
