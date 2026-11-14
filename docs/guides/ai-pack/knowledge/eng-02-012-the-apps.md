# Chapter 2 — The backend — The apps

Topic for: software engineers. Source: IntraForge Engineering Handbook, Chapter 2 — The backend.

| App | Responsibility | Key modules |
|---|---|---|
| `accounts` | People: sign-in, sessions, CSRF, TOTP two-step, passkeys, recovery codes, password change and reset | `services.py`, `totp.py`, `passkeys.py`, `middleware.py` |
| `organizations` | Organizations, members, invitations, teams | `services.py` |
| `permissions` | The capability catalog, roles, role assignments, resource grants; **the one authorization service** | `catalog.py`, `services.py` |
| `org_units` | Organizational hierarchy (branches, departments) and unit-scoped access | `services.py` |
| `workspaces` | Workspaces and projects inside an organization | `views.py` |
| `storage` | Buckets, folders, files, versions, trash, share links, cleanup, upload limits, ClamAV scanning | `services.py`, `backends.py`, `scanning.py` |
| `databases` | The visual schema builder (real tenant tables), rows, exports; connected external PostgreSQL/MySQL/SQL Server | `ddl.py`, `identifiers.py`, `rows.py`, `connectors.py` |
| `imports` | CSV inspection (encoding, delimiter, types) and background bulk insert | `inspect.py`, `tasks.py` |
| `analytics` | A fixed registry of statistics (numpy/scipy), table profiling, dashboards | `operations.py`, `profiling.py` |
| `sharing` | Share grants, compiled into resource grants | `services.py` |
| `applications` | API clients: Application, ServiceAccount, bearer credentials, request log | `authentication.py`, `middleware.py` |
| `oauth_provider` | IntraForge as an OAuth/OIDC sign-in provider for other apps, with a consent screen | `services.py` |
| `environments` | Development / Staging / Production, variables, encrypted secrets, signed webhooks | `services.py`, `crypto.py` |
| `app_platform` | The application platform (Chapter 5) | many; see Reference C |
| `service_apps` | Separately deployed apps (Pay, Spare Parts, Pharmacy): registry, provisioning, internal API, Pay bridge | `services.py`, `internal_views.py`, `pay_bridge.py` |
| `movie_shop` | Movie Shop catalogue, counter sales, media-agent API, customer portal, ads | `services.py`, `sales.py`, `portal.py` |
| `sites` | Hosted static websites, the app runner client, the internet gate (Cloudflare Tunnel) | `services.py`, `serve.py`, `internet.py` |
| `licensing` | Trial, serial number, activation code; read-only without a licence | `codes.py`, `middleware.py` |
| `catalogue_storage` | Storage for the spare-parts catalogue integration | `services.py` |
| `audit` | The immutable audit trail | `services.py` (`record`) |
| `exports` | Portable `.icp` export/import of a whole organization, idempotent restore | `builder.py`, `restorer.py`, `container.py` |
| `system` | `/healthz`, `/readyz`, `/metrics`, health history and alerts, backups and restore tests, diagnostics, throttling | `backups.py`, `health.py`, `redaction.py` |
