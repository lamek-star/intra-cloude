# Backend (Django + DRF)

Phase 4. Implemented so far: authentication, organizations/permissions,
workspaces/projects, file/object storage, audit logging, database builder.
See
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
        urls.py             # root URLconf (/healthz, /readyz, /api/v1/*)
        api_urls.py           # aggregates each app's /api/v1 routes
        wsgi.py / asgi.py
    accounts/          # custom User model, register/login/logout/me
    organizations/     # Organization/Team/Membership, membership + role-assignment API
    permissions/       # capability-based authorization (ADR-0008), catalog.py, services.py
    workspaces/        # Workspace/Project
    storage/           # Bucket/Folder/FileObject/FileVersion, MinIO/S3 abstraction (ADR-0004)
    databases/         # TenantDatabase/DBTable/DBColumn/DBForeignKey/DBIndex,
                       # schema-change service (identifiers.py + ddl.py safe DDL)
    audit/             # AuditEvent, record() helper, minimal audit.read API
    datasets/ imports/ applications/ sharing/
        # still bounded-app skeletons (apps.py + migrations/ only, no models yet) —
        # Phases 5+
    system/
        views.py    # HealthzView (liveness), ReadyzView (dependency checks)
        middleware.py  # request ID propagation
        exceptions.py    # structured, non-leaking API error responses
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
