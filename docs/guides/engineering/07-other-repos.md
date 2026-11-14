# Chapter 7 — The other repositories

## 7.1 IntraForge Pay (`intraforge-pay`)

**Simulated value — no cash value.** Pay is the shop's QR wallet: customers hold IF Credits, the cashier shows a QR
code, the customer confirms in the wallet. It runs inside IntraForge as a service application (ADR-0018): image
`intraforge-shop-pay`, containers `pay-1`…`pay-3`, served at `/apps/pay-N/`. Working branches: `main`,
`feature/counters` (counters, migration 0006), `fix/android-gradlew-lf`.

### Layout

| Path | What it is |
|---|---|
| `ifpay/web/app.py` | FastAPI app; pages `/shop` (cashier), `/wallet` (customer), `/admin` (office), `/login` |
| `ifpay/web/api_shop.py`, `api_wallet.py`, `api_admin.py`, `api_auth.py`, `api_internal.py` | The API by audience |
| `ifpay/ledger.py` | **The double-entry journal.** Every movement of credits is a balanced journal entry |
| `ifpay/money.py` | Amounts are integers of hundredths (2500 = 25.00). Never floats |
| `ifpay/checkout.py`, `qr.py`, `keys.py` | QR payment requests, HMAC-signed codes; the signing key lives in Pay's own schema |
| `ifpay/receipts.py`, `refunds.py`, `rewards.py` | One immutable receipt per purchase; maker/checker refunds; cashback |
| `ifpay/allocations.py` | Maker/checker allocation of credits (a manager asks, a supervisor approves) |
| `ifpay/counters.py` | Named counters (tills); each payment records its counter; "today" in the shop's time zone |
| `ifpay/audit.py` | Append-only audit (the table rejects UPDATE/DELETE/TRUNCATE) |
| `ifpay/platform.py`, `runtime.py` | IntraForge's internal API: waits to be installed, opens the provisioned schema |
| `ifpay/documents.py` | Receipts and documents in the shop's IntraForge bucket |
| `ifpay/security.py`, `tls.py` | Sessions, CSRF, capabilities; the "connect to this shop" pairing code for phones |
| `ifpay/migrations/000N_*.sql` | Forward-only SQL migrations with database-enforced rules (`db.py` runs them) |
| `tests/`, `tests_money/` | Tests against real PostgreSQL, and live tests against a real IntraForge |
| `android/` | The **IF Credits Wallet** Android app |

### Rules

- The ledger must always balance; the database enforces it. Never update or delete a journal row — correct with a new
  entry.
- Money is integer hundredths end to end (database, Python, JSON).
- Refunds and allocations need two different people (maker/checker).
- Pay capabilities come from IntraForge roles: Pay Cashier (`ifpay.checkout`), Pay Supervisor, Pay Manager.

### The Android wallet (`android/`, Kotlin, Jetpack Compose)

`MainActivity.kt`, `Screens.kt` (UI), `WalletViewModel.kt` (state), `PilotApi.kt` (HTTP to the shop's Pay),
`Shops.kt` (paired shops and their pinned certificate — `ShopTrustTest.kt`), `Theme.kt`. Build with the Gradle wrapper
(`./gradlew assembleDebug`; the wrapper must have LF line endings). The last debug build is
`kits/IFPayWallet-debug-70680a3.apk`; it has not yet been tested on a real phone.

## 7.2 The Spare Parts / Pharmacy shop application (`spare-part-shop`)

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

## 7.3 Licensing tool (vendor only)

`scripts/licensing/intraforge-license.py` makes serial numbers and activation codes with the vendor's private key, using
the same rules as `licensing/codes.py`. The private key (`licensing/private-key.pem`) and the serial registry stay in
the private `licensing` folder on the vendor's machine: never in a repository, a kit or a shop PC.
