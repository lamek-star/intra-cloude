# Chapter 7 — The other repositories — 7.1 IntraForge Pay (`intraforge-pay`)

Topic for: software engineers. Source: IntraForge Engineering Handbook, Chapter 7 — The other repositories.

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
