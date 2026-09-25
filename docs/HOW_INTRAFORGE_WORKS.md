# How IntraForge works

A plain-language tour of the whole project: what it is, what runs, how a request travels, how data and permissions are kept safe,
how the Spare Parts application works, how backups and installs work, and where everything is in the repository. For the
authoritative detail of any topic, follow the links at the end; where this file and a document under `docs/` disagree, the document wins.

## 1. What IntraForge is

**IntraForge** ("Build. Store. Connect. Privately.") is a **private business platform that runs on your own computer or server**, with no
internet needed for normal use. It combines:

* **File storage** (like a private drive),
* a **no-code database builder** (define tables and links, browse and edit rows, import CSV),
* an **application platform** that installs ready-made business applications on top of that (Spare Parts / Inventory & Sales is the one
  that is qualified for real use),
* **permissions, sharing, audit, backup and recovery**, and a controlled way for other programs to connect.

The product goal of the current phase ("Local Edition v1.0") is narrow: put the qualified **Spare Parts / Inventory & Sales** application on a
small shop's own PC, safely, offline, and keep the data recoverable.

## 2. The big picture

```
   Browser (you)                       other programs (optional, with a token)
        |  https://localhost:8443                |
        v                                        v
 +--------------------------------------------------------------+
 |  proxy   (Caddy: HTTPS, security headers, routes requests)   |
 +------------------+-------------------------------------------+
                    |                          |
          pages / screens                  /api/v1/...
                    v                          v
            +-------------+           +-------------------+        +-----------------+
            |  frontend   |           |  backend (Django) |------->|  worker + beat  |
            |  (Next.js)  |           |  REST API, rules  |        |  (Celery jobs:  |
            +-------------+           +---------+---------+        |  imports, backups)
                                                |                  +--------+--------+
                       +------------------------+----------------+          |
                       v                        v                v          v
              +-----------------+     +------------------+   +---------+  +---------+
              | postgres-control|     | postgres-tenant  |   | valkey  |  | object  |
              | who/what/rules  |     | the business data|   | cache + |  | storage |
              | (the "catalog") |     | (one schema per  |   | job     |  | (MinIO: |
              +-----------------+     |  organization)   |   | queue   |  |  files) |
                                      +------------------+   +---------+  +---------+
```

Everything runs as **Docker containers on one machine**, joined by a private network that has **no route to the internet**. Only the proxy is
reachable, and by default only from that same computer (`127.0.0.1`).

## 3. The parts

| Part | What it is | What it does |
| --- | --- | --- |
| **proxy** | Caddy 2 | Terminates HTTPS with the machine's own certificate (hence the browser's certificate warning), adds security headers, sends page requests to the frontend and `/api` requests to the backend. |
| **frontend** | Next.js 16 / React 19 | The screens: sign-in and registration, organizations, workspaces and projects, the file browser, the database builder and data explorer, the application gallery and each installed application, sharing, audit, dashboards. It holds **no business rules**; it only asks the backend. |
| **backend** | Django + Django REST Framework (gunicorn) | The brain: every rule, every permission check, every write. Business logic lives in service modules, not in views. |
| **worker** and **beat** | Celery | Background jobs (CSV imports, exports, restores, webhook delivery, backups) and the scheduler that starts the nightly and weekly ones. |
| **postgres-control** | PostgreSQL 18 | The *control plane*: users, organizations, roles, permissions, sharing, installed applications and their definitions, the audit trail, backup records. |
| **postgres-tenant** | PostgreSQL 18 | The *data plane*: the actual business tables. **One schema per organization**, so one organization's tables are physically separate from another's. |
| **valkey** | Valkey 9 (Redis-compatible) | Cache, rate-limit counters and the job queue. |
| **object-storage** | MinIO | Uploaded files (sales attachments, documents). Files are stored here, never in Django. |
| clamav (optional) | ClamAV | Scans uploads for malware; a file that cannot be scanned is quarantined (fail-closed). |

## 4. The rules the design never breaks

1. **Control plane and data plane are separate.** Django *describes, authorizes and audits* access to data; the data itself lives in
   PostgreSQL and object storage.
2. **Everything is denied unless a capability allows it**, checked **on the server**. The screen hiding a button is a courtesy, never the lock.
3. **Tenant isolation is a backend invariant.** Organization A must not reach Organization B's data by guessing IDs; every resource carries its
   organization and is checked on every request (and every new resource type gets tests proving this).
4. **No unreviewed dynamic SQL.** Creating tables from user input goes through validated, quoted, transactional service functions that check
   permission and write an audit event.
5. **Boring technology first.** Docker Compose, not Kubernetes; no new datastore or identity system without a written decision (ADR).
6. **Local-first.** No cloud dependency; sharing outside the machine is opt-in and off by default.

## 5. Who may do what: permissions and sharing

* A **capability** is a permission string such as `inventory.sell`, `storage.write` or `database.read`. Code never asks "is this an admin?"; it
  asks the shared authorization service "does this person hold *this capability* on *this resource*?".
* **Roles** are named bundles of capabilities (organization administrator, editor, viewer, auditor, ...). They are configuration, not code paths.
* **Sharing** (`ShareGrant`) lets an owner give another member access to one resource; it is compiled down to the same fine-grained grants the
  rest of the system enforces, not a second enforcement path.
* **Applications and programs** that connect (API clients) authenticate with a bearer token tied to a service account and get only the
  resources explicitly granted to them. Environment-scoped tokens (Development / Staging / Production) cannot reach a resource bound to a
  different environment.
* **People** sign in with email and password, optionally with a **TOTP second factor**. Sign-in attempts are rate-limited (10 per minute on
  purpose; it is a security control, not a bug).
* **Every important action writes an audit event** (who, what, on which resource, allowed or denied). The audit log cannot be edited.

## 6. The backend, app by app

`apps/backend/` is split into small, bounded Django apps:

| App | Responsibility |
| --- | --- |
| `accounts` | Users, sign-in, TOTP multi-factor |
| `organizations`, `permissions`, `org_units` | Organizations, teams, roles and capabilities, organizational hierarchy |
| `workspaces` | Workspaces and projects inside an organization |
| `storage` | Buckets, folders, files, versions (files go to MinIO), upload limits and malware scan |
| `databases`, `datasets` | The visual schema builder (real tables in the tenant database), row browse/edit/export, read-only connections to external PostgreSQL |
| `imports` | CSV preview and background bulk import |
| `analytics` | A fixed registry of statistics operations, per-table profiling, saved dashboards |
| `sharing` | Share grants |
| `applications`, `oauth_provider`, `environments` | API clients and their tokens, an OAuth provider, Development/Staging/Production environments, secrets and signed webhooks |
| `app_platform` | **The application platform** (next section) |
| `catalogue_storage` | Storage for the spare-parts catalogue integration |
| `audit` | The immutable audit trail |
| `exports` | Portable export/import of a whole organization (`.icp` package) |
| `system` | Health (`/healthz`, `/readyz`), backups and restores, diagnostics, secret redaction |

## 7. The application platform

An **application** in IntraForge is not code that is copied in; it is a **definition**:

1. A **template** describes an application: its tables, fields, relationships, screens, constraints, workflows. Templates are **immutable
   versions**, so a released version never changes underneath a customer.
2. An organization **installs** a template. That creates an **instance** and, in the tenant database, real tables for it (in that
   organization's schema) built through the validated provisioning service.
3. A **generic runtime** serves every instance: record create/read/update/delete, relationships, attachments, a generic frontend, sharing,
   workflows (approvals), and signed **webhooks** (delivered at-least-once, with retry and de-duplication by event id).
4. When a newer template version exists, an **upgrade** does a three-way comparison (what was installed, what the customer changed, what is
   new), adds what is safe, and never silently overwrites the customer's own changes.
5. The **application gallery** shows only applications whose release status is high enough. Statuses are QUALIFIED / PARTIALLY QUALIFIED /
   EXPERIMENTAL / DEFERRED; in a customer install **only Spare Parts / Inventory & Sales (QUALIFIED)** is offered.

## 8. Spare Parts / Inventory & Sales

What the shop sees: **products** (with part numbers, brands where supported), **suppliers**, **warehouses**, **customers**, **stock**, **receiving**,
**selling**, **sales documents** (invoices), stored **files**, and a stock history.

How it stays correct:

* **Stock is a ledger, not a number you edit.** Stock changes only by a *movement* (receive, sell, adjust, transfer). The **PostgreSQL database
  itself** (triggers) enforces that the balance always equals the sum of its movements and cannot go negative; the browser and the API never do
  the arithmetic. There is no "type a new quantity" screen, deliberately, so the history is always complete.
* **Part numbers are normalized**, so `04465-0K290`, `044650k290` and `04465 0K290` find the same product.
* **Authority belongs to the business operation** (ADR-0017): `inventory.sell`, `inventory.receive`, `inventory.adjust`, `inventory.transfer` are
  four separate capabilities and none implies another. A **cashier** can sell but not receive; a **receiver** can receive but not sell; the
  owner holds what the owner is given. Selling and receiving go through two controlled endpoints (`operations/sell`, `operations/receive`) that
  build the whole change as one **atomic transaction**, require an **Idempotency-Key** (a repeated click cannot sell twice), and accept human
  sessions only. Writing a movement through the general record API needs `inventory.adjust`.
* **Corrections** in this release are done by the project team through the adjust authority (there is no adjust screen), always as a new
  movement, never by editing or deleting history.

### The life of a sale

1. The cashier types a part number; the frontend calls the API; the backend finds the normalized match.
2. The cashier chooses quantity and customer and presses Sell. The frontend sends `POST .../operations/sell/` with an Idempotency-Key.
3. The backend checks **who** (session), **which organization**, **the `inventory.sell` capability**, then opens one database transaction in the
   organization's schema.
4. Inside that transaction: it creates the sales document and its lines, writes the *sell* movements, and PostgreSQL's triggers verify the new
   balances. If anything fails, **everything rolls back**.
5. An audit event is written, webhook events are queued, and the screen shows the new stock and the sales document.

## 9. Backups and recovery

* **Four kinds of backup**, all encrypted with the installation's backup key: the control database, the business data, the stored files, and the
  configuration. All are needed for a full recovery and should come from the same day.
* **Schedule:** the application's scheduler makes them nightly (02:00 / 02:30 / 02:45 / 02:50) and every Sunday it restores the latest of each into
  a throw-away target to prove it works. A backup never test-restored is shown as *unverified*.
* **Restore from a file** works even after a total loss: the files are restored in order (control database, business data, files) into a fresh
  system. The **keys file** (`.env`) must be the original one, so keep a copy off the PC.
* **On a shop PC** the kit adds a daily backup task at 19:00 (a PC that is off at 02:00 would never take the nightly one), a "Backup to USB"
  shortcut, and a weekly test-restore. A backup that stays on the same disk is not a backup: copy it elsewhere.
* Portable `.icp` exports cover an organization's tree, tables and files, but **not** the application-platform data; use the full backups for that.

## 10. Security in short

Private Docker network with no internet route; only the proxy published, on loopback; HTTPS everywhere; server-side authorization on every call;
tenant isolation by schema; encrypted secrets and backups; an immutable audit log; upload size limits and optional malware scanning; a guard against
connections to internal addresses (SSRF) with the resolved address pinned; webhooks signed with HMAC; secrets redacted from diagnostics; dependency
audits and a pinned, current framework version on every release.

## 11. Four ways to run it

| Way | What it is | Address | Use it for |
| --- | --- | --- | --- |
| **Development stack** (`docker compose up` in the repo root) | The everyday stack, built from source | `https://localhost:8443` | Working on IntraForge |
| **Qualification stack** (`scripts/qualification/compose.yaml`) | A disposable copy with its own volumes | `https://localhost:8444` | Tests, drills and demos of the current code; safe to destroy |
| **Offline demo kit** (`scripts/demo-kit`) | A folder that installs the investor demo (fictional company, stock 95) on a laptop with Docker Desktop and no internet | `https://localhost:8443` | Investor demonstrations |
| **Shop pilot installer** (`scripts/shop-kit`) | One file, `IntraForge-Setup-Complete.exe`, that installs everything on a clean Windows PC with no internet | `https://localhost:8443` | Running IntraForge in a real shop |

### What the shop installer does

`IntraForge-Setup-Complete.exe` carries IntraForge, Microsoft's WSL package and Docker Desktop. It checks the PC (Windows version, memory, disk,
**virtualization**), verifies its own three parts by checksum, unpacks into `C:\IntraForge`, then `Setup-IntraForge.ps1`: switches on the Windows
features Docker's engine needs and restarts (one administrator prompt), installs WSL and Docker after checking their publisher signatures (second
prompt), then installs IntraForge: fresh random secret keys for that shop, images loaded from the file, database structure created, Spare Parts
available in the gallery. It finally registers **start at Windows sign-in**, the daily backup and desktop shortcuts. Data location: databases and
files in Docker volumes; backups, keys copy and logs in `C:\IntraForgeData`. The shop starts **empty**, with no demo data.

## 12. Where things are in the repository

| Path | Contents |
| --- | --- |
| `apps/backend` | The Django backend (the apps above), its tests and migrations |
| `apps/frontend` | The Next.js frontend, unit tests (Vitest) and browser tests (Playwright, `e2e/`) |
| `docker-compose.yml`, `infrastructure/` | The development stack and the proxy configuration |
| `scripts/qualification` | The disposable stack, the recovery, scale and upgrade drills |
| `scripts/demo-kit`, `scripts/shop-kit` | The offline demo kit and the shop installer and its scripts |
| `installer/`, `control-center/` | The earlier Windows MSI / WSL2 / Control Center route (not used for the pilot; not qualified) |
| `docs/` | Architecture, ADRs, security, operations, implementation records, pilot guides (see below) |
| `CLAUDE.md` | The standing engineering rules for this repository |

## 13. Where to read more

* Architecture: `docs/architecture/ARCHITECTURE.md`, the decision records in `docs/architecture/adr/` (0001 control/data plane, 0005 schema per
  organization, 0008 capabilities, 0014-0017 application platform, ledger and inventory authority), `docs/APP_PLATFORM_ARCHITECTURE.md`.
* Security and permissions: `docs/security/THREAT_MODEL.md`, `docs/security/PERMISSIONS.md`.
* Operations: `docs/operations/` (backup and restore, customer backup policy, update policy, diagnostics, licences).
* Current state and evidence: `docs/implementation/CURRENT_STATE.md`, `docs/LOCAL_EDITION_V1_FINAL_QUALIFICATION.md`.
* Using it: `docs/guide/USER_GUIDE.md`, `docs/OWN_SHOP_PILOT_QUICKSTART.md`, `docs/LOCAL_EDITION_PILOT.md`, `docs/INVESTOR_DEMO.md`,
  `docs/pilot/TEST_ON_ANOTHER_PC.md`, `docs/implementation/OWN_SHOP_PILOT_READINESS.md`.

## 14. What is and is not proven (honest status)

* **Qualified:** the Spare Parts / Inventory & Sales application on the Docker runtime (search, receive, sell, sales documents, files,
  restricted users, backup and recovery from files, offline core, upgrade, accessibility, small-shop scale).
* **Tested only in a virtual machine:** the one-file Windows installer on a clean Windows 11 (offline install, restart, backup, recovery).
* **Not qualified / not proven:** a physical shop PC restart; the Windows MSI installer route; access from a second computer on the LAN; code
  signing; the external security scan; commercial distribution (the MinIO AGPL and Docker Desktop licences need decisions before anything is
  handed to anyone else); stock transfers, returns, quotations, reports and tax/accounting compliance are outside this release.

## 15. Glossary

* **Capability** a permission string checked by the server (`inventory.sell`).
* **Control plane / data plane** the catalog of who and what (control) versus the business data itself (data).
* **Tenant** one organization's isolated space.
* **Template / instance** a released application definition / one organization's installation of it.
* **Movement** one line in the stock ledger; stock is the sum of movements.
* **Idempotency-Key** a value that makes a repeated request act once.
* **ADR** an architecture decision record: a short document that says what was decided and why.
* **WSL 2** the Windows feature that runs Linux containers; Docker Desktop uses it on Windows.
* **Nested virtualization** letting a virtual machine itself run virtual machines (needed to run Docker inside a VM).
