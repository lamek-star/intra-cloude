# IntraForge in my own spare-parts shop -- quickstart

For the first real use, on **one shop PC**, **with no internet**. You keep your **existing records** (paper, spreadsheet or
current software) as the record of truth while you use IntraForge alongside them; the pilot ends with a decision, not with
an automatic switch. The full pilot rules and checklists are in [LOCAL_EDITION_PILOT.md](LOCAL_EDITION_PILOT.md).

What you have is the **IntraForge Local Edition pilot kit** (a folder, or one `.zip`). It is *not* the Windows installer:
that has never been run on a real Windows PC and is not used here.

## 1. Install (about 15-20 minutes, once)

You have **one file**, `IntraForge-Setup-Complete.exe` (about 1.4 GB, on a USB drive formatted NTFS or exFAT). It contains IntraForge,
Windows' WSL package and Docker Desktop, so a PC with nothing on it installs with **no internet**.

1. **Copy the file** to the shop PC and **double-click it.** Windows says "Unknown publisher" (not code-signed): **More info > Run
   anyway.** Read the "Checking this PC" block; every line should be `[OK]`. Press Enter.
2. Setup unpacks itself, then **switches on the Windows parts Docker needs**. Windows asks for administrator permission (**prompt 1**);
   answer Yes. Setup then asks to **restart the PC**; answer Y.
3. **Sign in again.** Setup continues by itself in a window: it installs WSL and Docker Desktop (administrator prompt **2**, about
   2 minutes), then IntraForge (2-3 minutes). It ends with "IntraForge is installed and running". (If it did not start by itself,
   double-click the file again: it carries on from where it stopped.)
4. **Copy `C:\IntraForgeData\keys\intraforge-keys.env` to a USB drive** and keep it safe (a different drive from your backups).
   Without it a backup cannot be read if the PC is lost.

If a PC already has Docker Desktop, Setup skips those steps. Running the file again on an installed PC changes nothing; it only starts
and opens IntraForge. If Setup shows a red `[X]` in the PC check (for example virtualization switched off in the BIOS), it says how to
fix it. The file is for your own PCs only (Docker Desktop's licence does not allow passing it on). See
[pilot/TEST_ON_ANOTHER_PC.md](pilot/TEST_ON_ANOTHER_PC.md) for a step-by-step test on a new PC.

## 2. Start and open IntraForge

When the installation finishes, your browser opens the **Spare Parts application** at `http://127.0.0.1:3000/` (press **Enter demo workspace**).
The desktop has two icons: **Open Spare Parts** (that address) and **Open IntraForge** (`https://localhost:8443`). They are two different
programs (see [HOW_INTRAFORGE_WORKS.md](HOW_INTRAFORGE_WORKS.md) section 8b): the Spare Parts application keeps its data **in that browser**
(it is not part of the IntraForge backups), IntraForge's own Spare Parts / Inventory & Sales is described below.

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
- **Every week (or every day for a busy shop):** plug in a USB drive (or use another disk) and double-click
  **IntraForge Backup to USB**: it takes a fresh backup and asks where to copy it. **A backup only on the shop PC's disk is
  not a backup.** (By hand: copy the newest three files from `C:\IntraForgeDataackups`.)
- **Kept:** the newest 30 of each kind stay on the PC; older ones are removed automatically.
- **Check:** **IntraForge Status** shows the age of the last complete backup and warns if it is more than a day old.

## 7. Restart the PC

Restart Windows, sign in, wait 1-2 minutes (Docker Desktop and IntraForge start by themselves; measured about 30 seconds
from a fully stopped Docker Desktop on the development PC). **Open IntraForge**: your data is still there. If it is not there after 5 minutes,
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
no edit/adjust screen for stock. IntraForge starts when you **sign in to Windows** (its sign-in entry starts Docker Desktop first), not at the
login screen: sign in, or set Windows to sign in automatically if the PC should come up unattended.
