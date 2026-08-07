# syntax=docker/dockerfile:1
FROM python:3.13-slim AS base

# Runtime deps for psycopg[binary] wheels and general TLS/certs — nothing else.
RUN apt-get update && apt-get install -y --no-install-recommends \
        libpq5 \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN addgroup --system app && adduser --system --ingroup app app

WORKDIR /app

FROM base AS builder
RUN apt-get update && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*
COPY requirements/prod.txt /app/requirements/prod.txt
RUN pip install --no-cache-dir --user -r /app/requirements/prod.txt

FROM base AS runtime
COPY --from=builder /root/.local /home/app/.local
ENV PATH=/home/app/.local/bin:$PATH \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=config.settings.prod

COPY . /app
RUN chown -R app:app /app /home/app/.local

USER app

EXPOSE 8000

# Migrations are NOT run automatically here (LOCAL_DEPLOYMENT.md Section 4)
# — they are a deliberate, reviewed operational step, not a container-start
# side effect that could silently apply an unreviewed schema change.
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3"]
