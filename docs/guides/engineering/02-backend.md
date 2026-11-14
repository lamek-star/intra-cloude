# Chapter 2 — The backend

## Layout

```
apps/backend/
  config/            settings (base, dev, prod, test), urls.py, api_urls.py, celery.py, db_routers.py
  <app>/             one bounded Django app per domain (below)
    models.py        control-plane models
    services.py      the business logic: permission checks, transactions, audit events
    views.py         thin DRF views: parse, call a service, shape the answer
    serializers.py   input validation and output shape
    urls.py          the app's routes (mounted under /api/v1/ by config/api_urls.py)
    tasks.py         Celery tasks (when the app has background work)
    migrations/      schema history — never edited after release
    tests/           the app's tests, against real PostgreSQL and MinIO
  app_runner/        the separate process that runs hosted Node.js apps in locked containers
  requirements/      base.txt, prod.txt, dev.txt — exact pins
```

Settings come from environment variables only (`config/settings/base.py`); the kit writes them into `.env` with fresh
random secrets per shop. `config.settings.test` is used by `pytest` (see `pytest.ini`).

## The apps

| App | Responsibility | Key modules |
|---|---|---|
| `accounts` | People: sign-in, sessions, CSRF, TOTP two-step, passkeys, recovery codes, password change and reset | `services.py`, `totp.py`, `passkeys.py`, `middleware.py` |
| `organizations` | Organizations, members, invitations, teams | `services.py` |
| `permissions` | The capability catalog, roles, role assignments, resource grants; **the one authorization service** | `catalog.py`, `services.py` |
| `org_units` | Organizational hierarchy (branches, departments) and unit-scoped access | `services.py` |
| `workspaces` | Workspaces and projects inside an organization | `views.py` |
| `storage` | Buckets, folders, files, versions, trash, share links, cleanup, upload limits, ClamAV scanning | `services.py`, `backends.py`, `scanning.py` |
| `databases` | The visual schema builder (real tenant tables), rows, exports; connected external PostgreSQL/MySQL/SQL Server | `ddl.py`, `identifiers.py`, `rows.py`, `connectors.py` |
| `imports` | CSV inspection (encoding, delimiter, types) and background bulk insert | `inspect.py`, `tasks.py` |
| `analytics` | A fixed registry of statistics (numpy/scipy), table profiling, dashboards | `operations.py`, `profiling.py` |
| `sharing` | Share grants, compiled into resource grants | `services.py` |
| `applications` | API clients: Application, ServiceAccount, bearer credentials, request log | `authentication.py`, `middleware.py` |
| `oauth_provider` | IntraForge as an OAuth/OIDC sign-in provider for other apps, with a consent screen | `services.py` |
| `environments` | Development / Staging / Production, variables, encrypted secrets, signed webhooks | `services.py`, `crypto.py` |
| `app_platform` | The application platform (Chapter 5) | many; see Reference C |
| `service_apps` | Separately deployed apps (Pay, Spare Parts, Pharmacy): registry, provisioning, internal API, Pay bridge | `services.py`, `internal_views.py`, `pay_bridge.py` |
| `movie_shop` | Movie Shop catalogue, counter sales, media-agent API, customer portal, ads | `services.py`, `sales.py`, `portal.py` |
| `sites` | Hosted static websites, the app runner client, the internet gate (Cloudflare Tunnel) | `services.py`, `serve.py`, `internet.py` |
| `licensing` | Trial, serial number, activation code; read-only without a licence | `codes.py`, `middleware.py` |
| `catalogue_storage` | Storage for the spare-parts catalogue integration | `services.py` |
| `audit` | The immutable audit trail | `services.py` (`record`) |
| `exports` | Portable `.icp` export/import of a whole organization, idempotent restore | `builder.py`, `restorer.py`, `container.py` |
| `system` | `/healthz`, `/readyz`, `/metrics`, health history and alerts, backups and restore tests, diagnostics, throttling | `backups.py`, `health.py`, `redaction.py` |

## The service-layer pattern

Business logic lives in services, never in views or serializers. A service:

1. **Finds the resource inside the caller's organization** (`get_member_bucket`, `get_member_table`, …). A resource of
   another organization raises `Http404` — the caller cannot tell whether it exists.
2. **Checks the capability** through `permissions.services.has_permission(user, code, organization_id, resource)`.
   Effective permission = a role held in that organization (or platform-wide) **or** a non-expired resource grant on
   that exact resource.
3. **Does the work in a transaction.** DDL on the tenant database runs first; if writing the catalog row then fails, a
   compensating DDL undoes it (`databases.services._write_catalog`).
4. **Records an audit event** with `audit.services.record(actor=…, organization_id=…, action=…, result=…)`, including
   a `denied` event when the permission check refuses.

A shortened real example (`databases/services.py`):

```python
def create_tenant_database(*, actor, project, name, request_id=""):
    org_id = project.organization_id
    _require(actor, "database.create", org_id, action="database.create",
             resource_type="tenant_database", resource_id="", request_id=request_id)  # audits "denied" too
    tenant_db = TenantDatabase(project=project, name=name, created_by=actor)
    tenant_db.schema_name = f"db_{tenant_db.id.hex}"
    _execute_tenant_ddl(sql.SQL("CREATE SCHEMA {s}").format(s=sql.Identifier(tenant_db.schema_name)))
    _write_catalog(tenant_db.save,
                   compensating_ddl=sql.SQL("DROP SCHEMA {s} CASCADE").format(s=sql.Identifier(tenant_db.schema_name)))
    audit.record(actor=actor, organization_id=org_id, action="database.create",
                 resource_type="tenant_database", resource_id=tenant_db.id, context={"name": name})
    return tenant_db
```

The view only translates: serializer in, service call, `Response` out, and maps service exceptions to status codes.

## Dynamic SQL

Tables, columns and constraints that people create are real PostgreSQL objects. The rules (`databases/identifiers.py`,
`ddl.py`, `rows.py`):

- identifiers are validated against a strict pattern and a reserved-word list before use;
- every identifier is quoted with `psycopg.sql.Identifier`, every value is a bound parameter — never string formatting;
- DDL runs in a transaction after the permission check and writes an audit event;
- reads are capped (rows and bytes) so one request cannot exhaust the server.

## Background jobs (Celery)

`worker` runs tasks from Valkey; `beat` schedules the periodic ones (`config/celery.py`). Long tasks set
`acks_late=True` with a visibility timeout longer than the task, so a worker that dies mid-task has the task delivered
again — and every such task is written to be safe to run twice (imports keep a checkpoint; exports and restores carry
idempotency keys and operation-derived ids; webhooks de-duplicate by event id). Schedules: backups nightly
(02:00–02:50), restore tests weekly, health checks every 5 minutes, webhook retries with back-off.

## Migrations

- Every model change ships with a migration; never edit a released migration.
- **Rollback safety:** the kit can roll an upgrade back to the previous images while the database keeps the newer
  schema. A new non-null column therefore needs a database default (`db_default=`), so the older code can still insert
  rows. Never drop or rename a column in the same release that stops using it.
- The shop upgrade runs `migrate` itself; on the test copy run
  `docker compose exec -T backend python manage.py migrate`.

## Errors

`system/exceptions.py` turns errors into `{"error": {"code": …, "message": …, "request_id": …}}`. A stack trace is never
sent to the browser; it is logged with the request id, which the screen can show under "View technical details".

## Rate limits

`DEFAULT_THROTTLE_RATES`: anonymous 30/min, signed-in 300/min, **auth 10/min** (sign-in, register, MFA — intentional;
never loosen it, space tests instead), import 20/min per organization. Counters live in Valkey (`CACHES`), so all
gunicorn workers share one budget.

## Management commands worth knowing

| Command | What it does |
|---|---|
| `seed_permissions` | Loads the capability catalog and system roles from `permissions/catalog.py` |
| `bootstrap_super_administrator` | Creates the installation's first Super Administrator |
| `passkey_reset` | Removes a person's passkeys (support) |
| `seed_reference_app`, `seed_spare_parts_reference_app` | Installs a reference application into an organization |
| `upgrade_operation_journals` | Additive upgrade of existing app runtimes' journals |
