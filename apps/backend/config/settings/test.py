"""Settings used by the test runner / CI. Keeps required env vars satisfied
with throwaway values so `pytest` doesn't need a hand-authored `.env`."""

import os

os.environ.setdefault("SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault("CREDENTIAL_ENCRYPTION_KEY", "test-credential-key-not-for-production")
os.environ.setdefault("CONTROL_DB_NAME", "pdc_control_test")
os.environ.setdefault("CONTROL_DB_USER", "postgres")
os.environ.setdefault("CONTROL_DB_PASSWORD", "postgres")
os.environ.setdefault("TENANT_DB_NAME", "pdc_tenant_test")
os.environ.setdefault("TENANT_DB_USER", "postgres")
os.environ.setdefault("TENANT_DB_PASSWORD", "postgres")

from .base import *  # noqa: F401,F403,E402

DEBUG = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]  # fast hashing for tests only

# Runs Celery tasks synchronously, in-process, instead of enqueueing to
# Valkey and needing a live worker — the standard pattern for testing
# task logic. Real worker/broker mechanics are verified separately
# against an actual running worker container, not by this test suite.
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
