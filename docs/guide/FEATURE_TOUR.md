# Feature tour — IntraForge with Spare Parts and Pay, on the shop PC

Status: VERIFIED on the real shop on 2026-11-22 (IntraForge 1.5.12, Spare Parts `f7a408b`, Pay `4f72e0d`), signed in
as the shop's owner. **Visit-only:** every screen was opened and read, filters and tabs were used, nothing was saved,
so the shop's real invoice numbers and stock ledger were not touched. Selling, receiving and payments were run on the
up-to-date test copy instead (the Spare Parts browser tests, 11 passing the same day).

Each step says what a **shop user** does, with an example from the real shop, and where a **developer** finds it. It
does not repeat what the other guides already explain — it links to them:

| For | Read |
|---|---|
| Everyday use of IntraForge | [USER_GUIDE.md](USER_GUIDE.md) |
| Spare Parts screens, buttons and fields | [../training/SPARE_PARTS_LEVEL1_GUIDE.md](../training/SPARE_PARTS_LEVEL1_GUIDE.md), [../training/SPARE_PARTS_BUTTON_REFERENCE.md](../training/SPARE_PARTS_BUTTON_REFERENCE.md), [../training/SPARE_PARTS_FIELD_REFERENCE.md](../training/SPARE_PARTS_FIELD_REFERENCE.md) |
| How it is built | [../HOW_INTRAFORGE_WORKS.md](../HOW_INTRAFORGE_WORKS.md), [../APP_PLATFORM_ARCHITECTURE.md](../APP_PLATFORM_ARCHITECTURE.md) |
| The shop PC (install, Control Center, network) | [../OWN_SHOP_PILOT_QUICKSTART.md](../OWN_SHOP_PILOT_QUICKSTART.md) |

## 0. Opening IntraForge

**User.** Double-click **IntraForge** on the desktop (the Control Center), then **Open IntraForge**. The address is
`https://localhost:8443`. To use names instead, with no port number — `https://intraforge.lan`, and each app at its own
name, such as `https://spare-parts.lan` — choose Control Center > Settings > Shop network > **Open by name on this PC**.
Windows asks for administrator rights once.

If the browser says **"Your connection is not private"**, this PC does not trust IntraForge's own certificate yet:
Control Center > Settings > **Browser certificate** > **Trust IntraForge on this PC**, then choose Yes in Windows'
question and reopen the browser.

**Developer.** Names: `scripts/shop-kit/template/Set-IntraForgeNetwork.ps1 -Mode Names` writes the names to the hosts
file (127.0.0.1), sets `SHOP_NAMES_PORT=443` (an extra loopback-only port line in `docker-compose.yml`, merged away
when unset), and adds the names to the certificate, `ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS`. `-Mode ThisPC` undoes
it. Certificate: `BrowserCertificate` in `scripts/shop-kit/control-center/ControlCenter.cs` reads Caddy's local root from the
proxy and adds it to the Windows user's Root store (Windows asks the user to confirm). Shop-network names for the
other PCs: ADR-0021.

## 1. IntraForge itself

| Step | What the user sees (real shop) | Developer: where it lives | More |
|---|---|---|---|
| Dashboard | "Welcome, sami": 1 organization, 1 workspace, system health 7/7, the last 8 events | `apps/frontend/src/app/(app)/dashboard` | USER_GUIDE §1 |
| Organization | *lamek general trading LLC*: members with phone, roles and **Details**, **Reset password** | `organizations`, `permissions` apps | USER_GUIDE §4, "People, their details" |
| Your account | Your details (phone, job title, address, emergency contact), password, passkeys, two-step sign-in | `accounts` (`MeView`, `ProfileSerializer`) | USER_GUIDE §3 |
| Workspaces and projects | Workspace "Applications" holds the projects *(Spare Parts)* and *(IntraForge Pay)*; a project holds buckets, databases and connected databases | `workspaces` | USER_GUIDE §5 |
| Storage | "Spare Parts files" bucket; usage 0 B, kept versions, Trash | `storage` (MinIO) | USER_GUIDE §6, §8 |
| Databases | None yet; "New database" in a project builds tables with a row editor | `databases` | USER_GUIDE §7 |
| Teams / Units | None yet; groups of members, and branches or departments | `organizations` | USER_GUIDE §4 |
| App templates | None yet; draft app definitions you publish and install | `app_platform` | APP_PLATFORM_ARCHITECTURE |
| Websites | None yet; upload a zip of a site or Node.js app (port 8445) | `system` sites, ADR-0019/0020 | USER_GUIDE §8 |
| Developer | 0 applications, 0 credentials; applications, environments, API keys, webhooks, logs | `applications`, `environments` | EXTERNAL_APP_API_CONTRACT |
| Audit log | Every security action, e.g. `auth.logout ... success`, filterable | `audit` | USER_GUIDE §4 |
| Apps | Installed: **Spare Parts** 1.5.12+f7a408b and **IntraForge Pay** 0.3.0, both Running; Pharmacy available | `service_apps` (ADR-0018) | LOCAL_EDITION_APPLICATIONS |
| Health | Checks every 5 minutes, two weeks of history; all OK | `system` health | USER_GUIDE §8 |
| Backups | Nightly backups of 4 kinds, each restore-tested; **Back up now**; restoring is done in the Control Center | `system/backups.py` | ../operations |
| Internet access | Off; only chosen websites can go online through a Cloudflare Tunnel, never IntraForge itself | ADR (internet gateway) | ../deployment/INTERNET_GATEWAY.md |
| Licence | Trial, 19 days left; this PC's code for activation | `licensing`, ADR-0023 | USER_GUIDE "The licence" |
| Features | Four parts (business apps, Pay and Movie Shop, websites and developer, files and data), all On | `system/features.py`, ADR-0025 | USER_GUIDE "Features" |

## 2. Spare Parts (Apps > Spare Parts > Open)

The shop's 10 real items, with the minimum and reorder levels set when they were entered. Prices and costs are still
**AED 0.00** on all of them: set them on each product (Edit) before the first sale, or quotations and invoices will
be zero.

| Step | What the user sees (real shop) | Developer: where it lives |
|---|---|---|
| Dashboard | Greeting, 11 products (10 active), **7 need ordering**, inventory value, open documents, the Sales trend chart, Stock status: 4 critical, 3 low, 3 OK | `src/app/(app)/page.tsx`, `src/ui/glass.tsx`, `src/ui/stockStatus.tsx` |
| Stock status rule | *Brake pad set* BRK-001: 0 on hand → **Critical**. *Air filter* FIL-002: 4 on hand, minimum 2, reorder 6 → **Low**. *Headlight bulb* LGT-001: 25 → **OK** | one rule: `src/server/standalone/repos/stockRule.ts` |
| My products | List with category filter, status filter and **Low stock only** (shows exactly the 7) | `src/app/(app)/products` |
| A product | *Air filter*: on hand 4, reserved 0, price, cost, reorder level 6 / minimum 2, tabs Overview, Stock, Supplier, OEM, Sales history, photos, **Print label** | `src/app/(app)/products/[id]` |
| Stock and locations | Main warehouse (MAIN): every item's on hand / reserved; movements; integrity check | ledger: ADR-0016 |
| Scan / Search | Scan a barcode or QR, or type a SKU or part number, then Enter | `src/app/(app)/scan` |
| Reference catalogue | Empty; import a CSV or an offline catalogue package (reference only, never your stock or prices) | docs/CATALOGUE_IMPORT.md (Spare Parts repo) |
| Enquiries → Quotations → Orders → Invoices | Empty in the real shop. The flow: an enquiry cart, a quotation, accepted → an order (reserves stock), delivered → an invoice, payments. Tested on the test copy | `src/server/domain/sales.ts`; e2e "enquiry to quotation to order to invoice to payment" |
| Purchasing | Empty; a purchase order, received → stock in and the product's weighted-average cost updated | `src/server/domain/purchasing.ts` |
| Customers / Suppliers | Empty lists with **New** | `src/app/(app)/customers`, `suppliers` |
| Reports | Daily sales log, stock by batch and expiry, expired stock, on hand, low stock, stock value, sales by month and by item, customer activity, unpaid invoices, quotation conversion, suppliers; a From/To date range | `src/server/domain/reports.ts` |
| Users | sami, Admin; on IntraForge, people and roles come from IntraForge (Organization > Members) | `src/server/platform/identity.ts` |
| Shop settings | Shop name, tax number, phone, email, address, currency AED, tax 5 %, quotation valid 14 days, invoice due 30 days, default terms; the shop language. **Tax number, phone, email and address are still empty**: until a tax number is set, invoices print as "Invoice", not "Tax invoice" | `src/app/(app)/admin/settings` |
| Audit | Every change, e.g. `product.create Product LGT-001 Headlight bulb created` | `src/server/domain/app.ts` (audit on every change) |
| Language and theme | Each person picks a language (English, Arabic, Amharic, Tigrinya); the sidebar's **Dark mode** switch | `src/ui/messages/*.ts`, `src/ui/glass.tsx` |
| Sign out | Ends the IntraForge sign-in too and goes straight to IntraForge's sign-in page | `src/ui/session.tsx` |

## 3. IntraForge Pay (Apps > IntraForge Pay > Open)

| Step | What the user sees (real shop) | Developer: where it lives |
|---|---|---|
| Checkout | New sale (amount in simulated IF Credits) → QR; "Shop verified with IntraForge"; today's sales per counter; refunds (another person approves) | Pay repo, `/apps/pay-1/shop` |
| Admin | Credits (maker/checker), cashback, refunds, customers, transactions, audit; the ledger is balanced (debits = credits) | `/apps/pay-1/admin` |
| Customer wallet | Customers sign in at `/apps/pay-1/login` with the details the shop gives them; staff never sign in there — they open Pay from Apps | Android app IF Credits Wallet 0.3.0 |

All Pay values are **simulated** credits with no cash value.

## 4. What the tour found

| Finding | Status |
|---|---|
| Sign-out showed Spare Parts' own sign-in form for a moment, then reloaded into IntraForge's | Fixed (Spare Parts `65df7ae`, with a browser test that fails on the old code) |
| The browser warned "not private" on the shop PC: the PC had never trusted the shop's own certificate (only an older test copy's) | Fixed: Control Center > Settings > Browser certificate (`a64c138`) |
| "From" / "To" on Reports and "To" on a stock transfer were English in every language | Fixed (keys `rep.from`, `rep.to`, `stock.to` in all four languages) |
| No names without a port on this PC | Added: Settings > Shop network > Open by name on this PC |
| All 10 items have price and cost AED 0.00 | The owner's data to fill in |
| Shop settings: tax number, phone, email and address empty | The owner's data to fill in |
| "TEST brake pad (delete me)" is still listed (inactive) | Inactive items stay for the history; filter Status > Active to hide it |
| No Super Administrator yet | The owner's step: Control Center > Settings > Owner |
| 3 of 4 backups "Not yet tested" | Expected right after the 12:09 upgrade backup; the nightly restore test marks them |

No page failed: every request in the tour answered without an error (checked on each page).
