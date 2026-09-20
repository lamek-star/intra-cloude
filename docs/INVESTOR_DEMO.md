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

## The offline demo kit (recommended for a laptop with no internet)

A ready-made folder that installs the whole demo, with the fictional company already set up, on a laptop **with no
internet**. It is the qualified Docker runtime, **not** the Windows installer (which is not qualified).

**Build it once, online, on the build machine:**

```bash
scripts/demo-kit/build-demo-kit.sh <output-folder> [rehearsal-port]
```

It builds the two IntraForge images from the current source, creates the demo business through the real screens inside a
clean copy of the kit's own stack (its own project, images, volumes and port -- it never touches any other stack), backs
it up (encrypted, control database + business data + files), exports all six images to one file, generates a fresh `.env`
with random secrets, and writes `DEMO_LOGINS.txt`, `IMAGES.txt` and a one-page `README.txt`. About 600 MB.

**On the demo laptop (before going offline):** Docker Desktop installed and showing *running* (it is **not** in the kit;
its installer is a separate download), WSL2 enabled, Chrome or Edge, and enough memory: the demo's containers use about
**1 GB** when idle (measured), so an 8 GB laptop should be comfortable -- *not tested on a small laptop*. Then:

1. Copy the whole folder (it contains a **hidden** `.env`; the installer stops with a clear message if it is missing).
2. Run `Install-IntraForgeDemo.ps1` (about 1.5 minutes): loads the images from the file, prepares a clean system, restores
   the three backup files, starts everything, and prints `https://localhost:8443`. Accept the certificate warning.
3. `Start-IntraForgeDemo.ps1` / `Stop-IntraForgeDemo.ps1` later (data kept); **`Reset-IntraForgeDemo.ps1`** puts the demo
   back to the starting state after you have entered things (about 1.5 minutes; it deletes only the demo's own volumes).

**Starting state:** owner `owner@harmoney-demo.example` and cashier `cashier@harmoney-demo.example` (password in
`DEMO_LOGINS.txt`); Harmoney Auto Parts LLC -- DEMO with Demo Oil Filter (part number `04465-0K290`), Demo Supplier A, Main
Warehouse, Demo Retail Customer, **95 on hand** (received 100, sold 5), one sales document, one stored data sheet.
**With the kit, start the script at step 5** (search): steps 1-4 are already done. Then do steps 5-15 live; for step 6/7
receive and sell a small extra quantity (95 becomes, for example, 115 then 112) and use Reset afterwards.

**What was rehearsed (2026-09-20), on this Windows machine, from a copy of the kit in a different folder, with Windows
PowerShell 5.1 (what a stock laptop has):** install in 84 s with the images loaded from the kit's file and all three
backups restored; a browser check as both demo users -- search, stock 95, exactly 2 movements, the sales document, the stored
file's bytes, the cashier's refusals -- and then a **live sale by the cashier and a live receive by the owner**: 3/3;
Stop then Start (data kept); Reset in 91 s back to exactly 95 on hand and 2 movements with the same record ids. The
containers have **no route to the internet** (the demo network is internal-only; only the proxy is published, on loopback),
so the demo cannot depend on it, and the primary IntraForge stack was untouched throughout.

**What was not proven:** a second, clean computer (the base images -- PostgreSQL, Valkey, MinIO, Caddy -- already existed on
this machine when loaded, so loading them "from nothing" was not exercised, although the command is the same); a laptop
without Docker Desktop preinstalled (it cannot be installed offline from this kit); a small-memory laptop; browsers other than
Chromium; cutting the laptop's own Wi-Fi (the containers cannot reach the internet, but the operating system's network was not
switched off). Rehearse once on the real laptop before the meeting.

**Handling:** the folder holds secrets (`.env`) and a shared demo password; it is fictional data on one computer. Do not put
real business data in it, do not send the folder around, and delete it afterwards. It ships MinIO (AGPL-3.0, unpinned
`latest`) -- fine for a private demonstration, but see [THIRD_PARTY_LICENSES.md](operations/THIRD_PARTY_LICENSES.md) before
giving it to anyone else.

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
