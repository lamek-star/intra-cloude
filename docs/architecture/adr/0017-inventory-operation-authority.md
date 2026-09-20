# ADR-0017 — Business-operation authority over stock

Status: accepted; implemented and qualified for the Spare Parts / Inventory & Sales flagship.
Date: 2026-09-20. Amends ADR-0016's "authority over the movement and balance models"; builds on ADR-0008
(capability-based authorization) and ADR-0016 (quantity ledger). No new datastore, identity provider or
orchestration.

## Problem (found by qualification, not assumed)

ADR-0016 made authority over a stock movement equal to write access to two models: the movement model and its
balance model. A sale and a receive both write exactly those two models. The restricted-cashier qualification
proved the consequence: a cashier who could sell could also post a positive `receive` movement (HTTP 201, on-hand
93 → 94) or a negative movement that is not a sale. The PostgreSQL ledger kept the books consistent, and the
action was audited, but the server could not say **"may sell, may not receive or adjust"**. Authority was attached
to tables when it belongs to business operations.

## Decision

**Authority belongs to the business operation.** Four stable, default-deny capabilities, checked with the ordinary
`has_permission` (no role name is ever consulted):

| Capability | Meaning |
|---|---|
| `inventory.sell` | Record a sale in an installed application |
| `inventory.receive` | Receive stock into a warehouse |
| `inventory.adjust` | Write arbitrary stock movements through the record API (no adjustment workflow exists in v1.0) |
| `inventory.transfer` | Move stock between warehouses (authority defined; no transfer workflow exists in v1.0) |

They deliberately do not overlap: **may sell ≠ may receive ≠ may adjust ≠ may transfer**, in every direction. They are
scoped to one installed application: a grant is either a role (organization-wide; `organization-administrator`
holds all four) or a `ResourceGrant`/`ShareGrant` on the AppInstance (share resource type `inventory_operations`,
levels `sell` / `receive` / `adjust` / `transfer`, one permission each). A grant on one application is nothing on
another.

The three concerns stay separate:

```
User
  → business-operation authority        "may this actor perform THIS operation?"   (inventory_authority.py)
  → existing resource/module/org-unit   "may they write the sales documents?"       (records.py, unchanged)
  → atomic business operation           "which records commit together?"           (transactions.py)
  → StockMovement
  → PostgreSQL quantity ledger          "is this inventory transition valid?"      (quantity_ledger.py, unchanged)
  → inventory balance
```

### Controlled operations, not caller-built movements

The browser states an **intent**; the server builds the records:

* `POST /api/v1/app-instances/<id>/operations/sell/` — customer, invoice number, `occurred_at`, lines
  (`part`, `warehouse`, `quantity`, `unit_price`). Requires `inventory.sell`. The server records the order, one line
  and one stock-out movement per item, and the invoice, in one transaction.
* `POST /api/v1/app-instances/<id>/operations/receive/` — part, warehouse, quantity, optional supplier and unit
  cost, reference, `occurred_at`. Requires `inventory.receive`. The server records the stock-in movement and, when a
  supplier is named, a received purchase order and line.

Both require an `Idempotency-Key`, are human-session only (never bearer-token clients), validate input strictly and
commit nothing on any rejection. The movement inside them is authorized **by the operation**, not by write access to
the stock tables: a cashier holds `inventory.sell` plus write access to the sales-order, order-line and invoice
models — **no write access to inventory or stock movements at all**. Existing per-model restrictions keep applying
to everything else the operation writes (a user without write access to the invoice model cannot sell; a receive
that records a supplier needs the purchase-order models).

### Direct movement bypass is closed

Creating, updating or deleting a stock movement through the record API or the generic transaction endpoint now
requires `inventory.adjust` **and** ADR-0016's write access to both ledger models. Only the two operations above
create a movement without it, and they do so through a Python argument to `records.create_record`
(`movement_operation`) that no request can reach: there is no flag, token, header or query parameter, and a request
that names its own operation is simply an ordinary movement write that needs `inventory.adjust`.

### What is unchanged

The PostgreSQL ledger still alone decides whether a balance is valid: negative-balance refusal, movement
immutability, balance protection, dimension and TRUNCATE protection. An oversell is still refused by the database
even for an actor with full authority and leaves no order, line, movement or invoice behind.

## Consequences

* **Least privilege improves.** The cashier no longer needs (and no longer has) write access to stock tables.
* **Revocation is immediate.** Authority is evaluated against current grants on every operation; the very next sale
  after revoking `sell` is refused, with nothing committed, and the refusal is audited as a `denied` event carrying
  the missing capability. Successful operations are audited as `inventory.sell` / `inventory.receive`.
* **External API clients** (bearer-token `Application`s) that wrote stock movements through the record API now need an
  explicit `inventory.adjust` grant on the application. That is intended: writing an arbitrary movement is an
  adjustment. The operation endpoints are not exposed to bearer tokens.
* **Existing installations.** Roles are seeded from the catalog, so re-running `seed_permissions` (already part of
  the upgrade procedure) gives `organization-administrator` the four capabilities. Customers who had granted a
  cashier write access to stock tables must grant `sell` instead; the sale screens now use the operation endpoints
  and would otherwise be refused. No data migration is needed. The sharing table gains four allowed `level` values
  (a migration that changes only choices).
* **Not built (feature freeze):** no adjustment or transfer workflow. Their authorities exist so a future workflow
  has a default-deny home; `adjust` today only governs direct movement writes.
* **Known limits, stated so nobody assumes more:** authority is per application, not per warehouse or per unit
  (organizational-unit scoping still applies to the records an operation writes, through the existing module rules);
  there are no field-level permissions (a cashier who can read a product also sees its cost); and there is no
  "own sales only" rule.

## Alternatives rejected

* *Infer the operation from `movement_type` or the sign of the delta.* Both are caller-supplied; a rule keyed on
  them is a rule the caller writes.
* *A hidden "trusted" flag on the record API.* Forgeable by construction; the controlled path is a Python-level
  argument instead.
* *Per-movement-type permissions on the generic record API.* Authorizes a string the client chooses and leaves the
  caller assembling stock movements; the operation, not the row, is the unit of authority.
