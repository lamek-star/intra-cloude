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

## Implementation status — quantity ledger (2026-09-19)

Implemented in `app_platform/quantity_ledger.py` (models `QuantityLedgerBinding`
/`QuantityLedgerDimension`, migration `0020_quantity_ledger`, endpoint
`app-instances/<id>/quantity-ledgers/`). `bind()` requires a provisioned
runtime, both models still empty, integer required fields, a balance field
defaulting to 0, at least two dimensions (a composite constraint needs two
members) and an existing composite `UNIQUE` constraint over exactly the
dimension relationships — the `ON CONFLICT` target of the installed upsert.
It installs, in the tenant schema, in one transaction:

| Trigger | Guarantee |
|---|---|
| AFTER INSERT on movements | Upserts the balance row in the same transaction; a raised error rolls back both. Rejects a NULL dimension (NULLs never conflict on `UNIQUE`, so they would create orphan balance rows) and, unless `allow_negative`, a resulting negative balance. |
| BEFORE UPDATE/DELETE on movements | Movements are append-only: quantity and dimension columns cannot change and a movement cannot be deleted; correct with a reversing movement. Other columns (a note, a reference) stay editable. |
| BEFORE INSERT/UPDATE/DELETE on balances | Balance and dimension columns cannot be edited, a balance row cannot be deleted, and a direct insert must start at 0 — unless issued from inside the movement trigger. The bypass requires the transaction-local flag **and** `pg_trigger_depth() > 1`, so a session that merely calls `set_config` is still rejected. |
| BEFORE TRUNCATE on both | `TRUNCATE` fires no row trigger, so it is guarded separately. |

`quantity_ledger.reconcile(binding)` independently compares every stored
balance with the sum of its movements and returns any discrepancy.

**Residual limits (documented, not hidden).** A database role able to alter
triggers (`ALTER TABLE … DISABLE TRIGGER`, `CREATE TRIGGER`, ownership) can
defeat any trigger. The opt-in least-privilege tenant role
(`provision_tenant_role`, THREAT_MODEL TB3) is the mitigation, and
`reconcile()` detects drift. Row deletion of a referenced Item/Warehouse whose
FK policy is CASCADE onto a guarded table fails closed (400) rather than
silently removing ledger rows. There is no unbind. There is no multi-leg
transfer endpoint yet, and inventory arithmetic exists only in the ledger.

**Evidence.** `app_platform/tests/test_quantity_ledger.py` — 39 tests against
real PostgreSQL: receive/sell, exact zero, insufficient stock, wrong
product/warehouse/foreign-organization ids, rollback after an induced failure,
idempotent replay, concurrent receives and sells (real threads), raw-SQL
bypass attempts (update, delete, truncate, dimension repointing, forged flag,
NULL dimension), movement immutability through both the API and raw SQL,
reconciliation including detected drift, binding contract, and cross-
organization isolation. The hardening tests were written first and failed
(12 of 39) against the initial implementation before the fixes; see
`ledger-hardening-reproduction.log` → `ledger-hardening-corrected.log`.
Still qualifying: transfers, and paired backup/restore of a ledger-bound
runtime (the destructive restore drill).
