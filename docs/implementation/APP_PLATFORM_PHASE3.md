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

1. **App Builder UI for existing capability — current step.** Template
   list/create/edit, a draft model/field/relationship builder (label, key,
   data type, required — the fields `DefinitionInput` already validates),
   publish, version history, install into a project, and wiring the
   installed instance through to Phase 2's already-built provisioning and
   record screens. No backend changes; this step is exclusively making
   already-tested backend capability reachable without the API directly.
2. **Defaults and ordering.** Extend `FieldDefinition`/the definition
   format with a validated default value per data type and an explicit
   display-order field for models/fields/relationships; extend the builder
   UI and the generated record screens (Phase 2) to use them.
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

Step 1 landed 2026-09-09, no backend changes. New frontend:
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
forgotten:** no drag-to-reorder (step 2's "ordering"); no default values
(step 2); no editing of an *installed* instance's models/fields once
provisioned (step 3's "safe populated-schema changes" — today the only
way to change a provisioned app's shape is a new template version and a
fresh install, which is the existing, correct behavior, not a gap this
step was scoped to close); no per-app permission assignment UI (step 4,
which needs its own design decision first).
