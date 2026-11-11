# App Platform Phase 8 -- Management templates

Status: **COMPLETE**, 2026-09-16 on `feature/app-platform`, right after
Phase 7's completion (`8f7d227`). Per [the roadmap](APP_PLATFORM_ROADMAP.md):
"Configured templates for school, HR, CRM, procurement, assets, projects,
documents and warehouses; representative end-to-end scenarios."

The user explicitly chose to build all eight templates in a single pass
rather than one-template-per-checkpoint (the option this session offered,
mirroring Phase 7's own per-step checkpoint discipline) -- this doc is the
one checkpoint covering all eight.

## What was built

Eight new reference-application templates, at the same depth as Phase 4's
"Spare Parts" template and built from the exact same generic primitives
(Phases 1-3 scalar fields/relationships/composite constraints, Phase 6/7's
`org_unit_reference` field) -- no industry-specific concept was added to
`app_platform` itself for any of them:

| Template | Models | Relationships | Distinguishing feature proven |
|---|---|---|---|
| School -- Enrollment & Records | 11 | 10 | Relationship-only composite constraint (Student x Class Section); native many-to-many (Student<->Guardian) |
| HR -- Workforce & Payroll | 9 | 10 | Self-referencing `manager` relationship; `org_unit_reference` field; mixed field+relationship composite constraint |
| CRM -- Sales Pipeline | 8 | 9 | Nullable (`set_null`) relationship; native many-to-many (Campaign<->Contact) |
| Procurement -- Requisition to Pay | 9 | 11 | Relationship-only composite constraint (Goods Receipt Line); two nullable relationships |
| Assets -- Lifecycle & Depreciation | 8 | 7 | Two independent `org_unit_reference` fields on different models; mixed composite constraint |
| Projects -- Delivery & Time Tracking | 8 | 8 | Nullable relationship; native many-to-many (Project<->Tag) |
| Documents -- Library & Review | 6 | 6 | Self-referencing folder hierarchy; mixed composite constraint; native many-to-many (Document<->Tag) |
| Warehouses -- Bin-Level Logistics | 10 | 12 | Relationship-only composite constraint (Stock Level); two distinct relationships from one model to the same target model |

Total: 78 models, 73 relationships across the eight new templates, on top
of Phase 4's existing 13/14.

## Design: package, not eight copy-pasted modules

`app_platform/reference_templates.py` (a single 283-line module) became
`app_platform/reference_templates/`, a package:

- `_helpers.py` -- the three pure builder functions (`_field`/`_model`/
  `_relationship`) Phase 4's module defined inline, now shared by every
  template module rather than duplicated.
- `spare_parts.py` -- Phase 4's module, moved as-is (same function name,
  same logic, only its two helper-import lines changed) so
  `test_spare_parts_reference_template.py` and
  `seed_spare_parts_reference_app.py` needed zero changes.
- `school.py`, `hr.py`, `crm.py`, `procurement.py`, `assets.py`,
  `projects.py`, `documents.py`, `warehouses.py` -- one module per new
  template, same shape as `spare_parts.py`.
- `__init__.py` -- re-exports every `*_reference_definition` function
  (so `from app_platform.reference_templates import
  spare_parts_reference_definition` still works unchanged) and defines
  `REGISTRY`, a `{key: {"label", "builder"}}` map that is now the single
  source of truth both seed commands publish from.

### Generic seeding command, not eight near-duplicate ones

`seed_spare_parts_reference_app.py` (Phase 4) is ~90 lines of
create-template/publish/install/provision orchestration. Copy-pasting
that eight times would violate this repo's own "don't duplicate business
logic" rule. Instead, `app_platform/management/commands/
seed_reference_app.py` is the same orchestration once, generic over
`REGISTRY`: `python manage.py seed_reference_app --template <key>
--organization <id> --actor-email <email> [--project <id>] [--provision]`.
It works for all nine registry entries, including `spare_parts` itself
(kept for compatibility, not routed through the new command, since
nothing required touching it and it was already qualified in Phase 4).

## Scope decisions (deliberate, not gaps)

Applied consistently across all eight templates, matching Phase 4's own
precedent:

- **No calculated/derived fields.** Totals, book values, line totals, and
  similar are plain caller-computed-and-written scalars; the platform has
  no formula/computed-column concept.
- **No enum/status type.** Every `status`/`stage`/`decision`/`severity`
  field stays free text, as in Spare Parts.
- **No workflow-engine (Phase 5) wiring.** Nothing here creates a
  `WorkflowDefinition` for any template's status field. Phase 5 already
  proved that capability generically; wiring it onto eight specific
  templates is feature-composition work distinct from this phase's own
  exit bar (breadth of domain coverage), and is tracked as a known limit
  below rather than silently added or silently skipped.
- **No cross-template relationships.** Each template's models can only
  reference models within the *same* template (e.g. Assets' `asset_
  assignment` names a plain `org_unit_reference`, never an `Employee` from
  the separate HR template) -- installed instances are independent
  installations of independent `AppTemplate`s, not a shared schema.
- **Documents' file storage reuses the existing generic per-record
  attachment API** (Phase 2) rather than inventing a template-scoped file
  field -- consistent with "no industry-specific concept added to
  `app_platform`."
- **Warehouses is deliberately distinct from Spare Parts' own
  `Inventory`/`Warehouse` models**, not a duplicate: Spare Parts models a
  single-level quantity-per-(part, warehouse) count for an auto-parts
  sales business; Warehouses models bin-level logistics (zones, bins,
  inbound/outbound shipments, inter-warehouse transfers) with no sales/
  purchasing concept of its own. Different depths of the same broad
  domain, not redundant business logic.

## A real bug found and fixed during live verification

Running `seed_reference_app` against the actual persistent dev stack (not
the ephemeral `manage.py test` database) failed for the HR and Assets
templates -- both use `org_unit_reference` -- with a real Postgres
`IntegrityError`: `new row for relation "app_platform_fielddefinition"
violates check constraint "app_field_type_valid"`.

`manage.py showmigrations` on the running `backend` container showed
Phase 7's own `0015_org_unit_reference_field` and `0016_unitscopedgrant`
migrations were **never applied** to this persistent database -- the
identical class of gap Phase 4's own report already flagged once
(`manage.py test` always migrates a fresh ephemeral database, so a gap
between "migration exists in the repo" and "migration is applied to the
actual running stack" never surfaces there). Fixed with a real
`manage.py migrate app_platform` against the live container, then the
two previously-failed seed runs (which had already created valid,
harmless template/version rows before failing at the install step)
succeeded on retry, proving the command's idempotency (`Reusing existing
template`/`Reusing existing version`) works as designed, not just in
theory.

## Test evidence

62 new tests across eight files
(`app_platform/tests/test_{school,hr,crm,procurement,assets,projects,
documents,warehouses}_reference_template.py`), each following Phase 4's
exact three-tier structure:

- **`DraftValidationTests`** -- the draft validates cleanly against
  `validate_definition`, with the expected model/relationship counts, and
  (where applicable) the expected constraint shape (field-only,
  relationship-only, or mixed).
- **`InstallTests`** -- every model is created on install; the
  template's distinguishing feature (self-reference, many-to-many,
  nullable relationship, `org_unit_reference` field, two distinct
  relationships to the same target) resolves to real definition rows.
- **`ProvisioningAndWorkflowTests`** (`TransactionTestCase`, real
  provisioning against real Postgres, real HTTP requests through the
  actual record API as a real authenticated user) -- the template's
  composite constraint is a real unique index in the provisioned schema,
  a genuine duplicate is rejected with `400` through the real API (not
  merely coincidentally paired with a missing-required-field 400 --
  duplicate-rejection payloads were checked to include every field
  actually `required=True` on that model, and two were fixed
  (`payroll_record`, `enrollment`, `goods_receipt_line`,
  `stock_level`) after being caught testing the wrong failure reason),
  and a representative multi-model business scenario for that domain
  completes end to end.

Cross-org isolation (IDOR) is not re-tested per template, for the same
reason Phase 4's own suite gives: none of these templates introduce a new
endpoint or resource type, only definitions installed through the
existing, already-isolation-tested `app_platform` pipeline.

Regression scope: `app_platform` + `databases` + `org_units` +
`organizations` + `permissions` + `sharing` + `analytics` + `exports` +
`imports` together (622 tests) pass clean, 2 skipped (pre-existing,
unrelated to this phase) -- run under `config.settings.test`, which is
required for `TransactionTestCase`-based record-API tests in this
container image (`config.settings.prod`'s `SECURE_SSL_REDIRECT` makes
Django's test client's plain-HTTP requests bounce through a 301 the test
client doesn't follow; a purely local, environment-level distinction, not
a code change).

## Live verification against the running Docker stack

Beyond the automated suite: a real organization ("Phase 8 Reference
Apps"), project, and owner user were created against the live persistent
control-plane database, and `seed_reference_app --provision` was run for
all eight new templates (plus the pre-existing Spare Parts command
untouched) -- each produced a real `AppTemplate`, published `AppTemplate
Version`, installed `AppInstance`, and a real `RuntimeProvision` with its
own per-organization tenant schema. This run is what surfaced the
migration gap above.

A genuine HTTP round trip through the real Caddy proxy (`https://
localhost:8443`, not the Django test client) then exercised the
Warehouses instance end to end as a real logged-in session: CSRF token
fetch, session login, `GET` the instance's models/fields, `POST` a real
Warehouse record (`201`, a real row in the real provisioned schema), a
second `POST` with the same `code` value genuinely rejected by the real
unique constraint (`400`), `GET` the list reflecting the one persisted
row, then `DELETE` and logout to leave the demo organization clean.

## Known limits (honest, not silently absorbed)

- **No browser-based UI verification this pass.** The Claude-in-Chrome
  browser extension was unavailable in this session, so the App Builder
  and record-detail pages were not visually confirmed rendering these
  eight new instances the way Phase 3/4 confirmed for the App Builder
  and Spare Parts. The generic frontend already renders any installed
  instance by definition metadata alone (proven for Spare Parts and every
  earlier template), so this is a verification gap for this specific
  session, not a known frontend defect -- tracked here rather than
  assumed away.
- **No workflow-engine (Phase 5) wiring for any template**, as scoped
  above -- every `status`-shaped field across all eight templates stays
  free text with no `WorkflowDefinition`/state machine attached.
- **No frontend-specific test additions.** These templates only exercise
  the existing generic backend API and the existing generic frontend
  rendering path; no new frontend code was written or needed.
- **The persistent dev stack's control-plane database had unapplied
  migrations before this phase's own live verification run** (see above)
  -- now applied, but this is the second time this exact class of gap
  (repo has the migration; the long-lived dev container never got
  `manage.py migrate` re-run against it) has been caught only by live
  verification, not by the automated suite. A pre-flight `manage.py
  migrate --check` step before any live-verification pass would catch
  this class of gap earlier; not implemented here as it is a process
  change, not a Phase 8 deliverable.
