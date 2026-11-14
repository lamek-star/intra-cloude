# Chapter 2 — The backend — Layout

Topic for: software engineers. Source: IntraForge Engineering Handbook, Chapter 2 — The backend.

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
