# IntraForge investor demonstration (10-12 minutes)

**The story in one sentence:** a shop gets its own private business system that runs on its own computer, keeps
working without the internet, and does not let the person at the counter do things they were never given.

Everything below is **fictional demo data** in a separate demo organization. Never mix it with a pilot's real data.

## Before the demo (5 minutes, once)

1. Start the system and open it in a browser. Confirm the health page says everything is ok.
2. Create the demo account and organization **"Harmoney Auto Parts LLC -- DEMO"**, a workspace "Company" and a project
   "Shop".
3. Create a second account for the "cashier" and add it to the organization (Organization page, *Add member*).
4. Pre-flight check: run the automated journey once (`apps/frontend/e2e/spare-parts-flagship.spec.ts`, about 20
   seconds). If it is green, every screen in the script below works on this machine.

Shortcut: `e2e/spare-parts-recovery-prep.spec.ts` builds exactly this business (owner, cashier with the right
permissions, 95 in stock, a stored document) through the real screens and writes the logins to a file.

## The script

| # | What you do | What to say | What the audience sees |
| --- | --- | --- | --- |
| 1 | Open *Applications* for the project | "This is a business system that belongs to the shop. No subscription, no cloud." | One application, **Spare Parts**, marked *Ready for use* |
| 2 | *Install*, then *Open application* | "One click. It installed a real database for this shop." | The Spare Parts home with counts at zero |
| 3 | Add a **supplier** ("Demo Supplier A"), a **warehouse** ("Main Warehouse", MAIN), a **product** ("Demo Oil Filter", list price 15.00) | "Ordinary business records." | Each appears in its list |
| 4 | On the product, *Add part number* `04465-0K290` (source "OEM (demo)") | "One part is known by many numbers." | The part number listed |
| 5 | In the search box type `044650K290`, then `04465 0k290` | "Staff type it every way. The system finds the same part and still shows the original number." | The same product both times |
| 6 | *Receive stock*: product (find it by that number), warehouse, quantity **100**, supplier, unit cost 9.50, reference "DN-1001" | "Goods arrive." | **On hand: 100** |
| 7 | Add a **customer** ("Demo Retail Customer"), then *New sale*: 5 of the oil filter | "A sale." | **On hand after sale: 95**; a sales document with an invoice number |
| 8 | Open the sales document | "Order, line and invoice are one record; the stock came out in the same instant." | The invoice |
| 9 | Try to sell **96** | "The system will not let stock go negative -- and it leaves nothing half-done." | A plain refusal, "Nothing was changed"; still 95, no ghost order |
| 10 | Product > *Files*: upload a data sheet, then open it | "Documents live on the shop's own machine." | The file downloads with its content |
| 11 | Sign in as the **cashier** in a private window: find the product, sell one | "The cashier can sell." | A sale goes through |
| 12 | As the cashier open *Suppliers*, try *Receive stock*, try to add a product | "But they cannot see suppliers, add stock or change the catalogue -- the server refuses, not just the screen." | Permission messages; nothing changes |
| 13 | As the owner: from the *project* page open the application's card, then its *Business operations* section: show "Sell" granted, "Receive" not | "Selling and receiving are separate rights. The owner decides." | The grant list |
| 14 | Unplug the network (or show the offline test result) and repeat a sale | "None of this needs the internet." | It still works |
| 15 | Show the **backup list** and the recovery record | "Backed up every night. We destroyed a test system and rebuilt it from the backup files: same stock, same documents, same permissions, and it kept trading." | The drill summary (`RECOVERY_DRILL.md`) |

## Numbers you can quote (all measured, with the evidence in this repository)

* Tested with **5,000 products, 10,000 part numbers and 10,000 stock movements**: searching a part takes roughly a
  tenth of a second; recording a sale takes about a fifth of a second, a five-line sale about half a second.
* A test business was **backed up, the whole environment destroyed and rebuilt from the backup files**, and it
  came back identical -- 53 of 53 independent checks -- including files and the cashier's restrictions, then kept
  selling. Restoring the data from the backup files took under a minute.
* The screens pass an automated accessibility scan with **zero findings** and can be used with the keyboard alone.
* A running business was **upgraded to a newer application version** with local customizations, and nothing was lost
  (68 of 68 checks).

## What NOT to claim

Say these plainly if asked -- an investor who finds them later will not forgive them:

* The **Windows installer, automatic start after a reboot, and code signing have not been qualified** (no Windows
  test machine was available). The demo runs on the supported container runtime.
* **One application** is qualified for release: Spare Parts / Inventory & Sales. HR and School are experimental;
  six others exist as templates and are not offered. Library and Organization management do not exist yet.
* **Not built yet:** stock transfers, adjustments workflow, quotations, returns, full purchase-order lifecycle,
  reports, exploded parts diagrams. Purchasing is a simple "received" record.
* Backups are on the same computer unless the shop copies them elsewhere; that step is the shop's discipline.
* Access from other computers on the network exists but has **not** been qualified on a second machine.
* The automatic security scan of the running system (HawkScan) has **not** been run (no credential).
* No pilot has run in a real shop yet.

## Rules for the presenter (carried over from the earlier rehearsal plan)

* Use only the clearly fictional **Harmoney Auto Parts LLC -- DEMO** organization. Use original text documents and
  illustrations you own; do not show third-party catalogue images as licensed assets or invented numbers as OEM
  facts. Demo records are company-owned examples, separate from any reference data.
* Start from reproducible demo data. Write down the starting quantities. Use a fresh operation for each new
  transaction on stage; repeat an operation only when demonstrating a *retry* (the screens do this for you: a retry of
  a failed sale reuses its key and cannot sell twice).
* Never reset customer data, and never touch the Phase 8 Reference Apps organization.
* Describe LAN access accurately if it comes up: it is opt-in, and **not** qualified on a second machine.
* If a step is unreliable on the day, say so and skip it; do not improvise a claim. Development-phase completion is
  not release certification: the Windows installer, automatic start and signing remain disclosed commercial blockers.

(The previous version of this document was a rehearsal plan marked "not yet qualified"; it is in the git history.)

## Reset for the next demo

Create a new organization (a few minutes) or restore the demo backup. Never reuse a pilot's organization.
