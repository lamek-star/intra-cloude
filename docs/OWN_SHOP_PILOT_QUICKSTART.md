# IntraForge in my own spare-parts shop -- quickstart

For the first real use, on **one shop PC**, **with no internet**. You keep your **existing records** (paper, spreadsheet or
current software) as the record of truth while you use IntraForge alongside them; the pilot ends with a decision, not with
an automatic switch. The full pilot rules and checklists are in [LOCAL_EDITION_PILOT.md](LOCAL_EDITION_PILOT.md).

What you have is the **IntraForge Local Edition pilot kit** (a folder, or one `.zip`). It is *not* the Windows installer:
that has never been run on a real Windows PC and is not used here.

## 1. Install (about 15 minutes, once)

**Prepare (needs internet once, on any PC):**

1. Download **Docker Desktop for Windows** (`Docker Desktop Installer.exe`) from docker.com and copy it to the shop PC on a
   USB drive. (It is free for a small shop. It is not part of the kit because its licence does not allow that.)
2. On the shop PC: run the Docker installer (leave "Use WSL 2" ticked), restart Windows if it asks, open Docker Desktop
   once and accept its terms until it says **Engine running**. Then *Settings > General* and tick **Start Docker Desktop
   when you sign in to your computer**.

**Install IntraForge (no internet needed):**

3. Copy the kit folder to the shop PC (for example `C:\IntraForge`) and keep it there.
4. Right-click **`Install-IntraForgeShop.ps1`** > **Run with PowerShell**. (If Windows blocks it, open PowerShell in the folder
   and run `powershell -ExecutionPolicy Bypass -File .\Install-IntraForgeShop.ps1`.) It checks the PC, verifies every file,
   creates the shop's own secret keys, starts IntraForge and sets up automatic start, a daily backup and shortcuts.
5. **Copy `C:\IntraForgeData\keys\intraforge-keys.env` to a USB drive** and keep it safe (a different drive from your
   backups). Without it a backup cannot be read if the PC is lost.

## 2. Start and open IntraForge

Sign in to Windows: IntraForge starts by itself (1-2 minutes). Double-click **Open IntraForge** on the desktop. The browser
warns about the certificate (it is this PC's own certificate): **Advanced > continue**. Nothing is reachable from other
computers; the address is `https://localhost:8443` on this PC only.

## 3. First use: your shop

1. **Create account** -- the first account is your administrator. Use a strong password and write it down somewhere safe.
2. Create your **company** (organization), then a workspace and a project when asked.
3. Open the **Application Gallery** and install **Spare Parts / Inventory & Sales**, then open it.
4. Create your staff accounts and give each **only** what they need (cashier: sell; receiver: receive), see the roles table
   in the pilot guide. The owner keeps the rest.

There is **no demo data** in your shop. Everything you enter is real.

## 4. Put your existing stock in -- the safe way

Never type a stock number directly: stock is a **ledger** and only changes through receiving and selling.

1. Add your **warehouse** (for example "Main"), your **suppliers** and a first set of **products** (start with the fast-moving
   parts, not the whole catalogue). Each product has your part number; searching finds it however it is typed
   (`04465-0K290`, `044650k290`, ...).
2. For each product enter its **opening stock as one Receive**: supplier "OPENING STOCK" (create it once), quantity = what is on
   the shelf, reference **OPENING**.
3. **Count and compare:** for every product you entered, the shelf count must equal the IntraForge stock. Fix any difference
   *before* you rely on the numbers (see Corrections).

## 5. The daily work

- **A part arrives:** search the part number > (create the product if it is new) > **Receive** > supplier, quantity > save.
  The stock goes up.
- **A customer buys:** search the part number > **Sell** > customer (if needed), quantity > save. The stock goes down and a
  **sales document** is created. Find it in the application's **Sales** list.
- **Files** (for example a supplier price list): open the application's file area, add the file, download it again to check.
- **End of day:** compare the day's sales and 5 fast-moving items with your existing records, write every difference in
  [pilot/PILOT_LOG.md](pilot/PILOT_LOG.md), then **IntraForge Backup Now**.

## 6. Backups

- **Automatic:** every day at 19:00 (and after a missed start), plus a Sunday test that proves the backups can really be
  restored. The window shows the result; the folder also holds `LATEST-BACKUP.txt` (when, what) or `BACKUP-FAILED.txt`.
- **Where:** `C:\IntraForgeData\backups`. Files are named `control_db_*`, `tenant_db_*`, `object_storage_*` with the date and
  time, and are encrypted.
- **Every week (or every day for a busy shop):** copy the newest three files to a USB drive or another disk. Easiest: run
  `Backup-IntraForgeShop.ps1 -CopyTo E:\IntraForge-backups` (E: = the USB drive). **A backup only on the shop PC's disk is not
  a backup.**
- **Kept:** the newest 30 of each kind stay on the PC; older ones are removed automatically.
- **Check:** **IntraForge Status** shows the age of the last complete backup and warns if it is more than a day old.

## 7. Restart the PC

Restart Windows, sign in, wait 1-2 minutes. **Open IntraForge**: your data is still there. If it is not there after 5 minutes,
see section 9. **The first time you do this, run "IntraForge Status" after the restart and keep the result** -- this is the
test the project team has not been able to run on a real Windows PC.

## 8. Corrections and recovery

**A wrong receive or sale.** Nothing is edited or deleted, and there is no "adjust stock" screen in this release. Write it in
the pilot log (what was entered, what it should have been) and tell the project team: a correcting stock movement is
recorded with the owner's *adjust* authority, and the history stays complete. Do not give staff broader access to work
around it.

**Something is wrong with the data (same PC).** Run `Restore-IntraForgeShop.ps1`: it shows which backup it will use and what
will be lost, takes a safety backup of the current state first, asks you to type `RESTORE`, then restores and checks.

**The PC is lost or rebuilt.** Install Docker Desktop, copy the kit, plug in the USB drive with `intraforge-keys.env` and the
backup files, then:
`powershell -ExecutionPolicy Bypass -File .\Install-IntraForgeShop.ps1 -KeysFile E:\intraforge-keys.env -RestoreFrom E:\IntraForge-backups`

## 9. If IntraForge does not start

1. Open Docker Desktop and wait until it says **Engine running**; then double-click **Open IntraForge**.
2. Double-click **IntraForge Status**. Read it; it says what is wrong (Docker down, keys missing, not ready, old backup).
3. Send the newest file in `C:\IntraForgeData\logs` (status-*.txt), plus `shop.log`, to the project team. They contain no
   passwords or keys.
4. If the keys file `.env` in the IntraForge folder was deleted, restore it from your USB copy (`intraforge-keys.env`, saved
   as `.env`). IntraForge cannot start without the same keys.

## What is not covered (tell the staff)

No transfers between warehouses, returns, quotations, reports, or tax/accounting compliance; no access from other computers;
no edit/adjust screen for stock. Windows automatic start relies on Docker Desktop starting at sign-in: **the PC must be
signed in** (set Windows to sign in automatically if the PC should come up unattended).
