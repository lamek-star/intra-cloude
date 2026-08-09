# API Documentation — Private Data Cloud

Status: Phase 3 — accounts, organizations, permissions, workspaces, and
storage endpoints exist and are covered by tests (`apps/backend/*/tests`,
`tests/security/`). No auto-generated OpenAPI schema yet (see "Open Items"
below) — this is a hand-maintained summary of what actually exists, kept
in sync with the code.

## Base Path and Versioning

All API endpoints are mounted under `/api/v1/`, per
`docs/architecture/ARCHITECTURE.md` and Section 14 of the master prompt.
`/healthz` and `/readyz` are unversioned infrastructure endpoints (see
`apps/backend/system/`), not part of the public API surface.

## Authentication

Session-based (Django session cookie), per ADR-0003. Log in via
`POST /api/v1/auth/login/`, then the session cookie authenticates
subsequent requests. CSRF protection applies to unsafe methods once a
session exists — send the `csrftoken` cookie's value back as an
`X-CSRFToken` header. Service-account (application) credential
authentication is Phase 7 work, not yet implemented.

## Error Shape

Every non-2xx response has the shape (see
`apps/backend/system/exceptions.py`):

```json
{"error": {"code": "...", "message": "...", "request_id": "..."}}
```

`request_id` matches the `X-Request-ID` response header
(`apps/backend/system/middleware.py`) for log/audit correlation. Unhandled
exceptions are logged server-side with full detail and never leak a stack
trace to the client (Section 14 of the master prompt).

## Endpoints

### Accounts (`accounts/urls.py`)

| Method | Path | Auth | Notes |
|---|---|---|---|
| POST | `/api/v1/auth/register/` | none | Creates a user, starts a session. Password validated via Django's configured validators. |
| POST | `/api/v1/auth/login/` | none | 401 on bad credentials or inactive account. |
| POST | `/api/v1/auth/logout/` | session | 204, ends the session. |
| GET | `/api/v1/auth/me/` | session | Current user's profile. |

### Organizations (`organizations/urls.py`)

| Method | Path | Auth | Required permission | Notes |
|---|---|---|---|---|
| GET | `/api/v1/organizations/` | session | — | Lists orgs the caller has an **active Membership** in. |
| POST | `/api/v1/organizations/` | session | — | Any authenticated user may create an org; creator becomes an active member and is granted `organization-administrator` (`organizations/services.py:create_organization`). |
| GET | `/api/v1/organizations/{id}/` | session | active membership | 404 (not 403) if the caller isn't a member — existence isn't leaked to non-members. |
| GET | `/api/v1/organizations/{id}/members/` | session | active membership | Lists memberships. |
| POST | `/api/v1/organizations/{id}/members/` | session | `users.manage` | Adds an **existing** user (by email) as an active member. 404 if no such user, 409 if already a member. |
| POST | `/api/v1/organizations/{id}/members/{membership_id}/role/` | session | `permissions.manage` | Assigns a system role (`{"role_slug": "..."}`) to that member within the org. |

### Workspaces & Projects (`workspaces/urls.py`)

| Method | Path | Auth | Notes |
|---|---|---|---|
| GET/POST | `/api/v1/organizations/{org_id}/workspaces/` | active membership | Any active org member may create a workspace (Section 1 of the master prompt — a basic capability, not admin-gated). |
| GET | `/api/v1/workspaces/{id}/` | active membership | 404 if not a member of the owning org. |
| GET/POST | `/api/v1/workspaces/{id}/projects/` | active membership | |
| GET | `/api/v1/projects/{id}/` | active membership | |

### Storage (`storage/urls.py`)

| Method | Path | Auth | Required permission | Notes |
|---|---|---|---|---|
| GET/POST | `/api/v1/projects/{project_id}/buckets/` | active membership | `storage.manage` (POST only) | |
| GET/POST | `/api/v1/buckets/{bucket_id}/folders/` | active membership | `storage.write` (POST only) | `?parent=<uuid>` filters by parent folder (default: top-level). |
| GET/POST | `/api/v1/buckets/{bucket_id}/files/` | active membership | `storage.read` (GET) / `storage.write` (POST, multipart `file` field) | `?folder=<uuid>`, `?search=<substring>`, `?ordering=` (whitelisted: `display_filename`, `-display_filename`, `created_at`, `-created_at`, `size`, `-size`). |
| GET/PATCH/DELETE | `/api/v1/files/{id}/` | active membership | `storage.read` / `storage.write` / `storage.delete` | `PATCH {"display_filename": "...", "folder": "<uuid-or-null>"}` renames/moves. `DELETE` is a soft delete (status flips to `deleted`, object stays in S3). |
| GET | `/api/v1/files/{id}/download/` | active membership | `storage.read` | Streams the file through the backend in 1 MiB chunks — not a presigned redirect (see storage/backends.py note below). |
| POST | `/api/v1/files/{id}/restore/` | active membership | `storage.delete` | Undoes a soft delete. |
| POST | `/api/v1/files/{id}/versions/` | active membership | `storage.write` | Uploads new content for an existing `FileObject`. If the bucket has `versioning_enabled`, the previous content is preserved as a `FileVersion`; otherwise the old S3 object is deleted. |

MIME type is always server-detected from file content
(`storage/backends.py:sniff_mime_type`), never the client-supplied
`Content-Type` header or filename extension — covers common binary
formats via magic-byte signatures, falls back to `text/plain`/
`application/octet-stream`. SHA-256 checksum is computed while streaming
(`storage/services.py:_hash_and_sniff`), never loading the whole file into
memory.

**Download is backend-streamed, not a presigned S3 redirect, by design in
this deployment**: `OBJECT_STORAGE_ENDPOINT` is an internal Docker DNS
name, unreachable from a browser outside the Docker network. Presigned
URL generation exists and works
(`storage/backends.py:ObjectStorageClient.presigned_download_url`) for
topologies where the endpoint is externally reachable — not wired up as
the default path yet.

## Authorization Model in Practice

Every org-scoped view (and, transitively, every workspace/project/bucket/
file view) resolves its target only through a queryset filtered by the
caller's active membership — `organizations.services.get_member_organization`,
`workspaces.views.get_member_workspace`/`get_member_project`,
`storage.services.get_member_bucket`/`get_member_file`. This is the
IDOR/BOLA defense, not a decorative permission check on top of an
unfiltered lookup (docs/security/THREAT_MODEL.md Section 4). Fine-grained
actions (`users.manage`, `permissions.manage`, `storage.*`) go through the
single shared `permissions.services.has_permission` entry point
(ADR-0008). `tests/security/test_tenant_isolation.py` proves org A cannot
read, list, or modify org B's organizations, memberships, role
assignments, buckets, or files by ID substitution.

## Open Items

- **OpenAPI/schema generation** (Section 14 of the master prompt) is not
  wired up yet — `drf-spectacular` or equivalent is a deliberate
  not-yet-added dependency (Section 24: avoid adding dependencies before
  they're needed); add it when the API surface is large enough that
  hand-maintaining this doc becomes the bottleneck.
- Service-account/application authentication — Phase 7.
- Rate limiting is configured at the DRF layer (`AnonRateThrottle`/
  `UserRateThrottle`, see `config/settings/base.py`) but not yet
  exercised by a test.
- Malware scanning on upload is not implemented — no antivirus service
  exists to hook into yet (see docs/security/THREAT_MODEL.md Section 6);
  the upload pipeline has a natural hook point
  (`storage/services.py:upload_file`) for one later.
- File search is a simple `icontains` on `display_filename` — fine at
  current scale, revisit (e.g. Postgres full-text search) if it becomes a
  bottleneck.
