from .base import *  # noqa: F401,F403

DEBUG = False

if not ALLOWED_HOSTS:  # noqa: F405
    raise RuntimeError("ALLOWED_HOSTS must be explicitly set in production")

# Reverse proxy terminates TLS; trust its forwarded-proto header only on the
# internal network path configured in infrastructure/proxy.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = True
# Infra liveness/readiness checks (Docker healthcheck, container
# orchestrators) hit gunicorn directly over plain HTTP on the internal
# Docker network — they never go through the TLS-terminating proxy, so they
# carry no X-Forwarded-Proto header and would otherwise be redirected to an
# HTTPS port gunicorn doesn't serve, hanging until the TLS handshake times
# out (confirmed by actually running this: the container healthcheck failed
# with an SSL handshake timeout before this exemption was added). Real user
# traffic still goes through the proxy and is unaffected.
SECURE_REDIRECT_EXEMPT = [r"^healthz$", r"^readyz$"]
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = False  # local/LAN-first deployments should opt in deliberately, not by default
