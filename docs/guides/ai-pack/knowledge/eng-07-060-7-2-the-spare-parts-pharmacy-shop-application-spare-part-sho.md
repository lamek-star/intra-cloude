# Chapter 7 — The other repositories — 7.2 The Spare Parts / Pharmacy shop application (`spare-part-shop`)

Topic for: software engineers. Source: IntraForge Engineering Handbook, Chapter 7 — The other repositories.

A standalone, offline-first Next.js application for a spare-parts shop: reference catalogue (manufacturer part numbers,
fitment, drawings), products with photos and prices, stock across warehouses and racks, customers and suppliers, the
chain **enquiry → quotation → order → invoice → payment**, PDFs, barcode/QR labels and reports. The same engine runs
the **Pharmacy** edition (`APP_EDITION=pharmacy`, `src/server/edition.ts`). Branch: `feature/labels-shop-name`.

| Path | What it is |
|---|---|
| `src/app/` | Next.js routes (`(app)/` screens, `api/` handlers) |
| `src/server/domain/` | The business rules: products, inventory, purchasing, sales, documents, reports, permissions |
| `src/server/providers/` | Interfaces (identity, audit, files, configuration, data, unit of work) the domain depends on |
| `src/server/standalone/` | Providers for running alone (SQLite via `node:sqlite`, local files) |
| `src/server/platform/` | Providers for running **inside IntraForge**: identity and capabilities from IntraForge, files in IntraForge storage, audit through an outbox to IntraForge's log, configuration from IntraForge, Pay |
| `src/server/db/` | SQLite connection and migrations; `pg-migrations/` + `postgres.ts` for the IntraForge-provisioned schema |
| `src/server/catalogue/` | Catalogue package import (CSV) |
| `src/server/documents/`, `labels/` | PDF documents and labels (the shop's name, product, captioned part number) |
| `src/ui/` | The screen kit |

Inside IntraForge it is built by `scripts/shop-kit/build-spareparts-image.sh` from a **committed** revision (`git archive`,
never `.env` or local data) and served at `/apps/spare-parts/` and `/apps/pharmacy/`. IntraForge's roles map to its
permissions in `platform/capabilities.ts` (pinned by a test).

Do not confuse it with IntraForge's **built-in** Spare Parts / Inventory & Sales (Chapter 5.1), which is defined as an
App Platform template and is the qualified application.
