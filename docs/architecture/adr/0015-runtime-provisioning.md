# ADR-0015: Resumable application runtime provisioning

Status: accepted for the Phase 2 provisioning step, 2026-09-09.

Business records use the existing tenant PostgreSQL catalog/services (ADR-0014).
Control metadata and tenant DDL cannot commit atomically. Reuse the durable
restore pattern: reserve an immutable operation first, serialize publication,
commit tenant work first, then publish the control catalog and success audit.

An instance has one RuntimeProvision receipt containing the pinned preflight
plan/fingerprint. Its creation freezes structural definitions; labels remain
editable. A Celery task uses the existing validated database services under
outer tenant/control transactions, with a tenant advisory lock. It creates
the deterministic database from the plan, then tables, fields and real FKs.
The ready receipt stores catalog UUID mappings and a protected database FK.

Reconciliation may rebuild only a pending operation's deterministic schema,
with no catalog owner by UUID or schema name, and an exact schema comment
matching the receipt identity and fingerprint. A schema lacking this ownership
marker causes a conflict; it is never dropped automatically. The marker and
DDL commit together. Once the catalog/receipt is ready, retries return it
without rewriting records. Worker loss is redelivered; ordinary failures are
recorded without raw values and can be retried explicitly. An enqueue outage
can leave a pending receipt; repeating the POST re-enqueues it. No transactional
broker outbox or claim of exactly-once task delivery is introduced.

Provisioning requires active human membership, app_instance.schema.manage
for the instance, and organization-wide database.create/database.schema.manage.
These are real shared checks; there is no privileged synthetic actor. The task
rechecks its requesting actor's current authority. App metadata access remains
human-only. This step introduces no separate app record permission policy:
the resulting managed database's records still use existing database.* checks,
including Environment credential isolation. New app-specific CRUD, attachment
and integration contracts remain later Phase 2 work. Existing database grants
are not silently replaced or claimed to provide record-level app isolation.

Ordinary database schema services refuse mutations on a published runtime's
database. Definition structural edits are rejected until a migration-aware
builder exists; renaming display labels remains safe. Full control and tenant
backups jointly preserve bindings and data. Portable .icp continues to exclude
App Platform metadata, so runtime data exported through its existing database
scope is restored as ordinary data, never claimed to be a reconstructed app.
No automatic template upgrade, destructive runtime delete, or configuration
restore is added here.
