"""
Base Django settings shared by every environment.

Nothing environment-specific (DEBUG, ALLOWED_HOSTS defaults, etc.) is
hardcoded here beyond safe-by-default values — see dev.py / prod.py for
environment overrides, and .env.example for the full variable list.
"""

import os
from pathlib import Path

from celery.schedules import crontab

BASE_DIR = Path(__file__).resolve().parent.parent.parent


def env(name, default=None, required=False):
    value = os.environ.get(name, default)
    if required and value is None:
        raise RuntimeError(f"Required environment variable {name!r} is not set")
    return value


def env_bool(name, default=False):
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in ("1", "true", "yes", "on")


def env_list(name, default=""):
    value = os.environ.get(name, default)
    return [item.strip() for item in value.split(",") if item.strip()]


SECRET_KEY = env("SECRET_KEY", required=True)

# Safe default: no hosts allowed until explicitly configured per environment.
ALLOWED_HOSTS = env_list("ALLOWED_HOSTS", "")
CSRF_TRUSTED_ORIGINS = env_list("CSRF_TRUSTED_ORIGINS", "")

# --- Applications ---
# Django admin is deliberately NOT installed at this phase (ADR-0002):
# it is a bypass of the capability-based permission model and will only be
# added later, explicitly gated to Super Administrators, if ever.
DJANGO_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.staticfiles",
]

THIRD_PARTY_APPS = [
    "rest_framework",
    "corsheaders",
]

# Bounded Django apps per docs/architecture/DATA_MODEL.md Section 1.
# Each owns its own models/services/serializers/tests; no giant shared app.
LOCAL_APPS = [
    "accounts",
    "organizations",
    "permissions",
    "workspaces",
    "storage",
    "databases",
    "datasets",
    "imports",
    "applications",
    "environments",
    "sharing",
    "audit",
    "system",
    "exports",
    "analytics",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "system.middleware.RequestIDMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# --- Databases ---
# Per ADR-0001 / ADR-0005: `default` is the control-plane database (users,
# orgs, permissions, catalog, audit) and is the only alias Django migrates.
# `tenant` is a *connection* to the tenant PostgreSQL cluster used by the
# `databases` app's service layer to execute validated, schema-scoped DDL/DML
# directly (see docs/architecture/DATA_MODEL.md Section 5) — Django's ORM/
# migration framework never manages tenant schemas.
# A generous but real upper bound on any single statement — a server-side
# backstop against a runaway/pathological query (Section 20 of the master
# prompt; docs/security/THREAT_MODEL.md TB3 "Denial of service") on top of
# the application-layer bounds that already exist (row API hard-capped at
# 500 rows per page, CSV import chunked at 1000 rows per transaction).
# Deliberately generous (not tight) since it applies to every statement on
# both connections, including admin/DDL operations — Phase 11 hardening,
# not meant to be the primary defense against slow individual queries.
DB_STATEMENT_TIMEOUT_MS = env("DB_STATEMENT_TIMEOUT_MS", "60000")

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env("CONTROL_DB_NAME", required=True),
        "USER": env("CONTROL_DB_USER", required=True),
        "PASSWORD": env("CONTROL_DB_PASSWORD", required=True),
        "HOST": env("CONTROL_DB_HOST", "localhost"),
        "PORT": env("CONTROL_DB_PORT", "5432"),
        "CONN_MAX_AGE": 60,
        "OPTIONS": {"options": f"-c statement_timeout={DB_STATEMENT_TIMEOUT_MS}"},
    },
    "tenant": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env("TENANT_DB_NAME", required=True),
        "USER": env("TENANT_DB_USER", required=True),
        "PASSWORD": env("TENANT_DB_PASSWORD", required=True),
        "HOST": env("TENANT_DB_HOST", "localhost"),
        "PORT": env("TENANT_DB_PORT", "5432"),
        "CONN_MAX_AGE": 60,
        "OPTIONS": {"options": f"-c statement_timeout={DB_STATEMENT_TIMEOUT_MS}"},
    },
}

# Only the `default` (control-plane) database is migrated; the `tenant`
# connection is never a migration target (see comment above DATABASES).
DATABASE_ROUTERS = ["config.db_routers.TenantConnectionRouter"]

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 12}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

AUTH_USER_MODEL = "accounts.User"

# --- Security defaults (secure by default; environments may tighten further,
# never loosen, without an explicit documented reason) ---
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SECURE = True
CSRF_COOKIE_HTTPONLY = False  # frontend JS needs to read it to set the header
CSRF_COOKIE_SAMESITE = "Lax"
X_FRAME_OPTIONS = "DENY"
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"

# CORS: deny by default; explicit allowlist only, never a wildcard
# (Section 24 / Section 17 of the master prompt).
CORS_ALLOWED_ORIGINS = env_list("CORS_ALLOWED_ORIGINS", "")
CORS_ALLOW_CREDENTIALS = True

# --- Django REST Framework ---
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
        "applications.authentication.ServiceAccountAuthentication",
    ],
    # Deny by default: every view requires authentication unless it
    # explicitly opts out (e.g. /healthz).
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.LimitOffsetPagination",
    "PAGE_SIZE": 50,
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "30/minute",
        "user": "300/minute",
        # Tighter budget for login/register/MFA-verify specifically —
        # the endpoints a credential-stuffing or brute-force attempt
        # would actually hit (Phase 10; docs/deployment/INTERNET_GATEWAY.md).
        "auth": "10/minute",
        # Shared per-organization budget (system.throttling.OrganizationRateThrottle,
        # not the per-user "user" scope above) on import-job creation — each
        # job is a background Celery task with real DB/object-storage cost,
        # so this bounds it per organization, not just per member.
        "import": "20/minute",
    },
    "EXCEPTION_HANDLER": "system.exceptions.structured_exception_handler",
}

# --- Celery (broker/result backend: Valkey, Redis-protocol — see ADR-0011) ---
CELERY_BROKER_URL = env("REDIS_URL", "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = env("REDIS_URL", "redis://localhost:6379/0")
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60

# Nightly full backups, weekly automated restoration tests (Phase 11;
# docs/operations/BACKUP_RESTORE.md Sections 3 and 7 — "a recurring job
# restores the latest backup set... this is a scheduled Celery Beat job,
# not a manual checklist item that quietly stops happening"). Only takes
# effect for the `beat` service, which schedules these against `worker`.
CELERY_BEAT_SCHEDULE = {
    "backup-control-db-nightly": {
        "task": "system.tasks.run_backup_task",
        "schedule": crontab(hour=2, minute=0),
        "args": ("control_db",),
    },
    "backup-tenant-db-nightly": {
        "task": "system.tasks.run_backup_task",
        "schedule": crontab(hour=2, minute=30),
        "args": ("tenant_db",),
    },
    "verify-control-db-backup-weekly": {
        "task": "system.tasks.verify_latest_backup_task",
        "schedule": crontab(hour=3, minute=0, day_of_week=0),
        "args": ("control_db",),
    },
    "verify-tenant-db-backup-weekly": {
        "task": "system.tasks.verify_latest_backup_task",
        "schedule": crontab(hour=3, minute=30, day_of_week=0),
        "args": ("tenant_db",),
    },
    # Phase 15: object storage and configuration join the same nightly-
    # backup/weekly-restore-test cadence as the two Postgres backups
    # above — a complete deployment's worth of state, not just the
    # database.
    "backup-object-storage-nightly": {
        "task": "system.tasks.run_backup_task",
        "schedule": crontab(hour=2, minute=45),
        "args": ("object_storage",),
    },
    "backup-configuration-nightly": {
        "task": "system.tasks.run_backup_task",
        "schedule": crontab(hour=2, minute=50),
        "args": ("configuration",),
    },
    "verify-object-storage-backup-weekly": {
        "task": "system.tasks.verify_latest_backup_task",
        "schedule": crontab(hour=4, minute=0, day_of_week=0),
        "args": ("object_storage",),
    },
    "verify-configuration-backup-weekly": {
        "task": "system.tasks.verify_latest_backup_task",
        "schedule": crontab(hour=4, minute=15, day_of_week=0),
        "args": ("configuration",),
    },
}

# --- Object storage (S3-compatible; MinIO locally — ADR-0004) ---
OBJECT_STORAGE_ENDPOINT = env("OBJECT_STORAGE_ENDPOINT", "")
OBJECT_STORAGE_REGION = env("OBJECT_STORAGE_REGION", "us-east-1")
OBJECT_STORAGE_ACCESS_KEY = env("OBJECT_STORAGE_ROOT_USER", "")
OBJECT_STORAGE_SECRET_KEY = env("OBJECT_STORAGE_ROOT_PASSWORD", "")
OBJECT_STORAGE_BUCKET_PREFIX = env("OBJECT_STORAGE_BUCKET_PREFIX", "pdc")

# Server-side upper bound on any single file upload (Section 8 of the
# master prompt) — no such cap existed before. Default 2 GiB; an
# operator with a real capacity plan (docs/architecture/... hardware
# guide, once written) can raise or lower it per deployment profile.
MAX_UPLOAD_SIZE_BYTES = int(env("MAX_UPLOAD_SIZE_BYTES", str(2 * 1024**3)))

# --- Malware scanning (Section 33 of the master prompt) ---
# Off by default: turning this on requires a ClamAV daemon actually
# reachable at CLAMAV_HOST/CLAMAV_PORT (see infrastructure/docker and
# docker-compose.yml's optional `clamav` service). storage/services.py
# fails closed — a scanner that can't be reached quarantines the file,
# it never falls back to treating it as clean.
MALWARE_SCAN_ENABLED = env_bool("MALWARE_SCAN_ENABLED", False)
CLAMAV_HOST = env("CLAMAV_HOST", "clamav")
CLAMAV_PORT = int(env("CLAMAV_PORT", "3310"))
CLAMAV_TIMEOUT_SECONDS = int(env("CLAMAV_TIMEOUT_SECONDS", "30"))

# Dedicated key for encrypting ConnectedDatabase credentials at rest
# (Section 15 of the master prompt) — distinct from SECRET_KEY.
CREDENTIAL_ENCRYPTION_KEY = env("CREDENTIAL_ENCRYPTION_KEY", required=True)

# --- Connected-database SSRF guard (Section 30 of the master prompt) ---
# databases/connectors.py always blocks loopback/link-local/reserved/
# multicast targets (link-local in particular covers cloud metadata
# endpoints like 169.254.169.254) before dialing a connected database.
# RFC1918 private ranges are allowed by default because they are the
# *expected* target for this local-first, on-prem product — a
# customer's own PostgreSQL is very likely to live on their own LAN.
# Flip this on for deployments where that assumption doesn't hold (e.g.
# a hosted/multi-tenant topology where "private network" might mean the
# host's own internal Docker network, which tenants must not reach).
CONNECTED_DATABASE_BLOCK_PRIVATE_NETWORKS = env_bool("CONNECTED_DATABASE_BLOCK_PRIVATE_NETWORKS", False)

# --- Analytics (Section 20/27 of the master prompt) ---
# Upper bound on how many rows any single analytics operation pulls
# into Python/numpy/scipy — a statistics engine must not become a
# denial-of-service vector. Deliberately smaller than a raw data-export
# cap: unlike a CSV export, this bounds request latency, not just total
# throughput.
ANALYTICS_MAX_ROWS = int(env("ANALYTICS_MAX_ROWS", "200000"))

# --- Backups (Phase 11; docs/operations/BACKUP_RESTORE.md) ---
# Where pg_dump output is written (system/backups.py). Mounted as a named
# Docker volume by default (docker-compose.yml) — an operator points its
# backing storage at off-host/NAS media per BACKUP_RESTORE.md Section 4;
# a local volume alone is not itself an off-host backup.
BACKUP_DIR = env("BACKUP_DIR", "/backups")

# Optional (Phase 15 hardening): when set, every backup type is wrapped
# in the same AES-256-GCM/Argon2id container format exports/container.py
# uses for .icp packages — one encrypted-archive format across the
# product rather than a second one invented for backups. Deliberately a
# *separate* secret from CREDENTIAL_ENCRYPTION_KEY: a configuration
# backup contains CREDENTIAL_ENCRYPTION_KEY itself, so encrypting it
# with itself would be circular (losing the key would make the very
# backup meant to recover it unreadable too). Store this key completely
# separately from BACKUP_DIR — e.g. a password manager, not this server
# — losing it makes every encrypted backup permanently unrecoverable.
BACKUP_ENCRYPTION_KEY = env("BACKUP_ENCRYPTION_KEY", "")

# --- Feature flags (secure defaults: off) ---
FEATURE_EXTERNAL_SHARING_ENABLED = env_bool("FEATURE_EXTERNAL_SHARING_ENABLED", False)
FEATURE_INTERNET_GATEWAY_ENABLED = env_bool("FEATURE_INTERNET_GATEWAY_ENABLED", False)

# --- Logging: structured, request-ID-aware (Section 20) ---
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "structured": {
            "format": (
                '{"time": "%(asctime)s", "level": "%(levelname)s", '
                '"logger": "%(name)s", "message": "%(message)s"}'
            ),
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "structured",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
    "loggers": {
        "django": {"handlers": ["console"], "level": "INFO", "propagate": False},
    },
}
