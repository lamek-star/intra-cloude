# Chapter 3 — The frontend — Talking to the API — `src/lib/api.ts`

Topic for: software engineers. Source: IntraForge Engineering Handbook, Chapter 3 — The frontend.

- `api.get / post / patch / delete` call `/api/v1/...` with `credentials: "include"` (the session cookie).
- Before the first write, `ensureCsrfCookie()` calls `GET /auth/csrf/`; every mutating call sends `X-CSRFToken`.
- Errors become `ApiError` with `status`, the backend's `code` and `requestId`. `ErrorBanner` shows a friendly message
  and offers "View technical details".
- The response types (`User`, `Organization`, `Bucket`, `DBTable`…) live in the same file — keep them in step with the
  serializers (Reference A lists the endpoints).
