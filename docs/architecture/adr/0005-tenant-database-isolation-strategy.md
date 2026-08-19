# ADR-0005: Tenant Database Isolation Strategy — Schema-Per-Organization Within Shared Tenant PostgreSQL Cluster(s)

Status: Accepted
Date: 2026-08-07

## Decision

User-created relational databases (the "database builder" feature) are
implemented as one PostgreSQL **schema per organization** (`org_<uuid>`,
further namespaced per logical `TenantDatabase` as `org_<uuid>__db_<uuid>`),
inside one or more shared "tenant" PostgreSQL clusters — not one full
Postgres instance per organization, and not a single shared schema
distinguished only by an `organization_id` column.

## Context

This is the highest-stakes data-model decision in the platform: it directly
determines how strong the isolation guarantee is between organizations for
the feature most likely to hold sensitive structured business data, and it
has real operational cost implications (Section 4, Section 6 of the master
prompt).

## Alternatives Considered

1. **One Postgres instance/cluster per organization.** Strongest isolation
   (separate process, separate connection, separate resource limits) but
   operationally expensive at scale (hundreds of orgs → hundreds of Postgres
   processes/containers), complicates connection pooling, backup
   orchestration, and monitoring.
2. **One shared schema, all tenant tables carry an `organization_id`
   column**, relying entirely on application-layer `WHERE` filtering (and
   optionally Postgres Row-Level Security policies). Cheapest operationally,
   but the *entire* isolation guarantee rests on every query everywhere
   remembering to filter correctly (or RLS policies being flawless) — a
   single missed filter is a full cross-tenant data leak, and it directly
   conflicts with Section 6's requirement to not depend solely on
   filtering for isolation.
3. **(Chosen) Schema-per-organization within a shared cluster.** Each
   organization's tables live in their own Postgres schema; the
   application's tenant-database connection role is granted access scoped
   to schemas it should reach (enforced by Postgres itself via `GRANT`/
   `search_path`, not only by application code); user-created tables
   within an org's schema are further namespaced per `TenantDatabase`.

## Advantages (of the chosen approach)

- Defense in depth: even a missed application-layer authorization check
  cannot trivially return another organization's rows, because the query
  executes against a different schema/role boundary, not just a different
  `WHERE` clause — directly satisfies Section 6's "never depend solely on
  UI/application filtering" requirement.
- Operationally realistic: schemas are cheap to create in PostgreSQL
  (unlike whole instances), and a shared cluster can be monitored, backed
  up, and connection-pooled as one system while still supporting per-schema
  `pg_dump` for export/backup granularity.
- Matches how the "database builder" and "CSV import" features naturally
  operate: DDL is scoped to one schema, so it's straightforward to validate
  that operations stay inside the caller's own schema.
- Leaves room to graduate a large or highly sensitive organization to its
  own dedicated cluster later (the `TenantDatabase` catalog already records
  which physical cluster a schema lives on) without a redesign — this is
  the scaling escape hatch, deferred until actually needed.

## Disadvantages

- More complex than a single shared-table design: every schema-modifying
  operation must dynamically target the correct schema, requiring the
  strict identifier validation and safe quoting mandated in Section 5/9.
- A single Postgres cluster is still a shared fault domain for all
  organizations on it (an outage affects everyone on that cluster) — 
  mitigated by clustering/replication at the infrastructure level and by
  the ability to shard organizations across multiple tenant clusters.
- Schema proliferation at very large scale (thousands of orgs) needs
  monitoring (catalog bloat, `pg_class` size) — acceptable for the target
  self-hosted organizational scale; revisit if that assumption changes.

## Security Considerations

- The Django application's Postgres role for tenant operations is not
  superuser and is granted privileges only on schemas it creates/owns; it
  never has blanket cross-schema `SELECT`/`ALL` grants.
- All dynamic schema/table/column identifiers go through the strict
  validation + safe-quoting rule from Section 5 of the master prompt
  regardless of this ADR — schema-per-org isolation is a second layer, not
  a replacement for identifier safety.
- Tenant isolation tests (THREAT_MODEL.md Section 4) must include a test
  that directly attempts a cross-schema query using another organization's
  `TenantDatabase` identifier and confirms it is rejected before it ever
  reaches Postgres, in addition to relying on the schema boundary itself.

## Operational Considerations

- Backup granularity: per-schema `pg_dump` supports exporting/restoring a
  single organization's tenant data independently (useful for org
  offboarding, targeted restore) alongside full-cluster physical backups.
- Migration path: if a specific organization needs dedicated hardware
  (compliance, noisy-neighbor performance isolation), the catalog's
  cluster-reference field makes moving its schema to a new cluster a
  data-migration task, not an architecture change.

## Final Recommendation

Adopt schema-per-organization within a shared tenant PostgreSQL cluster as
the default for Phase 4 (Database Builder). Revisit only via a new ADR if
a concrete scale or compliance requirement demands per-organization
clusters for specific tenants.

## Implementation Note (added Phase 12, 2026-08-19)

The naming scheme actually implemented is `db_<tenant-database-uuid-hex>`
— one schema per `TenantDatabase`, not the `org_<uuid>` /
`org_<uuid>__db_<uuid>` pattern sketched above. The nested pattern is 73
characters, over PostgreSQL's 63-byte identifier limit; this was found
by actually attempting to create a schema with that name (see
DATA_MODEL.md Section 3.5). The isolation property this ADR is actually
about — a missed application-layer filter cannot return another
organization's rows — is unaffected: every schema still maps to exactly
one organization via `project.workspace.organization`, so drawing the
schema boundary at the TenantDatabase level rather than nesting it
inside a per-organization schema is a naming/implementation detail, not
a change to the decision itself. Left as a note here, rather than
editing the Decision/Advantages sections above, so this document stays
an accurate record of what was decided and why — see DATA_MODEL.md
Section 3.5 and THREAT_MODEL.md Section 4 for the current, accurate
naming.
