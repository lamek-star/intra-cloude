# App Platform Phase 5 — Workflow engine

Status: **COMPLETE**, 2026-09-16 on `feature/app-platform`, right after
Phase 4's completion (`393a4eb`). Per [the roadmap](APP_PLATFORM_ROADMAP.md):
"Declarative states, transitions, conditions, approvals, actions,
notifications and audit; concurrent/replayed transitions cannot duplicate
effects."

## What this phase proves

That the generic App Platform can express a controlled-vocabulary
lifecycle (declared states, declared legal transitions between them, with
conditions/actions/approval/notification attached to each transition) as a
pure control-plane capability layered on top of an existing scalar `text`
field — no enum type, no new physical schema, no new tenant DDL. A
workflow's "state" is just the current value of one of the model's own
existing fields; `WorkflowDefinition`/`WorkflowState`/`WorkflowTransition`
are declarative `Definition` rows exactly like `ConstraintDefinition`, and
are **deliberately never read by `runtime_plan.py`/`runtime_build.py`** —
the same way `Definition.position` is already excluded from the
provisioning fingerprint. Installing, editing, or adding a workflow never
touches the tenant schema and has no interaction with `lock_active` or the
live schema-evolution machinery Phase 3 built.

## The hard requirement: concurrent/replayed transitions cannot duplicate effects

Two independent problems hide inside that one roadmap sentence, and both
are solved by reusing patterns this codebase had already proven correct
elsewhere, not by inventing new ones:

1. **Replay** (the exact same "apply transition" request retried after a
   timeout/crash) is solved by `WorkflowTransitionAttempt` — a durable
   attempt row keyed by `(record_id, idempotency_key)`
   (`app_workflow_attempt_idempotency_unique`, a partial unique constraint
   active only when `idempotency_key` is not null), with `completed_at` as
   the durable "already fully processed" marker. This is the identical
   shape `exports.RestoreJob` and `provisioning.RuntimeProvision` already
   use: `get_or_create` under `select_for_update`, compare the new
   request's fingerprint against the stored one (same idempotency key,
   different request body → `409`, not silent reuse), and short-circuit to
   the existing result if `completed_at` is already set.
2. **Concurrency** (two genuinely different transitions racing on the same
   record — e.g. "approve" and "reject" both fired from "pending") is
   solved by a new, small, reusable primitive: `databases/rows.py::
   update_row_if(table, row_id, *, expected, data)` — a compare-and-swap
   `UPDATE ... SET ... WHERE id = %s AND <expected columns still match>
   RETURNING ...`. Zero rows affected is split into "doesn't exist"
   (`RowNotFound`, a 404) vs. "exists but changed" (`RowConflict`, a 409)
   by a follow-up `get_row`, mirroring the not-found-vs-stale split
   `provisioning.reserve` already makes for a stale fingerprint. This
   realizes the project's own stated discipline (`records.py`'s docstring:
   "let it race, let a real Postgres operation be the gate") rather than
   an application-level lock.

Together: the idempotency-key row answers "was this exact request already
fully processed" (replay), and the compare-and-swap UPDATE answers "does
the record still actually match what this request assumed" (concurrency).
Both are verified against real PostgreSQL with real `ThreadPoolExecutor`
concurrency, not simulated.

## Data model (all in `app_platform/models.py`, migration `0014_workflow_engine.py`)

Declarative (`Definition`-based, control-plane only):

- **`WorkflowDefinition`**: `model`, `state_field` (must be a `text`
  `FieldDefinition` on the same model — validated at definition time, not
  DB-enforced).
- **`WorkflowState`**: belongs to a `WorkflowDefinition`. No separate
  "value" column — a state's own `key` (already a validated,
  storage-safe identifier) *is* the literal text value written to the
  record's state field.
- **`WorkflowTransition`**: `from_state` (nullable — null means "valid
  from any current state"), `to_state`, `conditions` (JSON list of
  `{field_id, operator, value}`, operators `eq`/`ne`/`is_null`/
  `is_not_null`), `field_actions` (JSON list of `{field_id, value}`,
  validated against each field's real data type at definition time),
  `requires_approval` (bool), `notify_url` (optional, SSRF-checked at
  definition time via `databases.connectors.assert_host_is_safe`).

Operational (receipt-row shape, not physical/declarative metadata):

- **`WorkflowTransitionAttempt`**: `transition`, `record_id`,
  `idempotency_key` (nullable), `request_fingerprint`, `state_before`/
  `state_after`, `completed_at`, `last_error`, `created_by`.
- **`WorkflowNotificationDelivery`**: one row per attempt that has a
  `notify_url`; `delivered_at` is the "send at most once" gate for the
  Celery task, denormalizing the URL at attempt time so a later edit to
  the transition never rewrites delivery history.

## Scope decisions (stated up front, not silently assumed)

- **Approvals are a capability gate, not a stateful approval-inbox.** A
  transition marked `requires_approval=True` additionally requires the new
  `app_instance.workflow.approve` capability (on top of the `database.write`
  every record write already needs) — reusing `permissions.services.
  has_permission`/`ResourceGrant` exactly as-is. A full pending/approve/
  reject human-approval-inbox subsystem is meaningfully larger scope and is
  **not** built here.
- **Conditions are narrow by design**: simple, ANDed `{field_id, operator,
  value}` checks against the model's own scalar fields — not a general
  expression language.
- **Actions are literal field writes only**, applied in the same
  compare-and-swap UPDATE as the state change — no calculated/derived
  values. This is also *why* replay-safety is simple: writing a fixed
  literal twice is naturally idempotent, unlike e.g. incrementing a
  counter.
- **Notifications are real, working delivery** (a Celery task doing an
  actual HTTP POST with a JSON payload), not a stub — but **not signed**:
  there is no per-target secret-storage model in this platform yet, and
  this phase does not fabricate one. Documented as a known limit below
  rather than overclaiming a security property.
- **Workflow definitions are additive-only once installed** — label/
  position can change and new states/transitions can always be added;
  there is no delete/structural-edit endpoint for an existing state or
  transition (avoids dangling-reference bugs from a state a record
  currently holds, or a transition an in-flight attempt references).

## Service layer (`app_platform/workflows.py`)

`apply_transition(actor, transition, record_id, *, idempotency_key=None)`:
resolves the record's table via `records.resolve` (so it gets the same
`database.write` capability check, cross-org isolation, and Environment
scoping every other record write already gets), checks
`app_instance.workflow.approve` when `requires_approval`, reserves a
`WorkflowTransitionAttempt` (idempotency short-circuit), evaluates
`conditions` against the record's current values, then applies the state
write plus all `field_actions` in one `update_row_if` call keyed on the
expected `from_state`. A `RowConflict` becomes a `409 TransitionConflict`;
a missing record is a `404`. On success, the attempt is marked complete,
an `AuditEvent` is recorded, and — if `notify_url` is set — a
`WorkflowNotificationDelivery` row is created and its Celery delivery is
enqueued via `transaction.on_commit` (so a task never fires for a
transaction that later rolls back).

`deliver_workflow_notification` (`app_platform/tasks.py`): `acks_late=True,
reject_on_worker_lost=True` (the same fix already applied to `imports`/
`exports`/`run_export_task`'s Celery tasks after Phase 2's audit). Checks
`delivered_at` first (replay-safe), re-validates `assert_host_is_safe`
immediately before dialing (defends against DNS rebinding between
definition time and delivery time), and marks `last_error` on failure
without ever raising past `MaxRetriesExceededError` into a stuck task.

## API

`WorkflowList`/`WorkflowDetail`, `StateList`/`StateDetail`,
`TransitionList`/`TransitionDetail` follow the existing `FoundationView`/
`DefinitionDetail` conventions exactly (human-session-only authoring).
`ApplyTransitionView` (`POST /app-models/{model_id}/records/{record_id}/
transitions/{transition_id}/apply/`) is open to service-account bearer
tokens too, since applying a transition is fundamentally a record write
and Phase 7 already lets a properly-scoped token do that; it accepts an
optional `Idempotency-Key` header and returns `409` on a real conflict,
`403` when approval is required and missing, `404` when the transition
doesn't belong to the model in the URL (ID-substitution safe).

## Frontend

- **Template draft editor** (`app-templates/[templateId]`): a new
  "Workflows" section per model, following the same whole-document-PATCH
  `saveDraft` idiom already used for models/fields/relationships/
  constraints — add workflow (pick a `text` state field) → add states →
  add transitions (from/to state, requires-approval, notify URL). No
  conditions/field-actions authoring UI in this pass (deliberate scope
  cut — those remain API-only for now).
- **Live instance editor** (`app-models/[modelId]`): dedicated `POST`
  add-forms for workflow/state/transition, mirroring `AddConstraintForm`.
- **Record detail page**: a new "Workflow" section showing a state
  `Badge` and buttons for every transition valid from the record's current
  state. A `requires_approval` button still renders (marked with `*` and a
  tooltip) even for a viewer who may lack the capability — the server is
  the real enforcement point, matching this project's existing "reactive,
  not proactive hiding" convention for permissions elsewhere in the UI.
  Applying a transition refreshes both the record and the History section.

## Test evidence

- `app_platform/tests/test_workflows.py` (15 tests): draft validation
  (state-field type/ownership, cross-workflow state/transition references,
  invalid action literals, unsafe `notify_url` rejected at definition
  time) and install-time creation.
- `app_platform/tests/test_workflow_transitions.py` (12 tests, real
  provisioned runtime, real record via the API): a transition writes state
  + field actions atomically; a mismatched `from_state` is a clean
  conflict, not a corrupted write; `requires_approval` denies without the
  capability and succeeds once granted; **the concurrency test that
  matters most** — two different, mutually-exclusive transitions fired
  concurrently at the same starting state via a real `ThreadPoolExecutor`:
  exactly one wins, the other gets a clean conflict, the record ends in a
  valid, non-corrupted state; a replayed idempotency-key request returns
  the original result without re-running actions or re-sending a
  notification (delivery row count stays at 1); notification delivery
  verified against a real local `http.server.HTTPServer`, not a mock.
- `app_platform/tests/test_workflow_api.py` (12 tests): URL routing,
  `Idempotency-Key` header round-trip, HTTP status codes (`409`/`403`/
  `404`), cross-org isolation (IDOR/BOLA, per CLAUDE.md's rule for every
  new resource type), and the service-account boundary (authoring
  blocked, applying allowed once properly scoped).
- `databases/tests/test_row_conditional_update.py` (6 tests): the new
  `update_row_if` primitive in isolation, including a real concurrent
  mutually-exclusive-update race proving exactly one writer wins.
- Full backend suite: 363 `app_platform` + `databases` tests pass together
  (0 failures), against real PostgreSQL (`TransactionTestCase`,
  `databases = {"default", "tenant"}`), not mocks.

## Live verification

Beyond the unit-test suite, run against the real running Docker stack (not
just asserted): a new template ("Phase 5 Workflow Test") was authored
through the actual App Builder UI — a `Ticket` model with a `Status` text
field, a `Lifecycle` workflow with `Draft`/`Open`/`Closed` states, a
`Submit` transition (`Draft → Open`) and a `Close` transition (`Open →
Closed`, `requires_approval`) — published, installed into a real project,
and provisioned. The live-instance editor's Workflows section correctly
rendered the installed workflow/states/transitions. A record was created
through the real record API, and both transitions were applied by
clicking the record-detail page's new "Workflow" section buttons: the
state badge updated from Draft → Open → Closed, the "Close *" button's
approval marker rendered correctly, and the History section showed real
`app_instance.workflow.transition.apply` audit events with `success`
after each click — not just a test-suite assertion.

## Known limits (honest, not silently absorbed)

- No stateful human approval-inbox — `requires_approval` is a capability
  gate, checked at apply time, not a separate pending/approve/reject
  request object.
- No delete or structural edit of an installed state or transition —
  only label/position changes and additive new states/transitions.
- Conditions and field actions have no expression language — a fixed,
  narrow condition/action shape only, and are not yet authorable through
  either frontend editor (API/JSON-draft only).
- `notify_url` deliveries are **not signed** — there is no per-target
  secret-storage model in this platform; a receiver cannot cryptographically
  verify a delivery came from this instance. Adding that requires a real
  secret-management design (likely reusing `environments.EnvironmentSecret`'s
  Fernet-encryption pattern), tracked as an open item, not fabricated here.
