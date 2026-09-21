INTRAFORGE LOCAL EDITION v1.0 - OWN-SHOP PILOT KIT
==================================================

A private stock-and-sales system that runs on THIS shop PC only and needs no internet. This is a controlled pilot:
keep your existing records (paper / spreadsheet / current software) as the record of truth while you use it.
Read OWN_SHOP_PILOT_QUICKSTART.md (in this folder) for the daily steps and the checklists.

WHAT IS IN THE KIT
  Install / Start / Stop / Backup / Restore / Status / Uninstall scripts (.ps1), the program itself (images\), the list
  of every part with checksums (OFFLINE_MANIFEST.txt), and the guides. It contains no secrets and no demo data.

BEFORE YOU START (once; needs internet only for Docker Desktop, on any PC)
  1. Windows 10 (22H2) or Windows 11, 64-bit; 8 GB memory or more; 10 GB free disk; virtualization switched on in the
     BIOS (it usually is).
  2. Docker Desktop for Windows. It is NOT in this kit. On any connected PC download "Docker Desktop Installer.exe" from
     docker.com, copy it to this PC, run it (accept "Use WSL 2"), restart Windows if it asks, then open Docker Desktop
     once and accept its terms until it says "Engine running".
     (Optional: Docker Desktop > Settings > General > "Start Docker Desktop when you sign in". Not required: IntraForge's own
     sign-in entry starts Docker Desktop by itself.)
     (Version this kit was tested with: see OFFLINE_MANIFEST.txt.)
  3. Copy this whole folder to the PC, for example C:\IntraForge (or unpack the .zip there). Keep it there.

INSTALL (about 3 minutes, no internet needed)
  Right-click Install-IntraForgeShop.ps1 > "Run with PowerShell".
  (If Windows blocks it: open PowerShell in this folder and run
   powershell -ExecutionPolicy Bypass -File .\Install-IntraForgeShop.ps1 )
  It checks the PC, verifies the kit, creates this shop's own secret keys, starts IntraForge, and sets up: start at Windows
  sign-in, a daily backup at 19:00, and three desktop shortcuts.
  THEN, ONCE: copy C:\IntraForgeData\keys\intraforge-keys.env to a USB drive and keep it safe. A backup cannot be read
  without it.

FIRST USE
  Double-click "Open IntraForge" > "Create account" (the first account is your administrator) > create your company >
  Application Gallery > install "Spare Parts / Inventory & Sales". The browser warns about the certificate (it is this PC's
  own): Advanced > continue.

EVERY DAY
  Sign in to Windows: IntraForge starts by itself (about 1-2 minutes). "Open IntraForge" opens it.
  End of day: "IntraForge Backup Now", then copy the newest backup to a USB drive (see the quickstart).
  "IntraForge Status" shows whether everything is healthy, and when the last backup was made.

WHERE THINGS ARE
  This folder (C:\IntraForge)        the program (can be replaced; contains the keys file .env - never delete it)
  C:\IntraForgeData\backups          every backup (encrypted); LATEST-BACKUP.txt says when and what
  C:\IntraForgeData\keys             a copy of the keys file - copy it to a USB drive
  C:\IntraForgeData\logs             backup.log, shop.log, status reports (send these to the project team when asked)
  Your shop's records and files      stored by Docker Desktop; the BACKUPS are your safety net

IF INTRAFORGE DOES NOT START
  1. Is Docker Desktop running? Open it and wait for "Engine running". Then double-click "Open IntraForge".
  2. Double-click "IntraForge Status" and read it. Send the saved status file (C:\IntraForgeData\logs) to the project team.

RECOVERY
  Same PC, something wrong with the data: Restore-IntraForgeShop.ps1 (asks you to confirm; takes a safety backup first).
  New or rebuilt PC: install Docker Desktop, copy this kit, then
    powershell -ExecutionPolicy Bypass -File .\Install-IntraForgeShop.ps1 -KeysFile E:\intraforge-keys.env -RestoreFrom E:\backups
  (E: = your USB drive with the saved keys file and the backup files).

Everything in this kit is unsigned (Windows may show a warning for the scripts). MinIO, which stores your files, is AGPL-3.0
licensed: fine for your own shop; see THIRD_PARTY_LICENSES.md before giving IntraForge to anyone else.
