# ADR-0016 — Tenant operation journal and quantity ledgers

Status: implementation decision for Local Edition; qualification pending.
Date: 2026-09-18. Extends ADR-0001/0005/0015 without a new datastore.

## Evidence and requirement

Inventory and Stock Movement currently commit independently. Ordinary record
mutation commits in tenant PostgreSQL before audit/webhook publication in
control PostgreSQL. Failure injection also proves that a broker failure can
surface as a failed record request after the record committed, and a receiver
can accept a webhook before its delivered marker is saved. Two independent
database transactions cannot provide the requested atomic business guarantee.

## Decision

Keep atomic business effects and their durable operation evidence in the same
tenant database transaction. Add a small internal operation journal inside
managed runtime schemas. It stores stable event/request identity, actor/model
identity, a non-sensitive audit context and, when needed, a tenant-only replay
response. It is not a second business datastore and is never exposed through
ordinary table browsing. A control-plane audit/webhook projection is retryable
and deduplicated by the durable event identity. Projection failures must be
observable and recoverable, not convert committed business work to failure.

Introduce an opt-in generic integer quantity ledger: administrator-validated
mapping between balance and append-only movement models, numeric fields and
matching relationship dimensions. Database triggers make a movement and its
balance effect atomic, reject insufficient quantity and prohibit bypass edits.
The same Part × Warehouse database constraint remains authoritative. New
configuration initially accepts empty models only; existing business data is
never silently reconciled or rewritten. Correcting a movement uses an explicit
reversing movement. Transfers use one tenant transaction containing both legs.

All mutations reuse capability checks, including authority over affected
balance and movement models. Environment/organization boundaries remain
enforced. No role-name branches or front-end synchronization substitute for
these checks. Internal DDL uses constant SQL templates and quoted, validated
runtime identifiers, operator/admin authorization and audit evidence.

## Delivery and recovery semantics

HTTP is not exactly-once or at-most-once: a receiver may accept a request
before the sender can durably acknowledge it. Use stable event IDs and
receiver deduplication with bounded retries. The operation journal closes
local commit/publication gaps; it cannot guarantee remote processing.
Control and tenant backup snapshots must still be matched while writes are
quiesced; this decision does not introduce distributed transactions.

## Qualification required

Rollback between effects; negative balance rejection; duplicate/conflicting
requests; concurrent receipts/sales; transfers; direct CRUD/import bypasses;
cross-tenant and revoked grants; process termination before/after tenant
commit; broker outage; audit-projection recovery; paired backup/restore.
No feature described here is marked qualified merely by this decision.
