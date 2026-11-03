# Reconciliation: past upgrades × feature freeze × future work

Date: 2026-11-03. Purpose: before `/replica-build` writes code, check every gap in `recon.md` / `architecture.md`
against (1) what past upgrades already shipped, and (2) the Local Edition feature freeze. That splits the work into
**already updated**, **fits the freeze**, and **future**.

## What was compared

| source | what it is |
| --- | --- |
| branch `replica/aws-parity` | new worktree at `C:\Users\your\intraforge\intra-cloude-replica`, from `feature/app-platform` `6fc50c7` (2026-10-04), the newest commit on this PC and on GitHub |
| kit 1.4.0 backend | source copied read-only out of the installed image `intraforge-shop-backend:1.4.0-dbf44f593` (built 2026-10-28). Not started; no network |
| kit 1.4.0 frontend | built output copied out of `intraforge-shop-frontend:1.4.0-dbf44f593` (compiled, so only text and CSS can be checked) |
| freeze rules | `CLAUDE.md` ("feature freeze stays in force"), `docs/implementation/CURRENT_STATE.md` (2026-09-20, re-confirmed in the 2026-09-27 kit 1.1 entry), `docs/implementation/LOCAL_EDITION_MANDATE.md` → SCOPE FREEZE |
| install history | `C:\IntraForgeData\logs\setup.log`, `shop.log`: this PC installed kit 1.4.0 on 2026-10-31. There are no earlier upgrades *on this PC*. The 1.1 → 1.4 history is in the kit itself |

**What the freeze allows (in its own words):** "pilot / bug-fixing / release-hardening". **What it stops:** "another
large feature phase merely because additional features are possible", unless "a small generic capability is genuinely
required to satisfy Local Edition acceptance criteria". It also bans outright: SaaS billing, public marketplace,
multi-region, AI, mobile apps, unrelated integrations. (Those were already `skip` rows in features.csv.)

**Note:** the freeze has already been relaxed once in practice. Kit 1.2–1.4 added Websites + the Node app runner
(ADR-0019/0020), the internet gate, IntraForge Pay and the Pharmacy edition after the freeze date. Those were your
calls to make. This file does not assume the freeze is lifted for anything else.

## 1. Already updated by past upgrades (in the kit, not on the branch)

These exist in `dbf44f593` but not in `6fc50c7`. They were marked "kit-only" in the recon and are now confirmed from
the source:

| item | where in the kit | recon/feature row |
| --- | --- | --- |
| Hosted websites with versions, rollback, take offline | `sites/` (new app), `sites.read`, `sites.manage` | S28, F08: "Static website hosting…" = yes |
| Node.js apps in a locked container | `app_runner/` (new), runner service | S25/S26, F07: "Deploy a small app…" = yes |
| Internet gate (Cloudflare Tunnel), Super Admin only | `sites.internet.manage` | F13, "Opt-in internet exposure" |
| IntraForge Pay slots 1–3, Pharmacy edition | `service_apps/app_pay.py`, `pay_bridge.py`, migrations 0002/0003 | S36 |
| Readable "who" in the audit log (H15) | `audit/serializers.py` `actor_display` | S31 (improves F09) |
| Linked rows show a name, not an id (H8) | `databases/views.py` foreign-key endpoint | S23 (related to L2, but **not** L2) |
| Remove one resource grant from an application | `applications/urls.py` grant detail route | S17 |
| Catalogue diagram figures | `catalogue_storage` migration 0004 | (Spare Parts; outside the AWS slice) |

**Consequence for the build:** none of these needs building. **Anything built on the branch must later merge into
`dbf44f593`.** The modules the first fixes touch (storage, system, accounts, environments, organizations, frontend
`ui.tsx`/`globals.css`) are **identical** in the kit and the branch, so merges there should be clean. `audit`,
`databases/views.py`, `applications`, `permissions/catalog.py` and `config/settings` differ, so changes to those
should wait for the newer source, or stay very small.

## 2. Still open, and fits the freeze (bug fix / hardening / accessibility)

Each was checked against the kit source or the live walkthrough: **none is fixed in 1.4.0**.

| # | item | kind | evidence it is still open | touches |
| --- | --- | --- | --- | --- |
| F1 | 7 WCAG AA contrast failures (primary/danger hover, active rail item, input/checkbox borders, placeholder, neutral focus ring, error-detail text) | accessibility bug | kit CSS still has the old classes; no `accent-hover`/`border-input` tokens | `globals.css`, `ui.tsx`, `AppShell.tsx`, `CommandPalette.tsx` (identical in kit) |
| F2 | Webhooks page says delivery is "**at-most-once** and retried" | doc bug; CLAUDE.md: "never document it as at-most-once" | text present in branch `developer/webhooks/_client.tsx:195` and in the kit build | 1 frontend file |
| F3 | Health "4/4" ignores object storage and service apps (L6) | reliability | `system/` identical in kit; live dashboard showed 4 checks | `system` health view + dashboard |
| F4 | Service account listed in Members with a role picker (L8) | security hardening | `organizations/` identical; seen live | org members serializer / page, `assign_role` guard |
| F5 | An environment typed `production` can lack production-tier protection (L3) | hardening (data integrity) | `environments/` identical; live "Production" is typed development | model constraint + migration; **your data needs fixing first** (see 4) |
| F6 | Sign-in ignores `?next=` and lands on `/apps` (L11) | bug, if reproducible | seen once live; must reproduce before fixing | `login/page.tsx`, `safe-next.ts` |
| F7 | Breadcrumbs skip the workspace level (L10) | UX bug | seen live on bucket and DB pages | page headers |
| F8 | App runtime DB page shows `m_…`/`f_…` ids (L2) | usability bug | seen live in 1.4.0 (H8 fixed linked rows, not this page) | `tenant-databases/[dbId]` + serializer; `databases/views.py` differs in kit → keep small |
| F9 | 3–7 s "Loading…" on first opens (L12) | performance | seen live | measure first; may be config, not code |

**Borderline (your call).** UI for backend endpoints that already exist and are tested. The project did exactly this
kind of unit before the freeze ("Unit 3 — frontend pages for API-only surfaces"), but each one is a new screen:

| # | item | backend already exists |
| --- | --- | --- |
| B1 | Account page: change password, MFA enrol/disable (L7, S04) | `auth/mfa/enroll|confirm|disable|verify` |
| B2 | Folders in the bucket page | `buckets/<id>/folders/` |
| B3 | Trash + restore a deleted file | `files/<id>/restore/` |
| B4 | File versions list | `files/<id>/versions/` |

## 3. Future: new features, after the freeze lifts

From `architecture.md`. Nothing below is in the kit. Each needs new tables, routes or permissions, i.e. a feature
phase:

- **Storage:** external expiring share links (the planned vertical slice, F02), lifecycle rules, tags, version
  *restore*, folder upload with per-file status, storage webhook events.
- **Identity:** MFA recovery codes, admin-issued password reset codes, OAuth provider UI (end-user auth is "not
  designed yet" per the live Auth tab), an org-wide API key list.
- **Observability:** API request log, usage metering, quotas, budgets/alerts, a metrics page, a web Backups page.
- **Console:** Ctrl K search over resources, org-wide storage and database lists, typed delete confirmation.
- **Compute:** hosted-app logs, env binding and restart (**must be built on `dbf44f593`**: `sites`/`app_runner`
  don't exist on the branch).
- **Databases:** connectors beyond Postgres.

## 4. Not code: things only you can do

- **L3 data:** change the "Production" environment of `pay intraforge` to type *production* (or rename it) before F5's
  constraint can migrate.
- **L4:** revoke the unused second credential on `pay intraforge` (both "Last used: Never").
- **Source:** push or copy the `dbf44f593` source to this PC so section 1's work and section 2's fixes end up in one
  history.

## Proposed build scope

Fixes F1–F9, one commit each with tests, on `replica/aws-parity`. That keeps to the freeze, touches almost only modules
that are identical in the kit, and fixes things a shop user meets every day. B1–B4 only if you say so. Section 3 waits
for a decision to lift the freeze.
