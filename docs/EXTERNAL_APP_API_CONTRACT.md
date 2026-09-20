# External App API Contract — App Platform

Baseline: commit `886e75f` (App Platform Phase 3, complete) plus
Post-Phase-3 Integration Enablement (external bearer-token access, field
indexing/uniqueness). This document describes exactly what an externally
developed frontend/reference application can call against IntraForge's
App Platform today, and marks plainly what does not exist yet. Every
capability listed is backed by reading the actual implementation and
tests — nothing here is inferred from another document, and nothing here
is a proposed/future endpoint unless explicitly marked **NOT YET
IMPLEMENTED**.

Companion document: `docs/SPARE_PARTS_INTEGRATION_READINESS.md` (the
broader capability review this contract was extracted from).

All paths are relative to `/api/v1/` unless stated otherwise.

---

## Authentication

### Browser session authentication

`POST auth/login/` sets a Django session cookie; `GET auth/me/` returns
the current user; `POST auth/logout/`. CSRF is enforced on unsafe methods
for session-authenticated requests (`GET auth/csrf/` issues the token).
This is what IntraForge's own Next.js frontend uses. It is same-origin-
oriented (cookie + CSRF token) and is **not** the recommended mechanism
for a separately hosted frontend.

### Bearer-token application credentials — the recommended mechanism

`applications` app (Phase 7), now reachable from App Platform (Post-
Phase-3 Integration Enablement, Part 1):

- `POST organizations/{org_id}/applications/` creates an `Application`
  (backed by a real `User` row via `ServiceAccount.identity_user`).
- `POST applications/{application_id}/credentials/` issues a credential;
  the plaintext secret (`Authorization: Bearer pdc_sk_<credential-id-hex>.<secret>`)
  is shown exactly once, never stored or retrievable again.
- `POST applications/{application_id}/resource-grants/` scopes the
  application's identity to specific resources via a `ResourceGrant` —
  `{"permission_code": "...", "resource_type": "...", "resource_id": "..."}`.
  No new endpoint was needed for this: it already accepts any permission
  code in the catalog and any `resource_type` string, so it already
  worked for `app_instance`/`databases.tenant_database` grants before
  this integration work — the gap was purely that App Platform's own
  views rejected the resulting authenticated request regardless.
- Requests authenticate with `Authorization: Bearer <token>`.

**What a bearer token can reach today** — `FoundationView.
service_account_methods` opts specific HTTP methods on specific views in;
everything else stays exactly as human-session-only as before this work:

| Endpoint | Bearer-reachable methods |
|---|---|
| `app-instances/{id}/` | `GET` only (not `PATCH` — rename/archive stays administrative) |
| `app-instances/{id}/models/`, `.../relationships/` | `GET` only (not `POST` — adding a model/relationship is schema mutation) |
| `app-models/{id}/`, `app-fields/{id}/`, `app-relationships/{id}/`, `app-constraints/{id}/` | `GET` only (not `PATCH`) |
| `app-models/{id}/fields/`, `.../constraints/` | `GET` only (not `POST`) |
| `app-models/{model_id}/records/` | `GET`, `POST` |
| `app-models/{model_id}/records/{record_id}/` | `GET`, `PATCH`, `DELETE` |
| `.../records/{record_id}/attachments/` | `GET`, `POST` |
| `.../attachments/{attachment_id}/` | `DELETE` |
| `.../attachments/{attachment_id}/download/` | `GET` |
| `app-instances/{id}/runtime/` | `GET` only (not `POST` — provisioning is a one-time human action) |

**Not bearer-reachable at all, regardless of any grant** (still fully
human-session-only): template administration (`app-templates/*`,
`app-template-versions/*`), installing a new instance
(`POST projects/{id}/app-instances/`), every schema-*mutation* endpoint
(adding a model/field/relationship/constraint, editing a definition),
runtime provisioning, `app-fields/{id}/unique/` and `.../indexed/` (see
Field indexing/uniqueness below). This is a deliberate first-slice boundary,
not a technical limitation — see the readiness review's Decision section.

Reachability alone grants nothing: every action, once reachable, still
goes through the identical deny-by-default `has_permission()`/
`ResourceGrant` check a human session uses. A bearer token with no grant
at all gets a `403` on every reachable endpoint too, exactly like a human
member with no role.

### Environment scoping (Phase 10)

`POST environments/{environment_id}/credentials/` issues a credential
bound to that one `Environment` (`environments` app) — distinct from
`POST applications/{application_id}/credentials/` above, which always
issues an unscoped one. When a credential is Environment-scoped:
every `app-models/{model_id}/records/*` and `.../attachments/*` endpoint
above now checks that the *target instance's own runtime database* is
bound to that *exact same* Environment — `GET
app-instances/{id}/runtime/` returns the `database_id` to check this
against, and an admin binds a database to an Environment via `PATCH
environments/{environment_id}/database/`. A credential with no
Environment at all is unrestricted by this check (existing behavior,
unchanged); a credential that *is* Environment-scoped gets a plain `403`
(no body) against an instance whose database is bound to a *different*
Environment, or to *no* Environment at all — explicit binding is
required, "no conflicting binding" is not enough to allow through. This
mirrors `databases`/`storage`'s own row/file endpoints exactly (same
`environments.services.check_environment_scope` call); before this
phase, App Platform's record/attachment endpoints were the one bearer-
token-reachable surface in this codebase with no such check at all.

### CORS

`CORS_ALLOWED_ORIGINS` is an explicit allowlist (deny-by-default),
`CORS_ALLOW_CREDENTIALS=True`. A separately hosted frontend on a
different origin is supported today if its origin is added to the
allowlist. Bearer-token requests are not cookie-carried, so they never
depend on or interact with CSRF protection at all — CSRF only applies to
the session-cookie path above.

---

## App discovery / AppInstance identity

All IDs below are stable UUIDs assigned at creation; none of them are
derived from or reveal physical PostgreSQL table/column names.

| Capability | Endpoint | Notes |
|---|---|---|
| List an org's app templates | `GET organizations/{org_id}/app-templates/` | Paginated |
| Inspect a template | `GET app-templates/{template_id}/` | Includes the current `draft` definition |
| List a template's published versions | `GET app-templates/{template_id}/versions/` | Immutable once published |
| Inspect a version | `GET app-template-versions/{version_id}/` | Frozen `definition` snapshot |
| List a project's installed instances | `GET projects/{project_id}/app-instances/` | Paginated |
| Inspect an instance | `GET app-instances/{instance_id}/` | `{id, organization, project, source_version, label, archived, created_at}` |
| Check/trigger runtime provisioning | `GET`/`POST app-instances/{instance_id}/runtime/` | `POST` is async (Celery); poll `GET` for `status: pending\|ready\|failed` |

## Schema discovery

| Capability | Endpoint | Response shape |
|---|---|---|
| List a model's fields | `GET app-models/{model_id}/fields/` | Each: `{id, model, key, label, data_type, required, default_value, unique, indexed, position, source_definition_id}` |
| List an instance's models | `GET app-instances/{instance_id}/models/` | Each: `{id, instance, key, label, position, source_definition_id}` |
| List an instance's relationships | `GET app-instances/{instance_id}/relationships/` | Each: `{id, instance, key, label, position, source_definition_id, source_model, target_model, kind, deletion_policy}` |
| Inspect one model/field/relationship | `GET app-models/{id}/`, `GET app-fields/{id}/`, `GET app-relationships/{id}/` | Same shapes as above |
| List a model's composite unique constraints | `GET app-models/{model_id}/constraints/` | Each: `{id, model, key, label, position, source_definition_id, field_ids, relationship_ids}` |
| Inspect one constraint | `GET app-constraints/{id}/` | Same shape as above |

`data_type` is one of exactly `text`, `integer`, `decimal`, `boolean`,
`date`, `datetime`. `kind` is `many_to_one` or `many_to_many` (native
many-to-many support — see the Records section below for the payload
shape this changes). `deletion_policy` is `restrict` or `set_null` (no
`cascade`) for a `many_to_one` relationship; for `many_to_many` it is
always `restrict` and is not meaningful — a join table's own two foreign
keys are always physically `ON DELETE CASCADE` regardless of what this
field says (see Records below). `unique`/`indexed` (added Post-
Phase-3 Integration Enablement) are independent booleans: `unique` means
a real Postgres `UNIQUE` constraint backs this field's column (which is
also a real B-tree index); `indexed` means a plain, non-unique B-tree
index backs it. A `unique` field is always effectively indexed too;
`indexed` is only meaningful — and only ever actually applied — when
`unique` is `False`. Setting either at field-creation time
(`POST app-models/{id}/fields/`, human-session-only) works whether or not
the instance is provisioned yet. Retrofitting either onto an *existing*
field is two dedicated, human-session-only actions:
`POST app-fields/{field_id}/unique/` and
`POST app-fields/{field_id}/indexed/` — safe against an already-
provisioned, populated instance (rejects cleanly with `400` if existing
values would violate the new constraint; leaves all data untouched
either way), and idempotent (calling either twice is a no-op the second
time).

`field_ids`/`relationship_ids` (the latter added when general composite
uniqueness was extended to cover relationships, not just scalar fields)
together are the set of >=2 stable AppField/AppRelationship ids this
model-level `UNIQUE` constraint covers, in their current display order —
never a physical constraint/index name; the underlying
`databases.services.add_field_set_unique_constraint` primitive names the
real Postgres object internally, and a client is never meant to need or
discover that name. A relationship member must be a `many_to_one`
relationship whose own FK column lives on this same model (i.e. its
`source_model`) — a `many_to_many` relationship has no column on either
side (it's a join table) and can never participate. A constraint's
membership is immutable after creation (no endpoint changes it); only
`label`/`position` can be patched via `PATCH app-constraints/{id}/`
(human-session-only), and that never touches the physical constraint —
a display-label rename or a participating member's position/order
changing is guaranteed not to recreate it. Declaring a new constraint
(`POST app-models/{model_id}/constraints/`, human-session-only, needs
`field_ids`/`relationship_ids` combined to total >=2 with no repeats,
each belonging to that same model) works whether or not the instance is
provisioned yet; against an
already-provisioned, possibly populated instance it runs the same real
DDL discipline as field uniqueness above — rejects cleanly with `400`
if existing rows would violate it (data is left completely untouched
either way), and is idempotent under retry. NULL semantics follow the
same, already-documented single-field convention: if any participating
member is nullable — every relationship FK column always is, and so is
any `required=False` field — two records can share NULL there (with
identical values elsewhere) without violating the constraint —
PostgreSQL's `UNIQUE` never treats NULL as equal to another NULL.

List endpoints use standard DRF `LimitOffsetPagination`:
`{count, next, previous, results}`.

## Records

| Capability | Endpoint |
|---|---|
| List records | `GET app-models/{model_id}/records/` |
| Create a record | `POST app-models/{model_id}/records/` |
| Read a record | `GET app-models/{model_id}/records/{record_id}/` |
| Update a record | `PATCH app-models/{model_id}/records/{record_id}/` |
| Delete a record | `DELETE app-models/{model_id}/records/{record_id}/` |

**Every record payload is keyed by field/relationship definition UUID,
both when sending and receiving** — never a physical column name. A
`many_to_one` relationship's value is `str | null` (the related record's
own UUID, or `null` for no association). A `many_to_many` relationship's
value is always `list[str]` — the related records' UUIDs — **in both
directions**, regardless of which model the request is for; the client
tells the two shapes apart via the relationship's already-exposed `kind`.

### Date and time values

Stricter than ISO 8601, and the same for every writer (the browser, an integration, the CSV importer):

* `date`: `YYYY-MM-DD`.
* `datetime`: `YYYY-MM-DDTHH:MM:SS` (a space instead of `T` is also accepted) -- **naive UTC, whole seconds**. A trailing
  `Z`, a UTC offset (`+04:00`) and fractional seconds (`...:00.646`) are **refused with `400`** and nothing is written; a
  JavaScript `Date.toISOString()` is therefore *not* accepted. Responses return the same naive-UTC form; a client that
  displays it should treat it as UTC. (Found by the browser journey, pinned by
  `app_platform/tests/test_transactions.py::MovementTimestampContractTests`.)

List response shape (`AppRecordsPage`, note: this is *not* the same
envelope as the schema-discovery endpoints above):

```json
{"count": 0, "limit": 50, "offset": 0, "results": []}
```

### Many-to-many associations

A `many_to_many` relationship is **readable from both the source and
target model** but **writable only from the source side** — the same
relationship key on a target-side record is present in every response
but rejected (`400`) if included in a `POST`/`PATCH` body there. On a
write, `null` and `[]` both mean "no associations"; **omitting the key
entirely from a `PATCH` body means "leave associations unchanged"** —
the same partial-update semantics every other field already has, but
easy to get backwards for a list-valued field, so called out explicitly
here. Values are deduplicated server-side before being applied — sending
the same id twice in one request is never itself an error. Referencing a
record id that doesn't exist returns the same `400 {"detail":
"referenced record does not exist"}` a bad `many_to_one` value already
returns. A many-to-many relationship can never appear as a `?ordering=`
or filter query param — see Errors below.

Deleting a record removes its many-to-many associations on both sides
automatically (the underlying join table's foreign keys are `ON DELETE
CASCADE`) — no separate cleanup call is needed or possible.

### Filtering / sorting / search (all query params on the list endpoint)

- **`ids=<uuid>,<uuid>,...`**: return exactly those records (at most 100 per request; anything else is `400`). It is the
  ordinary list with an id filter -- same permission check, same tenant, same paging -- and lets a client name a page of
  rows in one request instead of one request per row. It cannot be combined with `id=`.

- **Filtering**: any query param whose key matches a field or
  many_to_one relationship definition UUID is applied as an
  **exact-match equality** filter; multiple filters are AND-combined. No
  other operator exists. A `many_to_many` relationship key is rejected
  with `400` if used as a filter — filtering/sorting by many-to-many
  membership is out of scope (a record's own many-to-many value is still
  fully readable/writable, just not queryable this way).
  This is the same code path regardless of whether the field is
  `unique`/`indexed` — no separate "search API" exists for indexed
  fields (Post-Phase-3 Integration Enablement deliberately added no new
  query-layer code for this). The difference is invisible at the API
  level and entirely a matter of what Postgres does underneath: an
  exact-match filter on a `unique`/`indexed` field is answered by a real
  index scan instead of a sequential scan, confirmed with a real
  `EXPLAIN`/`EXPLAIN ANALYZE` (see
  `app_platform/tests/test_field_indexing.py`'s
  `IndexBackedSearchEvidenceTests`, and the readiness review for a
  200,000-row disposable benchmark: ~0.03ms indexed vs. ~25ms
  sequential-scanned on the same table/row count). A field that is
  neither `unique` nor `indexed` still works as a filter — it's just an
  unindexed sequential scan, exactly as before this work.
- **Sorting**: `?ordering=<definition_id>` or `?ordering=-<definition_id>`
  — one column only, and never a `many_to_many` relationship (see above).
  Unspecified defaults to `id` order, not the definition's display
  `position`.
- **Search**: `?search=<term>` performs a case-insensitive substring
  match (`ILIKE '%term%'`) **OR-ed across every text/varchar column on
  the model automatically** — it cannot be targeted to a single field,
  and it is not index-backed (see the readiness review §6).
- **Pagination**: `?limit=&offset=`, default limit 50, hard cap 500.

### Errors

- `401`/`403` — no credential at all, an invalid/expired/revoked bearer
  token, or a valid identity lacking the required capability for this
  instance or its tenant database (empty body for the capability-denied
  case). A revoked or garbage token is indistinguishable from any other
  authentication failure in the response — no information about why a
  specific token doesn't work is exposed.
- `400 {"detail": "..."}` — a value-level problem: an invalid reference,
  or **a uniqueness conflict** — creating or updating a record with a
  value that collides with an existing one on a `unique` field returns
  `{"detail": "a record with this value already exists"}`, distinguished
  server-side from a foreign-key violation (`"referenced record does not
  exist"`) by inspecting the real Postgres exception class, not a string
  match. The message never names the conflicting value or the other
  record — enough for the caller to know their own request was rejected,
  nothing about anyone else's data. Retrofitting uniqueness
  (`POST app-fields/{id}/unique/`) onto a field with existing duplicate
  values returns the analogous `400` without touching any existing row.
  The same two messages cover many-to-many associations: a nonexistent
  target id is `"referenced record does not exist"`; a same-pair
  duplicate (including one created by two concurrent requests racing to
  add the exact same new association — the real database constraint is
  the actual gate, not an application-level check) is `"a record with
  this value already exists"`. Writing to a many-to-many relationship's
  read-only (target) side, or using one as a filter/sort key, returns a
  `400` with a message naming which of those it was.
- `404` — the id doesn't exist, or exists in a different organization
  (identical response either way — the API never reveals whether a
  foreign-org resource exists).
- Definition-mutation endpoints (creating a model/field/relationship)
  follow standard DRF serializer validation-error conventions.
- Uniqueness is enforced by the real Postgres `UNIQUE` constraint, not an
  application-level pre-check — two concurrent requests creating the same
  value on a `unique` field always resolve to exactly one `201` and one
  `400`, never two successes (proven with real concurrent threads, not
  just reasoned about — see `test_field_indexing.py`'s
  `test_concurrent_duplicate_record_creates_the_database_constraint_is_the_real_gate`).

## Attachments (files/images/documents)

| Capability | Endpoint |
|---|---|
| List/add an attachment on a record | `GET`/`POST app-models/{model_id}/records/{record_id}/attachments/` |
| Inspect/remove one attachment | `GET`/`DELETE .../attachments/{attachment_id}/` |
| Download an attachment | `GET .../attachments/{attachment_id}/download/` |

A file must already exist in `storage` (its own upload endpoint, outside
`app_platform`) before it can be attached — attaching links an existing
`FileObject` id to `(model, record_id)`. Attachment metadata:
`{id, record_id, file_id, filename, mime_type, size, status, created_at}`.
Download is proxied through Django (not a signed/direct URL) and
re-checks authorization — record access, bucket access, and that the
file is still active — on every request, not just at attach time. One
file may be attached to multiple records; a record may have unlimited
attachments (no count cap in code). There is **no bulk-attach
endpoint** — one file per request.

## Webhooks (Phase 10)

App Platform pushes events toward an external application via
`environments.EnvironmentWebhook` (`environments` app) — the same
subscription/signing-secret store used for every other Environment-
scoped configuration, not a separate App Platform concept:

- `POST environments/{environment_id}/webhooks/` — `{"url", "event_types":
  [...], "enabled"}`. `event_types` is an allowlist of the event-type
  strings below; an empty list subscribes to every event type. The
  response's `signing_secret` is shown **exactly once**, at creation
  time — write it down; it is never retrievable again (same discipline
  as a credential's `secret`).
- A webhook fires only for events an instance emits *while its own
  runtime database is bound to that webhook's Environment* (`PATCH
  environments/{environment_id}/database/`) — an instance with no
  Environment binding at all has no possible subscribers, by
  construction, regardless of what webhooks exist elsewhere in the
  organization.

Event types:

| Event type | Fires when |
|---|---|
| `app_instance.record.create` | A record is created |
| `app_instance.record.update` | A record is updated |
| `app_instance.record.delete` | A record is deleted |
| `app_instance.workflow.transition` | A workflow transition is applied (independent of that transition's own `notify_url`, if any — see below) |

Delivery is `POST` to the webhook's `url`, `Content-Type:
application/json`, with two headers: `X-IntraForge-Event` (the event
type string above) and `X-IntraForge-Signature`, `sha256=<hex>` — an
HMAC-SHA256 of the *exact raw request body bytes*, keyed by the
webhook's own signing secret. Verify it before trusting the payload:

```python
import hmac, hashlib

expected = "sha256=" + hmac.new(signing_secret.encode(), raw_body, hashlib.sha256).hexdigest()
if not hmac.compare_digest(expected, request.headers["X-IntraForge-Signature"]):
    reject()
```

Payload shape is deliberately thin — ids and the event type only, never
a record's actual field values (fetch those via the real record API if
needed; a webhook receiver should treat the payload as a "something
changed, go look" notification, not a data feed):

```json
{"event_id": "...", "event_type": "app_instance.record.create", "instance_id": "...", "model": {"id": "...", "key": "..."}, "record_id": "..."}
```

A `workflow.transition` payload replaces `model`/`record_id` with
`transition` (`{key, label}`), `from_state`/`to_state`, and `record_id`.

Delivery is **at-least-once, never exactly-once and never at-most-once**: a
failed attempt is retried (up to 6 attempts in total, waiting 30 s, 60 s, 120 s,
240 s and 480 s between them; a delivery whose attempts are all used is marked
exhausted and is not retried again), and a receiver may accept a request before
IntraForge can durably record that it did -- for example when the worker dies
between the receiver's `2xx` and the `delivered` marker -- in which case the same
event is sent again. Every delivery carries a stable `event_id` (also the
delivery's identity) in the body: **a receiver must deduplicate on it**. Delivery
is done by a Celery worker — never inline with the request that
triggered the event, and never re-checked against the record's later
state (a payload reflects the moment the event was dispatched, like any
webhook system). This is **separate** from the older, per-transition
`notify_url` field (`docs/implementation/APP_PLATFORM_PHASE5.md`) — that
mechanism is unsigned and Environment-independent, kept exactly as
shipped and unaffected by this section; a transition with both set
fires both, independently.

## Stock movements need a business-operation authority (ADR-0017)

On an application with a stock ledger, **writing a stock movement through the record API needs `inventory.adjust`** on the
application (a `ResourceGrant` on resource type `inventory_operations`, resource id the AppInstance), in addition to
`database.write` on the movement and balance models. Write access to the tables is no longer enough: *the right to sell
is not the right to receive or adjust*. A client that only reads stock, or that writes ordinary records (products,
customers, part numbers), is unaffected. The controlled `operations/sell/` and `operations/receive/` endpoints are for
human sessions only and are not reachable with a bearer token.

## Permissions a client should expect to be gated by

Two separate resources, checked separately — see the readiness review §4
for the full explanation:

- **Instance metadata** (`app_instance.read`/`.manage`/`.schema.manage`)
  — governs the schema-discovery endpoints above and definition mutation.
- **Record data** (`database.read`/`database.write` on the instance's
  physical tenant database) — governs everything under `/records/` and
  `/attachments/`.

Both are capability-based, deny-by-default, and can be granted either
org-wide (a role) or scoped to the specific resource (a `ResourceGrant`
— for a human user via `sharing`, or for a machine client via the
`applications/{id}/resource-grants/` endpoint). For a bearer-token client
that only needs record CRUD (the common case), grant `app_instance.read`
scoped to the `app_instance` resource plus `database.read`/
`database.write` scoped to the instance's `databases.tenant_database`
resource (its id comes back as `database_id` from
`GET app-instances/{id}/runtime/`).

## Versioning

No API version header or URL-versioning scheme beyond the `/api/v1/`
prefix exists for app_platform specifically. An `AppTemplateVersion` is a
distinct, unrelated concept — it versions a *template's definition*, not
the API contract itself.

## What this contract deliberately does NOT include

Everything below is **NOT YET IMPLEMENTED** — do not build an adapter
that assumes any of it:

- Bearer-token/service-account access to schema *mutation*, template
  administration, instance install/archive, or runtime provisioning (see
  Authentication above — a deliberate first-slice scope boundary, not a
  technical blocker; these still require a human session).
- Any filter operator beyond exact-match equality (no `gt`/`lt`/`in`/
  `contains`), even on a `unique`/`indexed` field — indexing changed the
  *performance* of exact-match lookups, not the operator set.
- Multi-field or per-field-targeted search; identifier normalization
  (e.g. dash/space-stripping for a part-number-style lookup) — an app
  that needs this defines its own separate `normalized_...` field and
  populates it itself (see the readiness review §6 for the pattern).
- Multi-column sort.
- A general, arbitrary multi-column *index* for search acceleration
  beyond exact-match (composite uniqueness above is UNIQUE-only, not a
  general composite-index feature) — see the Schema discovery section
  above for what composite uniqueness itself now covers.
- A generic bulk/staged record-import endpoint targeting an App Platform
  model (the existing `imports` app targets `databases.DBTable` only).
- Any declarative, multi-record, atomic "action" or workflow concept.
- Field-level (as opposed to instance/database-level) permissions.
- Webhook delivery *history*/redelivery as an API a client can query or
  trigger (a `WebhookDelivery` row exists internally for
  retry bookkeeping (delivery is at-least-once), but there is no endpoint to list or replay one —
  see the Webhooks section above for what *is* implemented: real,
  signed, Environment-scoped event delivery).
