# Roadmap: finishing IntraForge, IntraForge Pay first

Written 2026-11-03, from the state of kit 1.4.0 (`dbf44f593`, Pay `b8ebedcf1`), the GitHub repos, and branch
`replica/aws-parity`. Sizes: **S** = days, **M** = 1–3 weeks, **L** = a month or more.

Each step says who does it: **Claude** (code, tests, docs, running the stacks on this PC), **You** (decisions, your
accounts, your shop), or **Outside** (a third party: a lawyer, a regulator, a certificate seller).

## Where things stand

| part | state |
| --- | --- |
| IntraForge Local Edition | qualified for the Spare Parts app; in the own-shop pilot; feature freeze |
| IntraForge Pay | built into kit 1.4.0 as an installable app (slots pay-1..3); **not installed in your shop yet**; simulated IF Credits only |
| Spare Parts → Pay | Spare Parts and hosted apps can request a Pay payment through the Pay bridge (ADR-0018, ADR-0020) |
| Phone wallet | Android app in `intraforge-pay/android`; needs the shop network on (HTTPS + certificate) |
| Source code | **kit 1.4.0's source (`dbf44f593`) and Pay's (`b8ebedcf1`) are on no branch, on GitHub or on this PC**, only inside the installed Docker images |
| This branch | `replica/aws-parity`: 3 security fixes, 9 fixes, 4 screens, pushed, not merged |

## Phase 0: safety net (before anything else) — S

Nothing new is safe to build until the newest code is saved and the security fixes can ship.

| # | step | who |
| --- | --- | --- |
| 0.1 | Find the folder(s) kit 1.4.0 and Pay 1.4.0 were built from and push them to GitHub. If they are gone, Claude can recover the backend Python source from the images (already done once, read-only); the frontend and Pay's Android app would need rebuilding from the nearest commits | You, then Claude |
| 0.2 | Merge `replica/aws-parity` into that source (conflicts expected only in `audit`, `databases/views.py`, `applications`, `permissions/catalog.py`, `config/settings`) and re-run all tests | Claude |
| 0.3 | Build kit **1.5.0** with the three security fixes; install it with the kit's upgrade (it takes a safety backup and rolls back on failure) | Claude builds, You install |
| 0.4 | Change the "Production" environment's type to production; revoke the unused Pay credential | You (2 minutes) |

## Phase 1: IntraForge Pay in your shop (simulated credits) — M

The goal is Pay running in the shop the way Spare Parts does, still with no real money: customers hold IF Credits in a
phone wallet, the cashier takes QR payments, and every payment has a receipt in IntraForge.

| # | step | who |
| --- | --- | --- |
| 1.1 | **Security review of Pay** with the same method that found this branch's three holes: ledger, wallet sessions, QR codes, the Pay bridge, maker/checker | Claude |
| 1.2 | **Close the pilot gaps that matter in a shop:** refunds and voids (none today; a wrong charge can't be undone), HTTPS for phones on the shop network, a per-shop time zone for "today", login rate limiting that holds across processes | Claude |
| 1.3 | Install Pay from **Apps**, give roles (Pay Manager, Pay Supervisor, Pay Cashier) to the right people, create the shop's customer wallets | You (Claude walks you through it) |
| 1.4 | **Spare Parts checkout with Pay:** a sale can be paid from a customer wallet, with the receipt in the sales document. The bridge exists; check the sale screen end to end and fill any gaps | Claude |
| 1.5 | **Phone wallet:** switch on Shop network, trust the shop certificate on phones, build and install the Android app on a test phone | Claude builds, You install |
| 1.6 | **Backups and restore include Pay's ledger**, verified by a real restore test, not assumed | Claude |
| 1.7 | **Pilot run:** 10–20 trading days in parallel with your current records, the same way the Spare Parts pilot was accepted (daily reconciliation, issue log, stop conditions) | You, Claude fixes what you log |

**Done when:** Pay has run 10+ days with every payment reconciled, zero open P0/P1 issues, and a tested restore.

## Phase 2: real money (a business decision before it is a code task) — L

Moving from simulated credits to real money is regulated almost everywhere. It needs a licence or a licensed partner,
not just code. Three paths, in order of how much regulation they bring:

| path | what it means | needs |
| --- | --- | --- |
| **A. Licensed payment partner (recommended)** | Customers pay by card or mobile money through a licensed provider; IntraForge records the payment, receipt and sale | an account with a provider that serves your country, its API keys; Claude builds the integration (webhooks, reconciliation, refunds) |
| B. Shop credit / loyalty points | Credits that can only be spent in your own shop, with no cash-out | a lawyer's check: prepaid credit is regulated in many countries even when closed-loop |
| C. Pay becomes a real wallet | Top-ups, balances in real currency, payouts | an e-money or payment licence from your central bank or payment regulator, audits, a compliance team; not a small-shop project |

Claude will not build real-money handling until you've chosen a path and, for B or C, have legal advice in writing.

## Phase 3: finishing IntraForge for sale — M to L

"Finished" in the project's own terms (`docs/implementation/CURRENT_STATE.md`) means commercial release qualified,
which today is **NOT QUALIFIED**. What stands between:

| # | item | who |
| --- | --- | --- |
| 3.1 | Finish the own-shop pilot: 20 trading days, the acceptance checklist in `LOCAL_EDITION_PILOT.md` | You |
| 3.2 | The externally blocked checks: a real Windows restart on the shop PC, a second PC on the shop network (physical LAN), the Windows installer on a clean machine | You run them, Claude prepares and records them |
| 3.3 | Code signing: a code-signing certificate (removes "Unknown publisher") | Outside (buy a certificate), then Claude wires it in |
| 3.4 | The 9 should-haves still missing: org-wide storage/database lists, backups page in the web app, API request log, usage and quotas, resource search (Ctrl K), OAuth sign-in screens, hosted-app logs, version download/restore, folder upload | Claude, one at a time, if you lift the freeze for each |
| 3.5 | Licences: MinIO is AGPL-3.0, fine for your own shop but **must be reviewed before you sell or give IntraForge to anyone** (README already warns) | Outside (a lawyer) or Claude swaps in an alternative |
| 3.6 | Release paperwork: user guide, support process, pricing, terms | You, Claude drafts |

## Phase 4: upgrades after release — pick as needed

Planned in `replica/architecture.md` and `replica/design/components.md`, not built (feature freeze):

- **Storage:** expiring share links for customers, lifecycle rules (auto-clean old files), tags.
- **Accounts:** MFA recovery codes, admin-issued password reset codes (no email needed), password change.
- **Look:** dark mode (already specified in DESIGN.md §2.5).
- **Operations:** a web backups page, health history, alerts when disk or backups go stale.
- **Apps:** more templates beyond Spare Parts and Pharmacy, Pay at more than one counter.

## Suggested order

```
Phase 0 (safety net)  ──►  Phase 1 (Pay in the shop, simulated)  ──►  Phase 3.1–3.2 (finish pilot checks)
                                         │
                                         └──►  Phase 2 decision (real money: A, B or C)  ──►  build it
Phase 3.3–3.6 and Phase 4: alongside, as you decide
```

The first thing to do is 0.1: find and push the kit 1.4.0 source. Every later step builds on it.
