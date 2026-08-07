from .base import *  # noqa: F401,F403

DEBUG = env_bool("DEBUG", True)  # noqa: F405

ALLOWED_HOSTS = ALLOWED_HOSTS or ["localhost", "127.0.0.1"]  # noqa: F405

# Local dev over plain HTTP (behind a dev-mode proxy or runserver directly)
# should not require HTTPS-only cookies; production (prod.py) does not
# relax these.
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

CORS_ALLOWED_ORIGINS = CORS_ALLOWED_ORIGINS or [  # noqa: F405
    "http://localhost:3000",
]
