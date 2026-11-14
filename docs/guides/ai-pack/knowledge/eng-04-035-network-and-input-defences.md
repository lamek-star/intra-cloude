# Chapter 4 — Security and permissions — Network and input defences

Topic for: software engineers. Source: IntraForge Engineering Handbook, Chapter 4 — Security and permissions.

- Only the proxy is published, on loopback by default; the Docker network has no internet route.
- `/api/v1/internal/` (service applications) is refused by the proxy from outside.
- **SSRF guard:** connected databases and webhook destinations resolve the host, refuse private/loopback/link-local
  addresses unless allowed, and pin the resolved address (`databases/connectors.py`, `app_platform/outbound_http.py`).
- Uploads have size limits; with ClamAV enabled, a file that cannot be scanned is quarantined (fail-closed).
- Hosted-site zips are fully validated (names, types, sizes, counts) before anything is stored; sites are served on a
  separate origin (port 8445) with cookies stripped.
- The internet gate is off by default; only the Super Administrator, with password and two-step sign-in, can publish
  a hosted site through a Cloudflare Tunnel. IntraForge itself is never published.
