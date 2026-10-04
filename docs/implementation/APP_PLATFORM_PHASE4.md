# App Platform Phase 4 — Inventory and Sales reference application

Status: **COMPLETE**, 2026-09-15 on `feature/app-platform`, right after
Phase 3's completion (`886e75f`). Per [the roadmap](APP_PLATFORM_ROADMAP.md):
"Spare-parts template covering inventory, purchasing and sales; real
business scenario; no industry-specific core models."

## What this phase proves

That the generic App Platform (Phases 1–3) can express a real,
non-trivial business application end to end using nothing but its own
existing primitives — scalar fields, `many_to_one`/`many_to_many`
relationships, composite unique constraints — with **no new concept added
to `app_platform` itself**. `docs/SPARE_PARTS_INTEGRATION_READINESS.md`
already did the capability analysis for exactly this scenario (§12: "READY
FOR SPARE PARTS ADAPTER PROTOTYPE"); this phase turns that analysis into a
real, installable, provisioned, live-verified reference template.

## A real gap found and closed first

Scoping this phase's Inventory model (`(Part, Warehouse)` must be unique)
found that the composite-uniqueness capability the readiness doc described
as closed was not actually usable for this case: `ConstraintDefinition`
only ever accepted scalar `FieldDefinition` members — there was no path
from a `RelationshipDefinition` to a constraint, even though `part`/
`warehouse` are necessarily relationships, not fields. This was a real,
previously undiscovered gap, not a documentation lag (see
`docs/SPARE_PARTS_INTEGRATION_READINESS.md` §1's composite-constraint row
for the before/after).

Closed generically, not as an Inventory-specific workaround, before
building the reference template itself:

- **Migration `0013_constraint_relationships.py`**: `ConstraintDefinition`
  gains a second M2M, `relationships` (parallel to the existing `fields`),
  plus a new trigger guard (`app_runtime_constraint_relationships_guard`)
  on the new through table, mirroring `0012`'s existing `fields`-guard.
- **Eligibility rule**: a relationship may only participate in a
  constraint on its own model — `relationship.source_model == constraint.
  model` and `relationship.kind == "many_to_one"`. A `many_to_many`
  relationship has no column on either side (it's a join table) and is
  never eligible — `many_to_many` behavior is completely untouched by this
  feature.
- **`definitions.py`**: `ConstraintInput` gains `relationship_ids`
  alongside `field_ids`; combined length must be ≥2. `DefinitionInput.
  validate()` checks each `relationship_id` resolves to an eligible
  relationship in the same draft.
- **`instances.py`**: `install()` reordered — constraints are now created
  in a pass *after* relationships exist (previously nested inside the
  per-model loop, before relationships were built at all), so a
  relationship-backed constraint resolves correctly regardless of its
  position in the draft's own JSON arrays. `add_constraint()` resolves
  `relationship_ids` via `model.outgoing.get(pk=id, kind="many_to_one")`.
- **`runtime_plan.py`/`runtime_build.py`**: the plan/fresh-provisioning
  build carries `relationship_ids` through; `runtime_build.build()` was
  restructured into three passes (tables+fields → relationships →
  constraints) since a constraint spanning a relationship's FK column
  can't be built before that column exists.
- **`schema_evolution.py`**: `add_constraint_to_runtime` (live addition to
  an already-provisioned instance) resolves relationship members via a new
  `_column_for_relationship` helper.
- **API/App Builder**: `ConstraintSerializer` gains `relationship_ids`;
  both the template draft editor (`app-templates/[templateId]`) and the
  live per-instance Constraints editor (`app-models/[modelId]`) now render
  a model's own eligible (`many_to_one`) relationships as additional
  checkboxes alongside its fields, with matching dangling-reference
  cascades on model/field/relationship deletion.
- **Tests**: `app_platform/tests/test_composite_constraints.py` extended
  with relationship-only and mixed field+relationship variants of every
  existing test class (draft validation, install ordering, fresh
  provisioning, live addition to a populated instance, NULL semantics,
  concurrency, tenant isolation, direct-ORM-write trigger-guard parity) —
  24 new tests, all passing alongside the existing 179.
- **Live-verified**, not just unit-tested: a real template (`Item`
  many_to_one to `Bin` and `Shelf`) built through the actual App Builder
  UI, published, installed, and provisioned against the running Docker
  stack; a duplicate `(Label, Bin)` combination on the record API was
  genuinely rejected ("a record with this value already exists") through
  the browser, not asserted by a test in isolation. This pass also found
  and fixed an unrelated pre-existing gap in this dev environment: neither
  migration `0011` nor `0012` (from an earlier session) had ever actually
  been applied to the live control-plane database — only to Django's
  ephemeral test database, which migrates fresh on every run and so never
  surfaced the gap. `python manage.py migrate app_platform` closed it.

Full detail: `docs/SPARE_PARTS_INTEGRATION_READINESS.md` §1/§10/§11,
`docs/EXTERNAL_APP_API_CONTRACT.md`'s constraint section, and
`ConstraintDefinition`'s own docstring (`app_platform/models.py`).

## The reference template

A single new AppTemplate, **"Spare Parts — Inventory & Sales"**
(`app_platform/reference_templates.py::spare_parts_reference_definition()`),
built and published through the same `templates.py`/`instances.py`/
`runtime_plan.py`/`provisioning.py`/`runtime_build.py` pipeline every
other template uses — no pipeline changes beyond the constraint work
above. 13 models, 14 relationships (13 `many_to_one`, 1 `many_to_many`),
1 relationship-backed composite constraint:

| Model | Purpose | Notable |
|---|---|---|
| `Part` | Catalog item | `is_active` boolean, cost/price decimals |
| `PartNumber` | Numbers referencing a Part | `number` unique+indexed; self-referencing `supersedes` (cross-reference/supersession) |
| `Vehicle` | Fitment target | — |
| `Warehouse` | Stock location | `code` unique |
| `Inventory` | Quantity per Part×Warehouse | **composite `UNIQUE` over two relationships**, not fields — the capability this phase closed |
| `StockMovement` | Quantity deltas | Not atomic with an Inventory update — see Known limits |
| `Supplier`, `PurchaseOrder`, `PurchaseOrderLine` | Purchasing | — |
| `Customer`, `SalesOrder`, `SalesOrderLine`, `Invoice` | Sales | `Invoice.invoice_number` unique+indexed |

Plus native `many_to_many`: `Part` ↔ `Vehicle` ("compatible_vehicles") —
real join table, frontend multi-select picker already existed from an
earlier phase.

Relationship keys are unique **per instance**, not per owning model
(`RelationshipDefinition`'s own `(instance, key)` constraint) — several
models here reference the same target (Part, Warehouse, Sales Order), so
those keys are prefixed by owning model (e.g. `purchase_order_line_part`,
`invoice_sales_order`) to stay distinct. This is purely an internal
identifier; the App Builder UI and record API only ever surface each
relationship's `label` ("Part", "Sales Order"), never its `key`.

**Deliberately excluded**, each a documented decision, not an oversight:

- **No `CataloguePart`/`CompanyProduct` split** — that's what the
  separately-shipped `catalogue_storage` app already does (external OEM
  catalogue vs. company data); re-modeling it here would duplicate it.
- **No calculated/derived fields** — `line_total`/`total_amount`/
  `amount_due` are plain decimals the caller computes and writes; the
  platform has no formula/computed-column concept.
- **No enum/status type** — `status` fields stay free text, same as
  everywhere else in the platform.
- **No cross-request atomicity** — "PO received → StockMovement →
  Inventory update" stays multiple separate record-CRUD calls; no
  declarative multi-record action concept exists yet (readiness doc §9).

## Seeding it

```
python manage.py seed_spare_parts_reference_app \
    --organization <id-or-slug> --actor-email <email> \
    [--project <id>] [--provision]
```

(`app_platform/management/commands/seed_spare_parts_reference_app.py`.)
Never invents an organization or bypasses permissions — `--actor-email`
must name a real user with `app_template.manage` (and, with `--project`/
`--provision`, `app_instance.manage`) in that organization; the command is
a thin wrapper around the same service calls the App Builder UI uses.
Idempotent: reuses an existing non-archived template/version with the same
label on repeat runs rather than duplicating it. `--provision` runs the
full plan/reserve/execute cycle, standing up a real, working demo instance
in one command.

## Test evidence

- `app_platform/tests/test_spare_parts_reference_template.py` (9 tests):
  draft validates cleanly and has the expected relationship-only Inventory
  constraint; `instances.install` creates all 13 models with correct
  relationship/constraint membership (including the self-referencing
  `supersedes` relationship and the native `Part`↔`Vehicle` many-to-many);
  fresh provisioning materializes the real composite index; a full
  Supplier→PurchaseOrder→line / Part→PartNumber(supersession)→Inventory
  (with a genuine duplicate `(Part, Warehouse)` rejection) /
  Customer→SalesOrder→line→Invoice / Part↔Vehicle workflow through the
  actual record API.
- This closes the self-referencing-relationship gap
  `docs/SPARE_PARTS_INTEGRATION_READINESS.md` had explicitly flagged as
  "SUPPORTED (untested)... add one before relying on it" — `PartNumber.
  supersedes` depends on exactly that, and now has install/provisioning/
  record-API coverage.
- Full `app_platform` suite: 212 tests pass (179 baseline + 24 from the
  constraint-relationships work + 9 from this template), 0 failures,
  against real PostgreSQL (`TransactionTestCase`, `databases = {"default",
  "tenant"}`), not mocks.
- Cross-org isolation is not re-tested per-template: this template
  introduces no new endpoint or resource type, only definitions installed
  through the existing, already-isolation-tested `app_platform` pipeline
  (`test_foundation.py::test_every_resource_endpoint_denies_foreign_organization`
  and the per-feature isolation tests already covering constraints/
  relationships) — a deliberate decision, documented in the test file's
  own module docstring, not a silent gap.

## Live verification

Beyond the unit-test suite, run against the actual running Docker stack
(not just asserted): `seed_spare_parts_reference_app --provision` against
a real organization/project produced a working instance; inspecting the
provisioned schema directly confirmed a real unique Postgres index backing
the Inventory constraint, a real self-referencing foreign key for
`PartNumber.supersedes`, and a real many-to-many join table for `Part`↔
`Vehicle`. The instance's own App Builder page (`/app-instances/{id}`)
correctly listed all 13 models and all 14 relationships with clean labels;
the generic record-detail page for `Part` rendered every field type
correctly (text, decimal as a number input, boolean as a select, the
many-to-many field as a multi-select picker showing "No records to link
yet" for an empty case) with no rendering gap introduced by this template.

## Known limits (honest, not silently absorbed)

- `StockMovement` and `Inventory` are separate models by design (§9's
  atomicity gap is real platform-level work, not something this phase
  should paper over with bespoke glue code); keeping them in sync after a
  stock movement is the caller's responsibility today.
- No field-level "protect Part from being overwritten by a company-facing
  import" concept — same as documented for `catalogue_storage`'s relation
  to company data; application-level discipline, not a platform guarantee.
- Reporting/aggregation (e.g. "total inventory value") is out of scope —
  `analytics`'s existing dashboard capability can be pointed at this
  instance's tenant database separately if needed, not built into this
  phase.
