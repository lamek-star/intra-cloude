# IntraForge in my own spare-parts shop -- quickstart

For the first real use, on **one shop PC**, **with no internet**. You keep your **existing records** (paper, spreadsheet or
current software) as the record of truth while you use IntraForge alongside them; the pilot ends with a decision, not with
an automatic switch. The full pilot rules and checklists are in [LOCAL_EDITION_PILOT.md](LOCAL_EDITION_PILOT.md).

This guide is for the **shop kit 1.1** installer, `IntraForge-Setup-1.1.0.exe`. In this version **Spare Parts runs inside
IntraForge**: one sign-in, one set of users, one backup. Opening `http://127.0.0.1:3000` is no longer used.

## 1. Install (about 15-20 minutes, once)

You have **one file**, `IntraForge-Setup-1.1.0.exe` (on a USB drive formatted NTFS or exFAT). It contains IntraForge, the
Spare Parts application, Windows' WSL package and Docker Desktop, so a PC with nothing on it installs with **no internet**.

1. **Copy the file** to the shop PC and **double-click it.** Windows says "Unknown publisher" (not code-signed): **More info > Run
   anyway.** Read the "Checking this PC" block; every line should be `[OK]`. Press Enter.
2. Setup unpacks itself, then **switches on the Windows parts Docker needs**. Windows asks for administrator permission (**prompt 1**);
   answer Yes. Setup then asks to **restart the PC**; answer Y.
3. **Sign in again.** Setup continues by itself in a window: it installs WSL and Docker Desktop (administrator prompt **2**, about
   2 minutes), then IntraForge (2-3 minutes). At the end the **IntraForge Control Center** opens. (If Setup did not continue by
   itself, double-click the file again: it carries on from where it stopped.)
4. **Control Center > Settings > "Copy the keys file to a USB drive"** and keep that drive safe (not the one you keep backups on).
   Without the keys a backup cannot be read if the PC is lost.

There is now **one shortcut**, **IntraForge**, on the desktop and in the Start menu. It opens the Control Center. IntraForge
also appears in Windows **Settings > Apps > Installed apps** (its Uninstall opens the Control Center's removal options).

If a PC already has Docker Desktop, Setup skips those steps. If Setup shows a red `[X]` in the PC check (for example
virtualization switched off in the BIOS), it says how to fix it. The file is for your own PCs only (Docker Desktop's licence does
not allow passing it on).

**Upgrading from the earlier pilot installer** (`IntraForge-Setup-Complete.exe`): double-click the new file on the installed PC.
It finds the installation, takes a complete backup, installs the new version over it (keeping your data and keys) and checks
it is healthy; if anything fails it puts the previous version back by itself. The old desktop icons are replaced by the one
**IntraForge** shortcut. (The old demo Spare Parts at port 3000 kept its data in the browser only; there is nothing on the PC
to carry over from it.)

## 2. The Control Center

Double-click **IntraForge**. The Control Center opens straight away, even when Docker or IntraForge is not running, and
shows one status at the top:

| Status | Meaning | What to do |
|---|---|---|
| **Healthy** | everything runs | nothing |
| **Starting** | Docker or IntraForge is starting (1-2 minutes after Windows starts) | wait |
| **Degraded** | IntraForge answers but a part does not (listed in red) | **Restart services** |
| **Stopped** | not running | **Start** |
| **Failed** | started but not ready | **Restart services**; if it stays, **Diagnostics** |
| **Repair required** | the installation or Docker Desktop is missing | run the setup file again |

Below the status: your **applications** with an **Open** button, and each check (Docker, virtualization, disk, memory,
last backup) with what to do when it is not green. On the left: **Open IntraForge**, Start / Restart services / Stop,
Backup now, Backup to a folder / USB, Restore, Settings, Diagnostics and Uninstall.

The browser warns about the certificate the first time (it is this PC's own): **Advanced > continue**. Nothing is reachable from
other computers; the address is `https://localhost:8443` on this PC only.

## 3. First use: your shop

1. **Open IntraForge > Create account** -- the first account is your administrator. Use a strong password and write it down.
2. Create your **company** (organization).
3. **Apps > Install** Spare Parts, give it your shop's name. It shows **Running**. **Open** takes you straight into it, with no
   second sign-in.
4. In Spare Parts, **Shop settings**: address, currency, tax and document details.
5. Your staff: add them to the company in IntraForge (**Organization > Members**) and give each **one** Spare Parts role:
   *Spare Parts manager* (everything), *sales* (customers, quotations, orders, invoices, payments), *inventory* (products,
   stock, suppliers, purchase orders) or *viewer* (read only). People without a Spare Parts role do not see it in Apps. Signing out of
   IntraForge also signs them out of Spare Parts.

There is **no demo data** in your shop. Everything you enter is real.

## 4. Put your products and stock in -- the safe way

Stock is a **ledger**: it only changes through receiving, delivering and recorded corrections, never by typing a number.

1. **Reference Catalogue** (optional): **Import** your supplier's or manufacturer's parts list (CSV: match the columns, preview,
   import). Search finds a part however the number is typed (`11110-36F00`, `1111036f00`, ...). **IMPORT TO MY PRODUCTS** turns
   a catalogue part into one of your products.
2. **My Products**: your own part numbers (SKU), prices and photos. **Suppliers**: who you buy from, with their cost.
3. **Stock & Locations**: create your store (for example "Main store"), then receive the **opening stock** of each product
   (quantity = what is on the shelf, note **OPENING**).
4. **Count and compare**: the shelf count must equal the stock shown. Fix any difference *before* you rely on the numbers.

## 5. The daily work

- **A part arrives:** **Purchase Orders** (or **Stock & Locations > receive**) -- the stock goes up.
- **A customer asks:** add parts to an **enquiry** > **Create quotation** > **Issue to customer** (PDF) > **Customer accepted** >
  **Create order** > **Record delivery** (stock goes down) > **Invoice delivered items** > **Record payment**.
- **Reports** and the **Dashboard** show the day's sales and payments. **Audit log** (in Spare Parts, and in IntraForge's
  organization audit log) shows who did what.
- **End of day:** compare the day's sales and 5 fast-moving items with your existing records, write every difference in
  [pilot/PILOT_LOG.md](pilot/PILOT_LOG.md).

## 6. Backups

- **Automatic:** every day at 19:00 (and at the next start if the PC was off), plus a Sunday test that proves the backups can
  really be restored. The Control Center shows the age of the last complete backup and turns red if a backup failed.
- **What:** everything -- IntraForge's accounts and settings, the Spare Parts data (products, stock ledger, customers, documents,
  catalogue) and all stored files (photos, drawings, PDFs), in one set of three encrypted files: `control_db_*`, `tenant_db_*`,
  `object_storage_*` in `C:\IntraForgeData\backups`.
- **Every week (every day for a busy shop):** plug in a USB drive and press **Backup to a folder / USB**: it takes a fresh
  backup and copies it into `IntraForge-backups` on the drive. **A backup only on the shop PC's disk is not a backup.**
- **Kept:** the newest 30 of each kind stay on the PC; older ones are removed automatically.

## 7. Restart the PC

Restart Windows, sign in, wait 1-2 minutes (Docker Desktop and IntraForge start by themselves). Open **IntraForge**: the Control
Center shows **Starting**, then **Healthy**; your data is still there. **The first time, press Diagnostics after the restart and
keep the zip** -- a real restart of the shop PC is still to be recorded (see the pilot log).

## 8. Corrections and recovery

**A wrong receive or sale.** Nothing is deleted; the history stays complete. A stock difference is corrected with an
**adjustment** in **Stock & Locations** (a reason is required; manager or inventory role), and a sale with the documents' own
steps (cancel a quotation or order, record a return, void an invoice). Write every correction in the pilot log.

**Something is wrong with the data (same PC).** **Control Center > Restore**:
1. choose *Backups on this computer* or the USB drive;
2. **Check this backup** -- nothing changes yet: it opens every file, checks the checksums, shows when it was made, which
   applications and how many products / customers / invoices it holds, and whether this version can restore it;
3. type **RESTORE** and press **Restore**. A safety backup of the current data is taken first (so the restore itself can be
   undone), then the data is restored, updated to this version and checked.

**The PC is lost or rebuilt.** You need the **keys file** from your USB drive and the **backup files** (a new installation makes
new keys, which cannot read the old backups). In a command prompt, unpack the setup file without installing:
`IntraForge-Setup-1.1.0.exe /extractonly` (it unpacks to `C:\IntraForge`), then in PowerShell in `C:\IntraForge`
(E: = your USB drive):
`powershell -ExecutionPolicy Bypass -File .\Setup-IntraForge.ps1 -KeysFile E:\intraforge-keys.env -RestoreFrom E:\IntraForge-backups`
It prepares Windows and Docker as in section 1, then installs IntraForge with the shop's own keys and restores the backup.

**Going back to the previous version after an upgrade.** The upgrade keeps the previous program files in
`C:\IntraForge\.previous`, and the data stays compatible with it (this upgrade only adds). Control Center > Stop, copy the
contents of `.previous` back over `C:\IntraForge`, then Control Center > Start. If you also want the data as it was before the
upgrade, Restore the safety backup the upgrade took (the newest set from before the upgrade time). The earlier installer file
itself is kept as `IntraForge-Setup-Complete.exe` (do not delete it until the new version has run for a while).

## 9. If IntraForge does not start

1. Open the Control Center. It says what is wrong: Docker Desktop not running (press **Start**: it starts Docker Desktop too),
   virtualization off, WSL missing, too little disk or memory, a service down.
2. Press **Restart services**.
3. Still not **Healthy**: press **Diagnostics** and send the zip it saves on the desktop to the project team. It contains no
   passwords or keys.
4. If the keys file `.env` in `C:\IntraForge` was deleted, restore it from your USB copy (`intraforge-keys.env`, saved as `.env`).
   IntraForge cannot start without the same keys.

## Removing IntraForge

**Control Center > Uninstall** (or Windows **Installed apps > IntraForge > Uninstall**):

- **A. Remove, keep data** -- reinstalling brings the shop back as it was.
- **B. Back up, then remove** -- as A, with a fresh backup first.
- **C. Complete removal** -- a backup first (nothing is deleted if it fails), then the databases, stored files, images and program
  folder are deleted. You must type `DELETE-MY-SHOP-DATA`.

In every option the **backups**, the **keys** and the **logs** in `C:\IntraForgeData` are kept, and Docker Desktop stays
installed (other programs may use it).

## What is not covered (tell the staff)

No access from other computers (this PC only); no tax/accounting compliance. IntraForge starts when you **sign in to Windows**,
not at the login screen: sign in, or set Windows to sign in automatically if the PC should come up unattended.
