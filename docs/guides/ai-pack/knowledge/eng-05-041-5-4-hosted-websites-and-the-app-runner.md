# Chapter 5 — Applications on IntraForge — 5.4 Hosted websites and the app runner

Topic for: software engineers. Source: IntraForge Engineering Handbook, Chapter 5 — Applications on IntraForge.

- **Static sites** (`sites/`): an organization uploads a finished website as a zip (validated by `archive.py`); each
  upload is an immutable `SiteVersion` stored in object storage; one version is active. Sites are served on port 8445,
  a separate origin, by path (`https://<pc>:8445/<site>/`) or by shop name (`https://myshop.lan:8445/`).
- **Server apps**: the `runner` container starts a hosted Node.js app in its own locked container (non-root,
  read-only, no capabilities, memory/CPU limits, no internet). The backend never talks to Docker; it calls the runner's
  fixed operations with a token (`sites/runner.py`).
- **Internet access** (`sites/internet.py`): off by default; the Super Administrator can publish a chosen site through a
  Cloudflare Tunnel. Only hosted sites are ever published — never IntraForge, its API or a service app.
