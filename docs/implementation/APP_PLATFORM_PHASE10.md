# App Platform Phase 10 -- Developer extension platform

Status: **COMPLETE**, 2026-09-16/17 on `feature/app-platform`, right
after Phase 9's completion (`543b9df`). Per [the roadmap]
(APP_PLATFORM_ROADMAP.md): "Documented APIs, environment-bound service
accounts, reliable webhooks, custom clients/workers and controlled
extension boundaries." **This is the tenth and final phase of App
Platform's own ten-phase plan** (Phases 0-9 were already complete; see
that roadmap for the full sequence).

## Two real gaps found by reading the existing contract, not guessed at

Before writing any code, this phase's own starting point was
`docs/EXTERNAL_APP_API_CONTRACT.md`'s existing "What this contract
deliberately does NOT include" section -- the authoritative, already-
audited list of exactly what App Platform's bearer-token surface was
missing. Two lines mattered:

1. *"Webhooks or any push/event-notification mechanism out of App
   Platform toward an external application"* -- listed as **NOT YET
   IMPLEMENTED**, verbatim.
2. Environment-scoping was not listed there at all, in either direction
   -- reading `databases/views.py`/`storage/views.py`'s own
   `_environment_scope_denied` helper (added for those two apps under
   the Phase 22 mandate) confirmed `app_platform`'s record/attachment
   endpoints -- the one bearer-token-reachable surface in this codebase
   with genuine record-CRUD power -- had **no equivalent check
   anywhere**. An Environment-scoped credential meant to be confined to
   a Development environment could reach *any* instance's records
   regardless of which Environment (if any) its runtime database was
   actually bound to. Not a documented, deliberate scope cut like most
   of that section's other bullets -- a real, silent gap.

Both are now closed. Both reuse existing infrastructure end to end --
`environments.EnvironmentWebhook`'s encrypted signing secret and
`environments.services.check_environment_scope` (Phase 22) -- rather
than inventing a second mechanism for either.

## 1. Environment-bound service accounts

`app_platform/access.py::environment_scope_denied(request, model)` --
one new function, called from all six record/attachment view methods
(`record_views.py`, `attachment_views.py`) right after each resolves its
`model`, mirroring `databases/views.py::_environment_scope_denied`
exactly (same `check_environment_scope` call, same "only ever restricts
credential-authenticated requests" behavior, same plain `403` with no
body). The one structural difference from `databases`/`storage`: those
two already have the target `TenantDatabase`/`Bucket` in hand from their
own `get_member_table`/`get_member_bucket` call; app_platform's record
views only have a `ModelDefinition`, so this function resolves the
instance's `RuntimeProvision` itself (one extra query, redundant with
`records.py`'s own `_receipt()` moments later -- an acceptable, narrow
duplication rather than threading the full `request` object down into
the service layer, which every one of `records.py`'s existing call
sites would have needed to change).

An unprovisioned instance, or one whose runtime database was never bound
to any Environment, is left undenied by this check specifically --
`records.py`'s own 404/403 already explains the former, and an unbound
database is categorically unreachable through *any* Environment-scoped
credential regardless (`check_environment_scope`'s own "explicit binding
required, not merely no conflicting binding" rule -- proven live below).

## 2. Reliable webhooks

`app_platform/webhooks.py` (dispatch) + a new task in `app_platform/
tasks.py` (`deliver_app_platform_webhook`) + a new model
(`WebhookDelivery`). Deliberately reuses `environments.EnvironmentWebhook`
as the *entire* subscription/signing-secret store -- no new
configuration concept, no new encrypted-secret model of App Platform's
own. `records.py`'s `create_record`/`update_record`/`delete_record` and
`workflows.py`'s `apply_transition` each call `webhooks.dispatch_event`
inside `transaction.on_commit` (the exact precedent `workflows.py`'s own
`_enqueue_delivery` already established for `notify_url` delivery), so a
change that later rolls back never dispatches an event that didn't
really happen.

An event only ever reaches a webhook when the *emitting instance's own
runtime database* is bound to that webhook's Environment -- the same
binding `check_environment_scope` uses for inbound access control, read
in the opposite direction for outbound dispatch. An instance with no
Environment binding has no possible subscribers, by construction.

Four event types: `app_instance.record.create`/`.update`/`.delete` and
`app_instance.workflow.transition` (fired independently of that
transition's own, older, unsigned `notify_url` field -- both can fire
for the same transition, neither gates the other). Delivery is `POST`
with `Content-Type: application/json`, an `X-IntraForge-Event` header,
and `X-IntraForge-Signature: sha256=<hex>` -- an HMAC-SHA256 of the exact
raw body bytes, keyed by the webhook's own decrypted signing secret
(`environments.crypto.decrypt_secret`). Same acks_late/at-least-once (never claimed
at-most-once)/host-re-checked-immediately-before-every-attempt discipline as
`deliver_workflow_notification` (Phase 5) and every other Celery task in
this codebase that does a real outbound HTTP call.

**Payloads are deliberately thin** -- ids and the event type only, never
a record's actual field values. This is a considered choice, not a
shortcut: a webhook receiver should treat a push as "something changed,
go fetch details via the real API" rather than trust a payload as a data
feed, and it avoids a real risk this codebase is otherwise careful about
-- a slow, broken, or malicious receiver logging or mishandling a
payload that happens to carry business data.

## "Documented APIs" / "custom clients/workers" / "controlled extension
boundaries"

Not new code -- confirmed satisfied by what already exists, extended
where this phase's own two additions needed new documentation:

- **Documented APIs**: `docs/EXTERNAL_APP_API_CONTRACT.md` was already
  the authoritative, implementation-verified contract (Post-Phase-3
  Integration Enablement). This phase added its own "Environment
  scoping" and "Webhooks" sections (the latter including a runnable
  Python signature-verification snippet -- the concrete artifact a
  "custom client" integrator actually needs) and removed the now-stale
  "webhooks NOT YET IMPLEMENTED" bullet, replacing it with the one
  narrower thing that genuinely remains unbuilt (a delivery-history/
  redelivery API).
- **Custom clients/workers**: a webhook receiver *is* the "custom
  worker" this line means -- an external process reacting to push
  events rather than polling. The Webhooks section's signature-
  verification recipe is its complete integration contract. Bearer-token
  API clients were already documented before this phase; nothing about
  that surface changed except the new Environment-scope restriction.
- **Controlled extension boundaries**: `FoundationView.
  service_account_methods` (unchanged in shape by this phase) remains
  the single, explicit allowlist deciding which HTTP methods a bearer
  token can reach on which view. Schema mutation, template
  administration, and instance install/archive/provisioning are still
  entirely human-session-only -- this phase never widened that boundary,
  only added a *narrowing* condition (Environment scope) on top of the
  surface that was already bearer-reachable.

## Test evidence

14 new tests, `app_platform/tests/test_webhooks.py`, `TransactionTestCase`
against real provisioned instances and real HTTP requests (bearer-token
and session both), never calling service functions directly for the
behavior under test:

- **`DispatchTests`**: a subscribed event type creates a delivery; an
  unsubscribed one doesn't; an empty `event_types` list subscribes to
  every event; a disabled webhook receives nothing; an instance with no
  Environment binding dispatches nothing; a webhook on a *different*
  Environment than the emitting instance's own binding receives nothing;
  a genuinely HMAC-signed delivery reaches a real local HTTP server with
  the signature independently recomputed and compared (not merely
  asserted non-empty), and the payload confirmed thin (no field values
  present); disabling a webhook between dispatch and the (Celery-eager,
  synchronous-in-test) delivery attempt is caught and not sent.
- **`WorkflowWebhookTests`**: a transition with *no* `notify_url` at all
  still dispatches a webhook event when one is subscribed -- proving the
  two delivery mechanisms are genuinely independent, not one gating the
  other.
- **`EnvironmentScopeTests`**: mirrors `environments/tests/
  test_environments.py::EnvironmentCredentialAndIsolationTests`'s own
  structure and scenario, applied to app_platform's record endpoint
  specifically -- a Development-scoped credential reaches a Development-
  bound instance and is denied a Production-bound one (both directions),
  an unscoped credential reaches both (backward compatibility, unchanged
  for every credential issued before this phase), and an Environment-
  scoped credential is denied an instance with *no* Environment binding
  at all despite holding a real `database.read` `ResourceGrant` for it
  -- proving the Environment-scope check itself is what blocks access,
  independent of and prior to the permission system, the same proof
  structure `test_development_credential_cannot_access_production_
  database` already established for `databases`.

Regression scope: `app_platform` (374 tests) plus `environments` +
`applications` + `databases` + `storage` together (558 tests) pass
clean, with the one pre-existing, already-documented flaky concurrency
test (`test_many_to_many.py::
test_concurrent_addition_of_the_same_new_pair_the_database_constraint_is_the_real_gate`,
timing-sensitive under full-suite load, confirmed passing reliably in
isolation) -- not a regression from this phase's diff.

## Live verification against the running Docker stack

Beyond the automated suite -- and beyond the ephemeral, Celery-eager
test database -- a real organization, application, Environment, and
provisioned instance were created directly against the persistent dev
control-plane database, with a real `EnvironmentWebhook` pointed at a
real Python `http.server` running on the host machine (reachable from
inside the Docker network via `host.docker.internal`, confirmed
resolvable and not blocked by the SSRF guard, which permits private
addresses by default). A record created through the real HTTP API (the
actual Caddy proxy, not the Django test client) was picked up by the
**real, separate `worker` Celery container** -- not eager/synchronous
test execution -- which computed and sent a genuinely correct HMAC-
SHA256 signature: independently recomputed against the exact bytes
received and the signing secret captured at webhook-creation time, and
confirmed to match exactly. A second live check issued a real
Environment-scoped `ApplicationCredential`, confirmed it could read the
bound instance's records (`200`) and was denied a second, deliberately
unbound instance's records (`403`) despite holding a real `database.read`
grant on it -- the exact scenario `EnvironmentScopeTests` proves in the
automated suite, reproduced against the live stack.

## Known limits (honest, not silently absorbed)

- **No webhook delivery-history/redelivery API.** `WebhookDelivery` rows
  exist and are queryable internally (via the Django ORM/admin, not a
  documented endpoint) for retry bookkeeping (delivery is at-least-once), but there is
  no `GET`/redeliver endpoint for an integrator to inspect or replay a
  past delivery. Tracked in `EXTERNAL_APP_API_CONTRACT.md`'s own "does
  NOT include" section rather than silently absorbed.
- **Environment scoping does not extend to the runtime-provisioning or
  schema-discovery endpoints** (`app-instances/{id}/runtime/`,
  `.../models/`, etc.) -- only record/attachment data, matching exactly
  what `databases`/`storage` themselves scope (row/file data, not schema
  metadata). Schema discovery over a bearer token was already a narrow,
  read-only surface before this phase; widening this phase's own scope
  to cover it was judged disproportionate to the actual risk (schema
  shape, not business data).
- **No per-webhook delivery-rate limiting or circuit-breaking** beyond
  the fixed 5-attempt/exponential-backoff retry every Celery task in
  this codebase already uses -- a chronically failing receiver keeps
  being dispatched to on every new matching event, not temporarily
  suspended. The same characteristic `deliver_workflow_notification`
  (Phase 5) already has, not a new gap introduced here.
