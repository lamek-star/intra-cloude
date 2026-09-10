# App Platform Phase 3 — App Builder v1

Status: **IN PROGRESS**, started 2026-09-09 on `feature/app-platform`, right
after Phase 2's completion (`b91d9e8`). Per
[the roadmap](APP_PLATFORM_ROADMAP.md): "No-code model/field/form/list
editing; labels, defaults, required flags, ordering, relationships and basic
permissions; safe populated-schema changes." That is several genuinely
separate pieces of work, not one PR — split into reviewable steps below, the
same discipline Phase 2 used, per the roadmap's own rule that a step split
"does not make any unimplemented phase complete."

## What already exists (Phase 1/2), and what's actually new

Template/instance metadata CRUD already exists end-to-end in the backend
(`app_platform/templates.py`, `instances.py`): create a template, edit its
whole `draft` JSON (validated by `DefinitionInput`), publish an immutable
`AppTemplateVersion`, install an `AppInstance` from a version, and edit an
installed instance's models/fields/relationships granularly (frozen once a
runtime is provisioned, per Phase 2's `lock_active`). **None of this has a
frontend** — Phase 2 built only the record-consumption screens
(`/app-instances`, `/app-models`), never template authoring or installation.
That gap, using entirely existing, already-tested backend capability, is
step 1.

Genuinely new backend work, not yet designed or built:
- **Defaults**: `FieldDefinition`/`SnapshotField` have no default-value
  concept at all today.
- **Ordering**: display order for fields/models is just creation order
  (`Identity.Meta`); nothing lets a user choose form/list order.
- **Safe populated-schema changes**: `lock_active` freezes *all* structural
  edits the instant a runtime is provisioned — Phase 3 needs to allow
  additive changes (new field/model/relationship) against a live, possibly
  populated tenant schema, with real DDL and real safety checks (e.g. adding
  a `required` field to a table with existing rows needs a default to
  backfill, not just a server-side validation error).
- **Basic permissions**: undefined beyond three words in the roadmap. Per
  CLAUDE.md's "When Uncertain" rule, this needs its own short design
  decision (documented, not guessed) before implementation, not a silent
  reuse of an unrelated existing mechanism.

## Steps

1. **App Builder UI for existing capability.** Template
   list/create/edit, a draft model/field/relationship builder (label, key,
   data type, required — the fields `DefinitionInput` already validates),
   publish, version history, install into a project, and wiring the
   installed instance through to Phase 2's already-built provisioning and
   record screens. No backend changes; this step is exclusively making
   already-tested backend capability reachable without the API directly.
2. **Defaults and ordering — current step.** Extend `FieldDefinition`/the
   definition format with a validated default value per data type and an
   explicit display-order field for models/fields/relationships; extend the
   builder UI and the generated record screens (Phase 2) to use them.
3. **Safe populated-schema changes.** Allow additive structural edits
   (new field/model/relationship, and only those — no destructive/
   type-changing edits in v1) against an already-provisioned runtime,
   applying real DDL immediately through the same validated
   `databases.services` operations Phase 2's provisioning uses, with
   explicit backfill/default handling for a new required field on a
   populated table. Isolation and destructive-action tests required before
   this ships, per CLAUDE.md.
4. **Basic permissions.** A short design decision first (documented, not
   guessed): what "basic" means here — likely app-instance-scoped
   ResourceGrants reusing the existing capability mechanism (ADR-0008), not
   a new authorization system. Then the builder UI to assign it.
5. **Qualification.** Fresh full backend/security suite, browser workflows,
   lint/types/builds, migrations, cross-org isolation, grant revocation,
   backup/restore, and a final documentation/remaining-debt pass before
   Phase 3 is declared complete.

## Current step evidence

### Step 2: defaults and ordering (2026-09-10)

**Defaults.** `FieldDefinition` gains a validated `default_value`
(`JSONField`, `null=True`); the same field is added to the definition
format (`FieldInput`/`SnapshotField` in `definitions.py`) so a template
draft can declare one. Validation reuses `databases.ddl.default_clause_sql`
directly — called purely for its validation side effect, not duplicated —
so a default is rejected at definition time with the exact same rule that
would otherwise reject it as DDL at provisioning time; the two can never
drift apart. That reuse surfaced a real, narrow gap in
`databases/ddl.py` itself: **date columns had no default support at
all** (`"Date column defaults are not supported yet"`, one of only 6
app_platform field types) — fixed there directly, validated against
`DATE_FORMAT`, `test_ddl.py` updated to assert the new accepted behavior
instead of the old rejection. `runtime_plan.py` carries `default_value`
into the compiled plan and fingerprint (it affects real DDL, so it must);
`runtime_build.py` passes it straight into `services.add_column`'s
existing `default_value` parameter — no changes needed to
`app_platform/records.py` at all, since a value genuinely absent from a
create payload already makes `insert_row` omit that column from the
`INSERT`, letting Postgres's own `DEFAULT` apply. Defaults are editable
pre-provision via the existing `FieldPatch`/`update_definition` path
(cross-checked against the field's actual `data_type`, since a partial
patch doesn't resend it); once provisioned, changing one is still
"structural" and blocked by `lock_active`, same as before — that's
step 3's job, not this one's.

**Ordering.** `Definition` (the abstract base under `ModelDefinition`/
`FieldDefinition`/`RelationshipDefinition`) gains a `position`
(`PositiveIntegerField`) and its `Meta.ordering` changes from
`["created_at", "id"]` to `["position", "created_at", "id"]` — replacing
an implicit, tie-break-by-random-UUID ordering with an explicit, always-
reorderable one. `instances.install()` sets `position` from the
definition's array index (so template draft order becomes installed
order, deterministically); `add_model`/`add_field`/`add_relationship` set
it to the current sibling count (append-to-end). Reordering is
deliberately **exempt** from `lock_active`'s structural freeze — swapping
two `position` values touches no DDL, ever, so it's allowed on an
already-provisioned instance too, unlike every other definition edit.
`LabelInput` (shared by `FieldPatch`/`RelationshipPatch`) gains
`position`, reachable through the same PATCH endpoints as label edits.
The template draft format itself carries no separate position field —
array order already is the order, so the builder's move-up/move-down
buttons are pure client-side array swaps, PATCHing the whole draft back
same as every other builder edit.

Backend: `0006_ordering_and_defaults` migration. 5 new tests in a new
`test_defaults_ordering.py` (default-value type validation over the API,
append-position on create, PATCH-driven reordering, draft-array-order
becoming installed position, and a `TransactionTestCase` proving a real
omitted-field record pick up its column `DEFAULT` — text/boolean/date all
checked, read back both through the translated API response and the raw
physical row) plus the updated `test_ddl.py` case. Fresh full backend
gate: **490 passed, 2 skipped, 0 failed** (up from 485); Ruff and Mypy
clean.

Frontend: the template builder gets ▲/▼ move buttons on every model,
field, and relationship row; the "Add field" form gains a type-appropriate
default-value input (text/decimal/date as typed input, boolean as a
tri-state select, datetime restricted to a "default to current time"
checkbox — matching exactly what the backend will actually accept, not a
free-text field that fails server-side); a field's "Rename" action became
"Edit" (a modal with label *and* default value together, since both are
now editable the same way). Generic record forms (Phase 2) show a field's
default as input placeholder text (`Default: P3`) — a hint only; the
input stays genuinely empty until the user types, so leaving it blank
still omits the key from the payload and lets the database apply the
default, rather than the client silently re-submitting a stale copy of it.

`next build`, ESLint, and the Vitest suite all pass clean.
**Live-verified end-to-end in a real browser** against a rebuilt dev
stack (both containers rebuilt/restarted, migration applied): added a
field with default `P2` to the already-published "Bug Tracker" template,
confirmed the default badge rendered, moved it above the required
"Title" field with the new ▲ button, edited its default to `P3` through
the new "Edit field" modal, published a second version, installed a
fresh instance of it, provisioned the runtime, and created a record
through the generated form leaving "Priority" blank — the row came back
showing **Priority: P3**, the real Postgres column default applied by
the database itself, with the field-order badges on the model page
confirming Priority now renders before Title everywhere, exactly as
reordered in the builder.

See [TEST_STATUS.md](TEST_STATUS.md) for the exact verification run.

### Step 1: App Builder UI for existing capability (2026-09-09)

No backend changes. New frontend:
`/orgs/[orgId]/app-templates` (list/create), `/app-templates/[templateId]`
(a draft builder: add/rename/delete model, add/rename/delete field with a
data-type picker and a `Required` toggle that saves immediately, add/rename/
delete relationship with a deletion-policy select, publish version),
`/app-template-versions/[versionId]` (read-only definition snapshot), an
"Install app" flow added to the project page (template → version →
label, cascading selects), and a "Provision runtime" action plus live
status polling added to the instance page (wired to Phase 2's existing
`runtime-plan`/`runtime` endpoints). Every add/edit/delete in the builder
PATCHes the *entire* `draft` JSON and replaces local state from the
server's response — never a locally-invented id — specifically so
already-assigned ids survive across edits (`publish_template`'s own
"retain definition lineage" comment); relationship source/target pickers
only ever offer already-saved models (ones with a server-assigned id), so
a relationship can never reference an element that doesn't durably exist
yet.

`next build` (type-checks against the real API response shapes), ESLint,
and the existing 10-test Vitest suite all pass clean. **Live-verified
end-to-end in a real browser** against a rebuilt dev stack (frontend
rebuilt and restarted; backend untouched since this step made no backend
changes): created a template from scratch ("Bug Tracker"), added two
models and a required text field, added a relationship between them,
published a version, installed it into a project through the new "Install
app" modal, provisioned its runtime (watched the async status go
pending → ready via the page's own polling, backed by the real Celery
worker), and opened its generated record screen — confirming Phase 3's
builder and Phase 2's runtime/record screens are actually one connected
system, not two features that happen to share a database. This is the
first time the full template → publish → install → provision → records
journey has been driven through the UI rather than the API directly.

See [TEST_STATUS.md](TEST_STATUS.md) for the exact verification run.

**Remaining in step 1's spirit, deferred to later steps by design, not
forgotten:** no editing of an *installed* instance's models/fields once
provisioned (step 3's "safe populated-schema changes" — today the only
way to change a provisioned app's shape is a new template version and a
fresh install, which is the existing, correct behavior, not a gap this
step was scoped to close); no per-app permission assignment UI (step 4,
which needs its own design decision first). Reordering/defaults, listed
here originally as step 2 scope, are done — see step 2's own account
above.
