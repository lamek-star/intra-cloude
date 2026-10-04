INTRAFORGE LOCAL EDITION - SHOP KIT
===================================

A private system for the shop -- people, files, and the Spare Parts / Inventory & Sales application -- that runs on THIS
PC (and, if you switch it on, the shop's other PCs over the shop's own network) and needs no internet. Read OWN_SHOP_PILOT_QUICKSTART.md (in this folder) for the daily steps and checklists.

WHAT IS IN THE KIT
  IntraForgeControlCenter.exe (the Control Center), the Setup / Install / Start / Stop / Backup / Restore / Status / Upgrade /
  Uninstall scripts (.ps1) it uses, the program itself (images\), the list of every part with checksums
  (OFFLINE_MANIFEST.txt) and the guides. It contains no secrets and no demo data.

INSTALL
  Normally: double-click the IntraForge setup file (IntraForge-Setup-<version>.exe). It prepares Windows, installs Docker
  Desktop and IntraForge from the file itself, and restarts the PC when Windows needs it (sign in again: it carries on).
  From this folder instead: right-click Setup-IntraForge.ps1 > "Run with PowerShell".
  When it is done there is ONE shortcut, "IntraForge", on the Desktop and in the Start menu.
  THEN, ONCE: Control Center > Settings > "Copy the keys file to a USB drive". A backup cannot be read without it.

FIRST USE
  "IntraForge" shortcut > Open IntraForge > "Create account" (the first account is your administrator) > create your
  company > Apps > install "Spare Parts". Open it from Apps (or from the Control Center). The browser warns about the
  certificate the first time (it is this PC's own): Advanced > continue.

THE CONTROL CENTER (the "IntraForge" shortcut)
  Opens even when IntraForge or Docker is not running -- it is where you fix things.
  Status       Healthy / Starting / Degraded / Stopped / Failed / Repair required, with each check and what to do.
  Open         IntraForge, and each installed application.
  Start / Stop / Restart services.
  Backup now, Backup to a folder / USB, and Restore (checks the backup and shows what it holds before anything changes;
               takes a safety backup of the current data first).
  Settings     start with Windows, copy the keys file, where everything is, and Shop network (let the shop's other
               PCs in, over the shop's own Private network only; or back to this computer only).
  Upgrade      when a newer IntraForge-Setup-<version>.exe is in Downloads, on the Desktop or in
               C:\IntraForgeData\updates, an "Upgrade to <version>..." button appears.
  Diagnostics  a zip for support (no passwords or keys in it).
  Uninstall    A: remove, keep data   B: back up, then remove   C: complete removal (backup first; also deletes the data).
               Backups, the keys file and logs are never deleted.

EVERY DAY
  Sign in to Windows: IntraForge starts by itself (about 1-2 minutes).
  A backup runs every day at 19:00 (or at the next start if the PC was off). Copy it to a USB drive regularly:
  Control Center > Backup to a folder / USB.

WHERE THINGS ARE
  This folder (C:\IntraForge)        the program (contains the keys file .env - never delete it)
  C:\IntraForgeData\backups          every backup (encrypted); LATEST-BACKUP.txt says when and what
  C:\IntraForgeData\keys             a copy of the keys file - copy it to a USB drive
  C:\IntraForgeData\logs             setup, backup, shop and status logs
  Your shop's records and files      stored by Docker Desktop; the BACKUPS are your safety net

UPGRADING
  Put the newer setup file in Downloads (or on the Desktop) and press "Upgrade to <version>..." in the Control Center, or
  run the file yourself. It shows the installed and the new version and asks "Upgrade now? Type Y" -- nothing changes before
  you answer. It takes a safety backup, keeps your data, keys and shop-network setting, and puts the previous version back by
  itself if the upgrade fails. An older setup file is refused. See the quickstart for going back to an older version by hand.

THE SHOP'S OTHER PCS (optional)
  Control Center > Settings > Shop network > "Allow other PCs in this shop...". Only on the shop's own network marked Private
  in Windows; public networks are blocked by the Windows Firewall; nothing is opened to the internet. Then, on each staff PC
  once: run C:\IntraForgeData\shop-network\Trust-IntraForge-on-this-PC.cmd (copy the folder on a USB drive) and open the
  address it shows. Everyone signs in with their own account.

RECOVERY ON A NEW OR REBUILT PC
  The backups can only be read with the shop's OWN keys file, so the installation must start from it (a new installation
  makes new keys). Unpack the kit to C:\IntraForge, then in PowerShell in that folder (E: = the USB drive):
    powershell -ExecutionPolicy Bypass -File .\Install-IntraForgeShop.ps1 -KeysFile E:\intraforge-keys.env -RestoreFrom E:\IntraForge-backups
  (On a PC without Docker Desktop yet, run the setup file first, then Control Center > Uninstall > option C, then the line above.)

Everything in this kit is unsigned (Windows shows "Unknown publisher"). MinIO, which stores your files, is AGPL-3.0
licensed: fine for your own shop; see THIRD_PARTY_LICENSES.md before giving IntraForge to anyone else.
