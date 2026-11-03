# Spare-parts demo review and integration decisions

Reviewed 2026-09-19, **read-only**, from `C:\Users\Hp\Documents\intraforge-spareparts-demo`
(branch `codex/spareparts-reference`, HEAD `c41cc75`, 2026-09-13; it also carries uncommitted auth and
catalogue-import work). Nothing in that repository was modified, and its Git history is not merged.

## What it is

A self-contained Next.js 16.3 / React 19 / strict-TypeScript application (~13k lines, 66 source files)
declared "reference app ready for an IntraForge adapter". Architecture: **React views → bounded typed
`Services` interface → adapter**. The only adapter is a browser-storage demo adapter that also owns
validation and stock derivation (on-hand = sum of movements; reserved = confirmed unfulfilled sales). The
seam for a platform adapter exists but is empty: `src/integrations/intraforge/contract.ts` defines
`IntraForgeContext` and `IntraForgeAdapterFactory` and nothing else, on purpose ("no speculative endpoints").
Its docs require that platform inventory commands be **transactional and idempotent** — which IntraForge
now provides (ADR-0016).

It was designed as a *separately hosted* app: its uncommitted work adds "Sign in with IntraForge" (OIDC +
PKCE) and a bearer-token client for IntraForge's `catalogue_storage` API.

Screens/modules found: dashboard; grouped navigation (Catalogue · Inventory · Purchasing · Sales · Reports ·
Documents · Management); part detail with tabs (numbers, cross references, compatibility, inventory,
supplier refs, purchases, sales, documents, images, movement history); purchase orders with partial receipts;
quotation → confirm (reserve) → fulfil → invoice → payment; returns; transfers and adjustments; low stock;
contacts; branches/users/roles/settings (design records, not security); documents; audit; CSV reports; invoice
print layout; reference catalogue + import admin; OEM part search; an exploded-diagram (EPC) viewer. Tests: 13
service/component tests and 4 Playwright tests (search → purchase → receipt → customer → sale → invoice).

## Architecture decision

**The customer experience is hosted inside IntraForge's own frontend** (`apps/frontend`, routes under
`/apps/[instanceId]/…`), talking to IntraForge APIs. It is *not* run as a second Next.js server.

- One deployment, one container, one origin, one session: no OIDC hop, no cross-origin cookies, nothing extra to
  install, back up or run offline. Local Edition needs exactly that.
- IntraForge stays authoritative for identity, organizations, projects, App Instances, models, records,
  relationships, constraints, permissions, audit, files, backup/restore, and above all **inventory**: the browser
  states a movement and the database ledger decides the balance.
- The demo's adapter, browser storage, personas, stock arithmetic and in-memory index are **not** brought over.
  Running the demo separately against IntraForge (OIDC) remains possible for a future hosted deployment; it is not
  the Local Edition v1.0 shape.

## Part-number normalization — one canonical behavior

| Where | Rule | Notes |
|---|---|---|
| Demo `normalizeNumber` | `value.toUpperCase().replace(/[\s-]/g, "")` | "other punctuation remains significant" |
| `catalogue_storage` (before) | Python `re.sub(r"[\s-]", "", v).upper()` | Python's `\s` differs from JavaScript's on some Unicode |
| IntraForge search (before this review) | explicit ASCII-ish class | disagreed with JS on em space, ideographic space, BOM |
| **Now (canonical)** | uppercase; remove exactly JavaScript's `\s` set + ASCII `-` | `databases/normalization.py`, code points |

`catalogue_storage.normalize_part_number` delegates to it; App Platform record search applies it server-side
(`normalized_search`); the browser has a ranking-only mirror. `tests/fixtures/part-number-normalization.json`
(19 vectors) is run against Python, the real PostgreSQL expression and JavaScript, and the demo's own function
agrees on 19/19. Original values are never rewritten. Lookup is server-side (no client scan); at 10,001 part
numbers a normalized search takes ~76–134 ms in the test stack.

## Gap map

`SoT` = source of truth in IntraForge. "Reuse UX" = adopt the workflow/IA/terminology; "component" = source
actually reused (none so far — see below).

| Feature | Demo | IntraForge today | Reuse UX | Component | SoT | Action |
|---|---|---|---|---|---|---|
| Navigation | grouped sidebar | flat tabs (in progress) | yes | no | — | **ADAPT** to grouped, supported items only |
| Dashboard | valuation, monthly sales, open POs, low stock | none | yes | no | App Platform records | **ADAPT**: counts + recent activity; no valuation/low-stock (template has no reorder level) |
| Products (Parts) | rich part (sku, brand, category, cost, price, reorder) | `part`: name, description, unit, active, cost, price | yes | no | records | **KEEP** list/add; richer fields = template evolution (post-P0) |
| Part numbers | 15 types, primary flag, provenance | `part_number`: number, source | partly | no | records | **KEEP**; extra types/brand = template evolution |
| Part search | global box, in-memory normalized index | server-side normalized search ✓ | yes (global search box) | no | backend search | **KEEP/ADAPT** picker + search page |
| Cross references / supersession | yes | `supersedes` relation exists in the template | yes | no | records | deferred after P0 |
| Vehicle compatibility | vehicle + m2m link | `vehicle` + m2m `compatible_vehicles` ✓ | yes | no | records | deferred after P0 |
| Warehouses | name, branch, address, bin | name, code | yes | no | records | **KEEP** |
| Inventory / stock | on hand, reserved, available | on hand only (ledger) | yes | no | **quantity ledger** | **KEEP**; do not show reserved/available |
| Stock movements | append-only, typed | append-only, ledger-enforced ✓ | yes | no | ledger | history in Inventory |
| Receive stock | PO receiving, partial | atomic receive (+ optional received PO) ✓ | yes | no | `POST …/transactions/` | **BUILD** |
| Transfers / adjustments | yes | two-leg / single movement supported by backend | yes | no | ledger | after P0 (cheap) |
| Suppliers / customers | contacts | supplier / customer | yes | no | records | **KEEP** |
| Purchase orders / goods receiving | draft → confirm → partial receipt | PO + line records; no lifecycle | partly | no | records | receive creates a *received* PO; full lifecycle post-v1.0 |
| Quotations / reservations / fulfil | full workflow | none (immediate sale) | no | no | — | **not exposed**; needs a workflow decision |
| Sales / invoices | order → invoice → payment | atomic sale: order + line + movement + invoice ✓ | yes | no | `POST …/transactions/` | **BUILD** sell + sales document |
| Invoice print | print stylesheet | none | yes | no | records | **ADAPT** print layout |
| Returns | RETURN_IN movements | reversing movement possible | yes | no | ledger | deferred |
| Reports | CSV | none | yes | no | — | deferred |
| Documents / images | base64 data URLs, 2 MB | attachments over real object storage ✓ | yes | no | storage + attachments | **BUILD** product files tab |
| Audit | local events | platform audit ✓ | no | no | audit | link to org audit page |
| Management (users/roles/branches) | design records only | real users, roles, units, grants ✓ | no | no | platform | **not duplicated** |
| Reference catalogue / Add to My Products | own JSON store + gated providers | `catalogue_storage` (OEMPart, diagrams; import gated to bearer credentials) ✓ | yes | later | catalogue_storage | after P0; never auto-inventory |
| EPC / exploded diagram | `ExplodedDiagramViewer` | none | yes | maybe (own code) | catalogue_storage | secondary; own/licensed art only |
| Authentication | persona + OIDC client | same-origin session ✓ | no | no | accounts | **not reused** |

## Reuse matrix

- **Kept** (existing IntraForge frontend work, judged consistent with the demo's patterns): the gallery/install
  flow; the schema-from-metadata loader; the operation builders that post to the atomic endpoint; the
  config-driven searchable list screen; the server-search product picker; the shared dialog focus fix.
- **Adapted** (ideas, not source): grouped information architecture and terminology; part-detail tab layout;
  global search entry; invoice print layout; empty/loading/error states; "receive then see the balance" flow.
- **Reused as source**: nothing yet. The demo's components are styled with its own CSS and consume its full
  in-memory snapshot, which conflicts with IntraForge's Tailwind design system and its server-side/500-row-cap
  data flow. Candidates for later, only after review of their dependencies: `ExplodedDiagramViewer` (175 lines,
  React only) for the EPC view, and `OEMPartSearch`'s interaction design for the reference catalogue.
- **Deliberately not reused**: the demo adapter, browser persistence, stock derivation, persona/auth, the
  Toyota EPC provider and Nengun import (rights-gated and copyright-sensitive; no third-party EPC artwork or
  Nengun content enters IntraForge), the catalogue JSON store.

## Findings

- Reference-catalogue reads (`catalogue_storage`) are open to any authenticated user by design (shared,
  non-tenant reference data, documented in `docs/CATALOGUE_STORAGE.md`); writes are gated to bearer credentials
  and tested. Fine for a single-organization Local Edition; worth remembering for a multi-tenant deployment.
- The template lacks fields the demo treats as core (part number type/brand/primary, part SKU/brand/category,
  reorder level, reservations). They are **template-evolution items**, not UI work, and are outside the P0 journey.
