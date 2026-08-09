# syntax=docker/dockerfile:1
FROM python:3.13-slim AS base

# Runtime deps for psycopg[binary] wheels, TLS/certs, and postgresql-client-18
# (pg_dump/pg_restore for Phase 11 backup automation — system/backups.py).
# Debian's own repo only ships client v17 (Debian trixie); pg_dump is not
# guaranteed forward-compatible with a newer major server version, and the
# stack runs PostgreSQL 18, so the PGDG apt repo is added to install a
# version-matched client instead of relying on whatever Debian bundles —
# confirmed by actually testing pg_dump 17 vs 18 during Phase 11.
RUN apt-get update && apt-get install -y --no-install-recommends \
        libpq5 \
        ca-certificates \
        curl \
        gnupg \
    && install -d /usr/share/postgresql-common/pgdg \
    && curl -fsSL https://www.postgresql.org/media/keys/ACCC4CF8.asc \
        -o /usr/share/postgresql-common/pgdg/apt.postgresql.org.asc \
    && . /etc/os-release \
    && echo "deb [signed-by=/usr/share/postgresql-common/pgdg/apt.postgresql.org.asc] https://apt.postgresql.org/pub/repos/apt ${VERSION_CODENAME}-pgdg main" \
        > /etc/apt/sources.list.d/pgdg.list \
    && apt-get update && apt-get install -y --no-install-recommends postgresql-client-18 \
    && apt-get purge -y --auto-remove curl gnupg \
    && rm -rf /var/lib/apt/lists/*

RUN addgroup --system app && adduser --system --ingroup app app

WORKDIR /app

FROM base AS builder
RUN apt-get update && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*
# A venv (rather than `pip install --user`) makes the runtime stage's
# package availability independent of the `app` user's HOME resolution —
# `--user` installs turned out not to be importable across the stage/user
# boundary when this was actually run (see
# docs/architecture/DEPENDENCY_VERSIONS.md), so don't reintroduce it.
RUN python -m venv /opt/venv
ENV PATH=/opt/venv/bin:$PATH
COPY requirements/prod.txt /app/requirements/prod.txt
RUN pip install --no-cache-dir -r /app/requirements/prod.txt

FROM base AS runtime
COPY --from=builder /opt/venv /opt/venv
ENV PATH=/opt/venv/bin:$PATH \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=config.settings.prod

COPY . /app
# Created here (not left to be auto-created on first volume mount) so its
# ownership is right from the start — a named volume mounted at a path
# that already exists in the image inherits that path's ownership/content
# on first run; one that doesn't would be created root-owned, unwritable
# by the non-root `app` user backup jobs run as (system/backups.py).
RUN mkdir -p /backups && chown -R app:app /app /opt/venv /backups

USER app

EXPOSE 8000

# Migrations are NOT run automatically here (LOCAL_DEPLOYMENT.md Section 4)
# — they are a deliberate, reviewed operational step, not a container-start
# side effect that could silently apply an unreviewed schema change.
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3"]
