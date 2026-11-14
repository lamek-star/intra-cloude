# Chapter 5 — Applications on IntraForge

IntraForge runs business applications in three different ways. Know which one you are touching:

| Kind | Example | Code lives in | Data lives in |
|---|---|---|---|
| **Built-in app (App Platform)** — defined as data, run by one generic engine | Spare Parts / Inventory & Sales, Pharmacy, Repair Shop, Rentals | `app_platform/` + `frontend/src/components/business/` | The organization's tenant schema |
| **Service application** — a separate program with its own image | IntraForge Pay, the Spare Parts shop app, the Pharmacy app | Its own repository; `service_apps/` is IntraForge's side | Its own schema in the tenant database (+ IntraForge storage) |
| **Feature app** — a normal IntraForge app with its own models | Movie Shop, hosted websites | `movie_shop/`, `sites/` | The control database (metadata) + object storage; films stay on the shop's drives |

## 5.1 The App Platform (ADR-0014 – ADR-0017)

An application is a **definition**, not copied code.

1. **Template** (`AppTemplate`, `AppTemplateVersion`) — models, fields, relationships, constraints, workflows, labels.
   The format is strict, bounded and non-executable (`definitions.py`). A published version is **immutable**.
2. **Instance** (`AppInstance`) — one organization's installation of a version (`instances.py`).
3. **Runtime** — real tables in the organization's tenant schema, built by **provisioning** (`runtime_plan.py` plans,
   `provisioning.py` reserves and replays, `runtime_build.py` builds inside transactions). Provisioning is resumable:
   a crash part-way is finished on the next attempt, never duplicated.
4. **Records** — one generic CRUD engine for every instance (`records.py`, `record_views.py`), with relationships,
   attachments (`attachments.py`), unit-scoped access (`unit_scope.py`) and workflow transitions with optional
   approval (`workflows.py`).
5. **Schema evolution** — additive-only live changes to a populated runtime (`schema_evolution.py`).
6. **Upgrades** — a three-way diff between the install snapshot, the live configuration and the newer version: adds
   what is safe, never silently overwrites the customer's own changes (`upgrades.py`). Definitions get deterministic ids
   (`built_in_apps.stabilize_ids`) so a diff compares like with like.
7. **Webhooks** — record and workflow events delivered as HMAC-signed POSTs, **at least once**, with durable retry
   (`webhooks.py`, `delivery_transport.py`, `outbound_http.py`).

### The gallery and release status

`app_platform/built_in_apps.py` is the customer catalog. `install()` does the whole template → instance → runtime
sequence in one call through the same services (so every capability check still applies). Status is real:

| App | Status | Shown to customers |
|---|---|---|
| Spare Parts / Inventory & Sales | QUALIFIED | Yes |
| Pharmacy | PARTIALLY QUALIFIED | Only with `SHOW_UNQUALIFIED_BUILT_IN_APPS` |
| HR, School, Repair Shop, Rentals | EXPERIMENTAL | Only with the flag, clearly labelled |
| CRM, Procurement, Assets, Projects, Documents, Warehouses | DEFERRED | Never |

Promote an app to QUALIFIED only with evidence (main workflow in the normal UI, relationships, constraints,
permissions, restart, upgrade, backup and restore) and record where it lives in the entry's `evidence`.

### Stock: the ledger and operation authority

- **The database decides stock** (ADR-0016). Stock is a quantity ledger (`quantity_ledger.py`): a balance changes only
  by a movement, and PostgreSQL triggers enforce that balance = sum of movements and never below zero. No code in the
  browser, a view or a service does stock arithmetic.
- **Authority belongs to the operation** (ADR-0017, `inventory_authority.py`): `inventory.sell`, `.receive`, `.adjust`,
  `.transfer` are separate, default-deny capabilities. A cashier can sell but not receive.
- Selling and receiving go through `operations/sell` and `operations/receive` (`inventory_operations.py`): one atomic
  transaction (`transactions.py`), an **Idempotency-Key** is required (a double click cannot sell twice), human sessions
  only. A movement written through the generic record API needs `inventory.adjust`. Never add a way for the client to
  name the operation.
- Every record change is journalled in the tenant transaction and published to the control plane afterwards, replayably
  (`operation_journal.py`).

### Adding a new built-in application

1. Write a pure builder in `app_platform/reference_templates/<key>.py` using `_helpers.py` (copy `repair_shop.py` or
   `rentals.py` for a small one; `spare_parts.py` if it needs stock).
2. Add a `BuiltInApp` entry in `built_in_apps.py` with status EXPERIMENTAL.
3. If it needs custom screens, add them under `frontend/src/components/business/`; otherwise the generic record
   screens serve it.
4. Test: the builder validates; install provisions; records CRUD; permissions deny the wrong role; IDOR across
   organizations; upgrade from the previous version.

## 5.2 Service applications (ADR-0018)

A service application is a separately built program that runs as its own container and uses IntraForge for identity,
storage, settings and audit.

- **Types** (`service_apps/types.py`) declare each app's capabilities, the one needed to open it, its settings schema
  (validated by IntraForge and again by the app) and the tables counted in the removal confirmation.
- **Deployments** (`deployments.py`, `SERVICE_APP_DEPLOYMENTS`) are the containers that exist in this installation:
  `pay-1`…`pay-3`, `spareparts`, `pharmacy`. Each gets a service token and a database password in `.env` — only the
  values it needs, never the whole file.
- **Provisioning** (`provisioning.py`) creates one PostgreSQL login role per deployment and one schema per installed
  instance in the tenant database.
- **Open** (`views.py`, `sessions.py`): a person with the open capability clicks **Apps > Open**; IntraForge creates a
  short-lived browser session for that app and redirects to `/apps/<deployment>/`.
- **The internal API** (`internal_views.py`, `/api/v1/internal/`): reachable only on the internal network, authenticated
  by the deployment's token, scoped to that deployment's own instance — there is no way to name another instance.
  It serves the person's identity and capabilities, settings, file storage and audit writes.
- **The Pay bridge** (`pay_bridge.py`, `app_pay.py`): other apps (the Movie Shop, a hosted Node.js app with its
  `IF_API_TOKEN`) ask the organization's Pay to take a payment; IntraForge picks the Pay and passes the result back.

## 5.3 The Movie Shop (ADR-0022)

- **Catalogue** (`models.py`, `scanning.py`): only metadata lives in IntraForge. The films stay on the shop's drives;
  covers are ordinary files in the shop's `movie-covers` bucket. Every folder in a library becomes a category.
- **The media agent** (`scripts/shop-kit/media-agent/MediaAgent.cs`) is a small Windows program on the shop PC. It
  reports drives, scans library folders and copies sold titles onto the customer's USB drive. IntraForge checks every
  value it sends (`scanning.py`) — nothing is trusted because it came from our own agent.
- **Counter sales** (`sales.py`): a cart for one customer, paid through IntraForge Pay or cash, then copied by the agent;
  each title's copy progress is tracked; a failed copy can be retried.
- **The customer portal** (`portal.py`, `portal_views.py`, frontend `components/portal/`): customers sign up on the
  shop Wi-Fi (`https://movies.lan:8443` through the shop-names service), wait for approval, browse and order, and
  collect points (welcome, referral, birthday, every Nth title free). Ads (`ads.py`) show on the portal.
- Capabilities: `movies.read`, `movies.sell`, `movies.manage`.

## 5.4 Hosted websites and the app runner

- **Static sites** (`sites/`): an organization uploads a finished website as a zip (validated by `archive.py`); each
  upload is an immutable `SiteVersion` stored in object storage; one version is active. Sites are served on port 8445,
  a separate origin, by path (`https://<pc>:8445/<site>/`) or by shop name (`https://myshop.lan:8445/`).
- **Server apps**: the `runner` container starts a hosted Node.js app in its own locked container (non-root,
  read-only, no capabilities, memory/CPU limits, no internet). The backend never talks to Docker; it calls the runner's
  fixed operations with a token (`sites/runner.py`).
- **Internet access** (`sites/internet.py`): off by default; the Super Administrator can publish a chosen site through a
  Cloudflare Tunnel. Only hosted sites are ever published — never IntraForge, its API or a service app.

## 5.5 Licensing (ADR-0023)

A new installation has a 30-day trial. Then it needs a **serial number** and an **activation code** made for that PC's
code (`licensing/codes.py`, Ed25519-signed by the vendor tool `scripts/licensing/intraforge-license.py`). Without a
valid licence, `LicenceMiddleware` makes IntraForge **read-only**: anything that would change data is refused except
signing in and out, consent screens, activating the licence and the internal service API. Data is never lost. The
private key and the serial registry live only with the vendor — never in a repository, kit or shop PC.
