# API Documentation — Private Data Cloud

Status: Phase 2 — accounts, organizations, and permissions endpoints exist
and are covered by tests (`apps/backend/accounts/tests`,
`apps/backend/organizations/tests`, `tests/security/`). No auto-generated
OpenAPI schema yet (see "Open Items" below) — this is a hand-maintained
summary of what actually exists, kept in sync with the code.

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

## Authorization Model in Practice

Every org-scoped view resolves the target `Organization` only through a
queryset filtered by the caller's active membership
(`organizations/views.py:_get_member_organization`) — this is the
IDOR/BOLA defense, not a decorative permission check on top of an
unfiltered lookup (docs/security/THREAT_MODEL.md Section 4). Fine-grained
actions (`users.manage`, `permissions.manage`) go through the single
shared `permissions.services.has_permission` entry point (ADR-0008).
`tests/security/test_tenant_isolation.py` proves org A cannot read, list,
add members to, or assign roles within org B by ID substitution.

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
