# Chapter 1 — Architecture — How a request travels

Topic for: software engineers. Source: IntraForge Engineering Handbook, Chapter 1 — Architecture.

1. The browser calls `https://localhost:8443/api/v1/...`. Caddy terminates HTTPS and forwards `/api/*` to
   `backend:8000`.
2. Django's middleware runs in order: security headers, a request id (`system.middleware.RequestIDMiddleware`),
   sessions, CSRF, authentication, **`PasswordChangeMiddleware`** (a person whose password was reset may do nothing
   until they choose a new one), **`LicenceMiddleware`** (read-only without a licence), **`ApiRequestLogMiddleware`**
   (records requests made with an application's token).
3. DRF authenticates the caller: a session cookie for people, `Authorization: Bearer pdc_sk_…` for applications.
4. The view is thin: it parses input with a serializer and calls a **service function**.
5. The service resolves the resource **inside the caller's organization** (a foreign id answers 404, not 403, so it
   does not reveal that it exists), checks the **capability** with `permissions.services.has_permission`, does the work
   in a transaction and writes an **audit event**.
6. Slow work is handed to Celery (`worker`) through Valkey; the screen polls the job.
