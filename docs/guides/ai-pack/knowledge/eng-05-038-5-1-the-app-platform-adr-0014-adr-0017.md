# Chapter 5 — Applications on IntraForge — 5.1 The App Platform (ADR-0014 – ADR-0017)

Topic for: software engineers. Source: IntraForge Engineering Handbook, Chapter 5 — Applications on IntraForge.

An application is a **definition**, not copied code.

1. **Template** (`AppTemplate`, `AppTemplateVersion`) — models, fields, relationships, constraints, workflows, labels.
   The format is strict, bounded and non-executable (`definitions.py`). A published version is **immutable**.
2. **Instance** (`AppInstance`) — one organization's installation of a version (`instances.py`).
3. **Runtime** — real tables in the organization's tenant schema, built by **provisioning** (`runtime_plan.py` plans,
   `provisioning.py` reserves and replays, `runtime_build.py` builds inside transactions). Provisioning is resumable:
   a crash part-way is finished on the next attempt, never duplicated.
4. **Records** — one generic CRUD engine for every instance (`records.py`, `record_views.py`), with relationships,
   attachments (`attachments.py`), unit-scoped access (`unit_scope.py`) and workflow transitions with optional
   approval (`workflows.py`).
5. **Schema evolution** — additive-only live changes to a populated runtime (`schema_evolution.py`).
6. **Upgrades** — a three-way diff between the install snapshot, the live configuration and the newer version: adds
   what is safe, never silently overwrites the customer's own changes (`upgrades.py`). Definitions get deterministic ids
   (`built_in_apps.stabilize_ids`) so a diff compares like with like.
7. **Webhooks** — record and workflow events delivered as HMAC-signed POSTs, **at least once**, with durable retry
   (`webhooks.py`, `delivery_transport.py`, `outbound_http.py`).

### The gallery and release status

`app_platform/built_in_apps.py` is the customer catalog. `install()` does the whole template → instance → runtime
sequence in one call through the same services (so every capability check still applies). Status is real:

| App | Status | Shown to customers |
|---|---|---|
| Spare Parts / Inventory & Sales | QUALIFIED | Yes |
| Pharmacy | PARTIALLY QUALIFIED | Only with `SHOW_UNQUALIFIED_BUILT_IN_APPS` |
| HR, School, Repair Shop, Rentals | EXPERIMENTAL | Only with the flag, clearly labelled |
| CRM, Procurement, Assets, Projects, Documents, Warehouses | DEFERRED | Never |

Promote an app to QUALIFIED only with evidence (main workflow in the normal UI, relationships, constraints,
permissions, restart, upgrade, backup and restore) and record where it lives in the entry's `evidence`.

### Stock: the ledger and operation authority

- **The database decides stock** (ADR-0016). Stock is a quantity ledger (`quantity_ledger.py`): a balance changes only
  by a movement, and PostgreSQL triggers enforce that balance = sum of movements and never below zero. No code in the
  browser, a view or a service does stock arithmetic.
- **Authority belongs to the operation** (ADR-0017, `inventory_authority.py`): `inventory.sell`, `.receive`, `.adjust`,
  `.transfer` are separate, default-deny capabilities. A cashier can sell but not receive.
- Selling and receiving go through `operations/sell` and `operations/receive` (`inventory_operations.py`): one atomic
  transaction (`transactions.py`), an **Idempotency-Key** is required (a double click cannot sell twice), human sessions
  only. A movement written through the generic record API needs `inventory.adjust`. Never add a way for the client to
  name the operation.
- Every record change is journalled in the tenant transaction and published to the control plane afterwards, replayably
  (`operation_journal.py`).

### Adding a new built-in application

1. Write a pure builder in `app_platform/reference_templates/<key>.py` using `_helpers.py` (copy `repair_shop.py` or
   `rentals.py` for a small one; `spare_parts.py` if it needs stock).
2. Add a `BuiltInApp` entry in `built_in_apps.py` with status EXPERIMENTAL.
3. If it needs custom screens, add them under `frontend/src/components/business/`; otherwise the generic record
   screens serve it.
4. Test: the builder validates; install provisions; records CRUD; permissions deny the wrong role; IDOR across
   organizations; upgrade from the previous version.
