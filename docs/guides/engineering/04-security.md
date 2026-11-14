# Chapter 4 — Security and permissions

The detailed, authoritative documents are `docs/security/PERMISSIONS.md` (every capability and the rule for each
endpoint) and `docs/security/THREAT_MODEL.md` (trust boundaries, every gap found and how it was closed). This chapter
is the working summary.

## Who is calling

| Caller | How they prove it | Where |
|---|---|---|
| A person | Email + password → session cookie; optional TOTP second step; passkeys (WebAuthn); recovery codes | `accounts` |
| An application | `Authorization: Bearer pdc_sk_…` → its ServiceAccount's identity user | `applications/authentication.py` |
| A service application (Pay, Spare Parts, Pharmacy) | Its deployment's service token on the **internal** API only | `service_apps/authentication.py` |
| The media agent | That Movie Shop's own agent credential | `movie_shop/views.py` |
| The app runner | A shared runner token, fixed operations only | `sites/runner.py`, `app_runner/` |
| A portal customer | A portal account for one shop (phone number + password) | `movie_shop/portal.py` |

Person details:

- **TOTP** (RFC 6238) is implemented directly in `accounts/totp.py` with the standard library; secrets are encrypted
  at rest with Fernet (`CREDENTIAL_ENCRYPTION_KEY`).
- **Recovery codes** are stored hashed; each works once.
- **Password reset by an administrator** sets `must_change_password`; `PasswordChangeMiddleware` then refuses every API
  call except "who am I", changing the password and signing out.
- New administrative role grants can require MFA in internet-gateway mode.
- Sign-in endpoints are throttled at **10 per minute** on purpose.

## What they may do — capabilities (ADR-0008)

A **capability** is a permission string. Code never branches on a role name; it calls:

```python
from permissions.services import has_permission
has_permission(user, "inventory.sell", organization_id=org.id, resource=("app_instance", instance.id))
```

Effective permission = a **role** held in that organization (or platform-wide, for the Super Administrator) whose
capability set includes the code, **or** a non-expired **ResourceGrant** for that exact capability on that exact
resource. Sharing (`ShareGrant`) compiles down to ResourceGrants — there is no second enforcement path.

Capability families (all in `permissions/catalog.py`, the single source of truth that `seed_permissions` loads):

| Family | Examples |
|---|---|
| Platform | `system.admin`, `backup.manage`, `users.manage`, `permissions.manage`, `audit.read`, `sites.internet.manage` |
| Workspaces, storage | `workspace.manage`, `storage.read/write/delete/share/manage`, `sharing.manage` |
| Databases, data | `database.create/read/write/delete/schema.manage`, `dataset.import/export/analyze`, `connection.manage` |
| Integration | `application.create/read/credentials.manage`, `environment.read/manage/secrets.manage/production.manage`, `export.manage` |
| App platform | `app_template.read/manage/publish`, `app_instance.read/manage/schema.manage/workflow.approve`, `org_unit.*` |
| Stock (ADR-0017) | `inventory.sell`, `inventory.receive`, `inventory.adjust`, `inventory.transfer` — separate, none implies another |
| Service apps | `ifpay.*`, `spareparts.*`, `pharmacy.*` |
| Shop features | `movies.read/sell/manage`, `sites.read/manage` |

System roles are named bundles: Super Administrator (everything, platform-wide), Organization Administrator, Storage
Administrator, Database Administrator, Developer, Editor, Viewer, Auditor, Guest, Service Account, and the app roles
(Spare Parts Manager/Sales/Inventory/Viewer, Pay Manager/Supervisor/Cashier, Pharmacy Manager/Pharmacist/Cashier/
Accountant). **Adding a capability:** add it to `catalog.py` and to `PERMISSIONS.md`, re-run `seed_permissions`, check
it in the service, and test both the allowed and the denied path.

## Tenant isolation

- Every tenant resource carries its organization. Lookups go through `get_member_*` helpers that filter by the
  caller's memberships first; another organization's id answers **404**.
- Business data sits in a per-organization PostgreSQL schema; a service application's data in its own schema with its
  own login role (`service_apps/provisioning.py`).
- **Environment isolation:** an Environment-scoped application credential can never reach a database or bucket bound to
  another Environment (enforced in `databases`, `storage`, `imports`).
- **Every new tenant resource type needs IDOR tests** — Organization A substituting B's ids must fail — before it ships.

## The audit log

`audit.services.record(...)` writes who, what, which resource, the result (`success`, `denied`, `error`) and the request
id. The model refuses updates and deletes. Denied attempts are recorded too. Organization admins and auditors read it
at `/orgs/[orgId]/audit`.

## Secrets and encryption

| What | How |
|---|---|
| MFA secrets, connected-database passwords, environment secrets | Fernet, key from `CREDENTIAL_ENCRYPTION_KEY` |
| Environment secrets, application credentials | Shown exactly once; stored encrypted or hashed |
| Backups and `.icp` exports | AES-256-GCM with an Argon2id-derived key (`exports/container.py`) |
| Webhooks | HMAC-signed bodies, at-least-once delivery, receivers de-duplicate by event id |
| Licences | Ed25519-signed activation codes; the private key never leaves the vendor (`licensing/codes.py`) |
| Diagnostics | Secrets redacted before anything is written (`system/redaction.py`) |

The kit generates fresh random secrets per shop into `.env`. Never commit `.env`, keys or passwords; never print a
secret into a log.

## Network and input defences

- Only the proxy is published, on loopback by default; the Docker network has no internet route.
- `/api/v1/internal/` (service applications) is refused by the proxy from outside.
- **SSRF guard:** connected databases and webhook destinations resolve the host, refuse private/loopback/link-local
  addresses unless allowed, and pin the resolved address (`databases/connectors.py`, `app_platform/outbound_http.py`).
- Uploads have size limits; with ClamAV enabled, a file that cannot be scanned is quarantined (fail-closed).
- Hosted-site zips are fully validated (names, types, sizes, counts) before anything is stored; sites are served on a
  separate origin (port 8445) with cookies stripped.
- The internet gate is off by default; only the Super Administrator, with password and two-step sign-in, can publish
  a hosted site through a Cloudflare Tunnel. IntraForge itself is never published.

## Rules for every change

- Default deny: a new endpoint checks a capability before doing anything.
- Never trust the client to name an operation, an organization or an amount the server can work out itself.
- Stock arithmetic happens only in PostgreSQL (ADR-0016); never in the browser or a view.
- Run `npm audit --omit=dev --audit-level=high` and `pip-audit` for every release; pins never update themselves.
- When a security-sensitive choice is unclear, stop, write the open question down (doc or ADR) and choose the
  established conservative pattern.
