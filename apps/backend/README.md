# Backend (Django + DRF)

Phase 1 skeleton. No product features yet — this is the control-plane
project structure, settings, health endpoints, and bounded-app layout that
Phase 2+ builds on. See `docs/architecture/DATA_MODEL.md` Section 1 for the
module boundaries and `docs/architecture/adr/` for the reasoning behind the
framework, database, and broker choices.

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
        api_urls.py           # aggregates each app's /api/v1 routes (empty until Phase 2)
        wsgi.py / asgi.py
    accounts/ organizations/ permissions/ workspaces/ storage/
    databases/ datasets/ imports/ applications/ sharing/ audit/
        # bounded app skeletons (apps.py + migrations/ only, no models yet)
    system/
        views.py    # HealthzView (liveness), ReadyzView (dependency checks)
        middleware.py  # request ID propagation
        exceptions.py    # structured, non-leaking API error responses
        tests/
    manage.py
    pyproject.toml   # ruff / mypy / pytest configuration
    requirements/
```

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
pytest                 # uses config.settings.test automatically (pyproject.toml)
ruff check .
mypy .
```

`pytest`/`ruff`/`mypy` have been run against this scaffold and pass. Tests
that touch a real database require PostgreSQL to be reachable (see
`docker-compose.yml`); this has not yet been exercised end-to-end since the
Phase 1 development machine used to write this scaffold does not have
Docker available — verify `docker compose up` + `pytest` together as the
first step of Phase 2 work.

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
