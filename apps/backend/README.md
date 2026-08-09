# Backend (Django + DRF)

All 12 planned phases complete. Implemented: authentication (including
TOTP MFA), organizations/permissions (including Teams; gateway-mode MFA
enforcement for new admin role grants), workspaces/projects,
file/object storage, audit logging, database builder (schema +
row-level data explorer), CSV import, application/service-account
integrations, external database connectors (read-only connected-mode
PostgreSQL), internal sharing, optional internet-gateway hardening
(auth-endpoint rate limiting, documented ACME TLS add-on), and
monitoring/backup automation (real `pg_dump`/restore-test cycles on a
Celery Beat schedule, `/metrics`, an opt-in least-privilege tenant-DB
role, a `statement_timeout` DoS backstop). See
`docs/architecture/DATA_MODEL.md` Section 1 for the module boundaries and
`docs/architecture/adr/` for the reasoning behind the framework, database,
and broker choices.

## Layout

```
apps/backend/
    config/
        settings/
            base.py     # shared settings, env-var driven, secure defaults
            dev.py       # local development overrides
            prod.py       # production overrides (fails closed if misconfigured)
            test.py        # settings used by pytest/CI
        celery.py       # Celery app wiring
        db_routers.py     # keeps Django migrations off the tenant DB connection
        urls.py             # root URLconf (/healthz, /readyz, /metrics, /api/v1/*)
        api_urls.py           # aggregates each app's /api/v1 routes
        wsgi.py / asgi.py
    accounts/          # custom User model, register/login/logout/me,
                       # TOTP MFA (totp.py, crypto.py, services.py — Phase 10)
    organizations/     # Organization/Team/Membership, membership + role-assignment + team API
    permissions/       # capability-based authorization (ADR-0008), catalog.py, services.py
    workspaces/        # Workspace/Project
    storage/           # Bucket/Folder/FileObject/FileVersion, MinIO/S3 abstraction (ADR-0004)
    databases/         # TenantDatabase/DBTable/DBColumn/DBForeignKey/DBIndex,
                       # schema-change service (identifiers.py + ddl.py safe DDL),
                       # data explorer row API (rows.py + values.py), formats.py
                       # ConnectedDatabase (Phase 8): crypto.py (Fernet at rest),
                       # connectors.py (external connector interface), connections.py
                       # (service layer — separate from the TenantDatabase DDL path)
    audit/             # AuditEvent, record() helper, minimal audit.read API
    imports/           # ImportJob/ImportJobError, CSV preview + async Celery bulk insert
    applications/       # Application/ServiceAccount/ApplicationCredential, bearer-token auth,
                       # credential lifecycle, ResourceGrant scoping (Phase 7)
    sharing/           # ShareGrant (Phase 9) — compiles to ResourceGrant rows, not a
                       # second enforcement path; external-sharing org toggle lives on
                       # organizations.Organization, not here
    datasets/
        # still a bounded-app skeleton (apps.py + migrations/ only, no models yet) —
        # no phase's exit criteria ended up requiring it
    system/
        views.py    # HealthzView, ReadyzView (dependency checks), MetricsView (Phase 11)
        middleware.py  # request ID propagation
        exceptions.py    # structured, non-leaking API error responses
        models.py    # BackupRecord (Phase 11)
        backups.py    # pg_dump/pg_restore automation + restore-verification
        tenant_role.py  # opt-in least-privilege tenant-DB role provisioning (TB3)
        tasks.py     # Celery tasks wired into CELERY_BEAT_SCHEDULE
        management/commands/  # run_backup, verify_backup, provision_tenant_role
        tests/
    manage.py
    pyproject.toml   # ruff / mypy / pytest configuration
    requirements/
```

See `docs/api/API.md` for the full endpoint reference and
`tests/security/test_tenant_isolation.py` (repo root) for the
cross-organization IDOR/BOLA regression suite that every new resource
type gains a case in.

## Local Setup

Requires Python 3.13 (see `docs/architecture/DEPENDENCY_VERSIONS.md`).

```
python -m venv .venv
./.venv/Scripts/activate   # or source .venv/bin/activate on Linux/macOS
pip install -r requirements/dev.txt
```

`config.settings.dev` requires a running control-plane and tenant
PostgreSQL (see the root `docker-compose.yml`) plus the environment
variables in `.env.example`. Without them, `manage.py check` still passes
(no DB connection is opened for a system check), but running the server or
tests requires the databases to be reachable.

```
DJANGO_SETTINGS_MODULE=config.settings.dev python manage.py check
DJANGO_SETTINGS_MODULE=config.settings.dev python manage.py runserver
```

## Testing & Linting

```
ruff check .    # from apps/backend — uses this dir's pyproject.toml
mypy .          # from apps/backend — same, needed for the django-stubs plugin config
```

For `pytest`, run from the **repo root**, not this directory — the root
`pytest.ini` adds `apps/backend` to `pythonpath` and includes the
top-level `tests/` directory (cross-app tests like
`tests/security/test_tenant_isolation.py`) in the same run:

```
cd <repo-root> && pytest --cov=apps/backend --cov-report=term-missing
```

Running `pytest` from inside `apps/backend` still works for module-local
tests (it'll pick up this directory's `pyproject.toml` instead), but won't
collect `tests/security/`.

All of the above require PostgreSQL, Valkey, and MinIO to be reachable —
in this dev environment (no Docker, and a local networking quirk that
makes bare TCP connects to unlistened `localhost` ports hang instead of
failing fast — see DEPENDENCY_VERSIONS.md), that means running inside a
container attached to the Docker Compose network rather than a host venv;
see the "Phase 3 verification method" note in
`docs/architecture/DEPENDENCY_VERSIONS.md` for the exact command. On a
normal Linux CI runner or dev machine, the host venv works fine directly.

## Regenerating Lock Files

`requirements/*.in` are the source constraints; `requirements/*.txt` are
compiled, pinned lock files (generated with `uv pip compile`, PEP
440-compatible with pip-tools' `pip-compile` if preferred). Regenerate
after changing a `.in` file:

```
uv pip compile requirements/base.in -o requirements/base.txt
uv pip compile requirements/dev.in -o requirements/dev.txt
uv pip compile requirements/prod.in -o requirements/prod.txt
```
