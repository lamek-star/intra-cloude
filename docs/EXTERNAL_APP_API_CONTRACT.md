# External App API Contract — App Platform

Baseline: commit `886e75f` (App Platform Phase 3, complete). This document
describes exactly what an externally developed frontend/reference
application could call against IntraForge's App Platform today, and marks
plainly what does not exist yet. Every capability listed is backed by
reading the actual implementation at the stated commit — nothing here is
inferred from another document, and nothing here is a proposed/future
endpoint unless explicitly marked **NOT YET IMPLEMENTED**.

Companion document: `docs/SPARE_PARTS_INTEGRATION_READINESS.md` (the
broader capability review this contract was extracted from).

All paths are relative to `/api/v1/` unless stated otherwise.

---

## Authentication

### What exists and works today

**Browser session authentication** (`accounts` app): `POST auth/login/`
sets a Django session cookie; `GET auth/me/` returns the current user;
`POST auth/logout/`. CSRF is enforced on unsafe methods for session-
authenticated requests (`GET auth/csrf/` issues the token). This is what
IntraForge's own Next.js frontend uses. It is same-origin-oriented
(cookie + CSRF token) and is **not** the recommended mechanism for a
separately hosted frontend.

**Bearer-token application credentials** (`applications` app, Phase 7):
a real, working, tested mechanism designed for exactly this situation.

- `POST organizations/{org_id}/applications/` creates an `Application`
  (backed by a real `User` row via `ServiceAccount.identity_user`).
- `POST applications/{application_id}/credentials/` issues a credential;
  the plaintext secret is shown exactly once.
- `POST applications/{application_id}/resource-grants/` scopes the
  application to specific resources via `ApplicationResourceGrant` (the
  same underlying `ResourceGrant`/capability mechanism used everywhere
  else in this codebase).
- Requests authenticate with `Authorization: Bearer <token>`
  (`ServiceAccountAuthentication`, registered globally in
  `DEFAULT_AUTHENTICATION_CLASSES`).
- **Proven working today for `storage` and `databases`** — see
  `applications/tests/test_applications.py::
  test_resource_grant_restricts_access_to_exactly_that_bucket` for a
  concrete example of a scoped bearer-token client.

### What does NOT work today — blocking gap

**No `app_platform` endpoint accepts a bearer-token/`Application`
client.** Every app_platform view (`FoundationView` and everything that
subclasses it: templates, versions, instances, models, fields,
relationships, records, attachments, runtime provisioning — no
exceptions) rejects a service-account-backed request outright:

```python
# app_platform/views.py — FoundationView.initial()
if not request.user.is_active or hasattr(request.user, "service_account"):
    raise PermissionDenied("Foundation administration requires a human session.")
```

This means **every capability documented below currently requires a real
human browser session** — an external frontend cannot call any of it
using its own service identity yet, even with a correctly scoped
`ApplicationResourceGrant`. Closing this (relaxing or replacing the
`FoundationView` gate for a bearer-token actor holding a valid grant) is
prerequisite platform work, not something an external app can work around
on its own side.

### Recommendation

Once the gap above is closed: bearer-token `ApplicationCredential`,
scoped via `ApplicationResourceGrant` to the specific `AppInstance` (and,
if record-level access is also needed, to the instance's tenant
database — see Permissions below), is the right and safe mechanism —
no cookie/CSRF/session coupling, works cross-origin by design. Until
then, no supported mechanism exists for a non-human client.

### CORS

`CORS_ALLOWED_ORIGINS` is an explicit allowlist (deny-by-default),
`CORS_ALLOW_CREDENTIALS=True`. A separately hosted frontend on a
different origin is supported today *if* its origin is added to the
allowlist — this is generic, not app_platform-specific, and already
works for any API in this codebase once bearer-token access to
app_platform itself is fixed.

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
| List a model's fields | `GET app-models/{model_id}/fields/` | Each: `{id, model, key, label, data_type, required, default_value, position, source_definition_id}` |
| List an instance's models | `GET app-instances/{instance_id}/models/` | Each: `{id, instance, key, label, position, source_definition_id}` |
| List an instance's relationships | `GET app-instances/{instance_id}/relationships/` | Each: `{id, instance, key, label, position, source_definition_id, source_model, target_model, kind, deletion_policy}` |
| Inspect one model/field/relationship | `GET app-models/{id}/`, `GET app-fields/{id}/`, `GET app-relationships/{id}/` | Same shapes as above |

`data_type` is one of exactly `text`, `integer`, `decimal`, `boolean`,
`date`, `datetime`. `kind` is always `many_to_one` (see the readiness
review §1 for why, and how to emulate many-to-many). `deletion_policy` is
`restrict` or `set_null` (no `cascade`).

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
relationship's value is the related record's own UUID.

List response shape (`AppRecordsPage`, note: this is *not* the same
envelope as the schema-discovery endpoints above):

```json
{"count": 0, "limit": 50, "offset": 0, "results": []}
```

### Filtering / sorting / search (all query params on the list endpoint)

- **Filtering**: any query param whose key matches a field or
  relationship definition UUID is applied as an **exact-match equality**
  filter; multiple filters are AND-combined. No other operator exists.
- **Sorting**: `?ordering=<definition_id>` or `?ordering=-<definition_id>`
  — one column only. Unspecified defaults to `id` order, not the
  definition's display `position`.
- **Search**: `?search=<term>` performs a case-insensitive substring
  match (`ILIKE '%term%'`) **OR-ed across every text/varchar column on
  the model automatically** — it cannot be targeted to a single field,
  and it is not index-backed (see the readiness review §6).
- **Pagination**: `?limit=&offset=`, default limit 50, hard cap 500.

### Errors

- `403` (empty body) — the authenticated actor lacks the required
  capability for this instance or its tenant database.
- `400 {"detail": "..."}` — a value-level problem (e.g. an invalid
  reference, a constraint violation surfaced from Postgres).
- `404` — the id doesn't exist, or exists in a different organization
  (identical response either way — the API never reveals whether a
  foreign-org resource exists).
- Definition-mutation endpoints (creating a model/field/relationship)
  follow standard DRF serializer validation-error conventions.

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
— for a human user via `sharing`, or for a machine client via
`ApplicationResourceGrant` once the authentication gap above is closed).

## Versioning

No API version header or URL-versioning scheme beyond the `/api/v1/`
prefix exists for app_platform specifically. An `AppTemplateVersion` is a
distinct, unrelated concept — it versions a *template's definition*, not
the API contract itself.

## What this contract deliberately does NOT include

Everything below is **NOT YET IMPLEMENTED** — do not build an adapter
that assumes any of it:

- Bearer-token/service-account access to any app_platform endpoint (see
  Authentication above — this is the actual blocker, not a missing
  endpoint per se).
- Any filter operator beyond exact-match equality (no `gt`/`lt`/`in`/
  `contains`).
- Multi-field or per-field-targeted search; identifier normalization.
- Multi-column sort.
- A generic bulk/staged record-import endpoint targeting an App Platform
  model (the existing `imports` app targets `databases.DBTable` only).
- Any declarative, multi-record, atomic "action" or workflow concept.
- Field-level (as opposed to instance/database-level) permissions.
- Unique constraints or indexes on App Platform field values.
- Webhooks or any push/event-notification mechanism out of App Platform
  toward an external application.
