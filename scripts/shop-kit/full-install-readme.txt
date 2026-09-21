INTRAFORGE - FULL INSTALL (own-shop pilot)
==========================================

This folder is everything needed to put IntraForge on one shop PC. No internet is needed on that PC.

  IntraForge-Setup.exe                     the installer (one file, contains the whole program)
  prerequisites\Docker Desktop Installer.exe   Docker Desktop, which IntraForge runs on (only used if the PC does not have it)
  CHECKSUMS.txt                            what each file should be, to check that copying did not damage it

HOW TO INSTALL
  1. Copy this whole folder to the shop PC (for example on a USB drive).
  2. Double-click  IntraForge-Setup.exe
     Windows may say "Windows protected your PC - Unknown publisher" (the installer is not code-signed).
     Click "More info", then "Run anyway".
  3. Press Enter when Setup asks. It checks itself, unpacks, and looks for Docker Desktop.
     - If Docker Desktop is missing, Setup offers to run its installer: say yes, allow the administrator permission, keep
       "Use WSL 2" ticked, and finish it. If Docker asks to restart Windows, restart, open Docker Desktop once until it says
       "Engine running", then double-click IntraForge-Setup.exe again: it carries on from where it stopped.
  4. Setup installs IntraForge (about 2 minutes) and opens it in your browser (accept the certificate warning: Advanced,
     then continue). Create your account: the first account is the administrator.
  5. IMPORTANT, once: copy  C:\IntraForgeData\keys\intraforge-keys.env  to a USB drive and keep it safe. Without it, a
     backup cannot be read if the PC is lost.

AFTER THAT
  The desktop has "Open IntraForge", "IntraForge Backup Now", "IntraForge Backup to USB" and "IntraForge Status".
  IntraForge starts by itself when you sign in to Windows and backs up every day at 19:00.
  Running IntraForge-Setup.exe again on an installed PC changes nothing: it only starts and opens IntraForge.
  Read OWN_SHOP_PILOT_QUICKSTART.md (installed in C:\IntraForge) for the daily routine, backups and recovery.

THE FIRST RESTART TEST (please do it and keep the result)
  Restart Windows, sign in, wait 2 minutes, double-click "Open IntraForge": your data must still be there. Then double-click
  "IntraForge Status" and keep the saved file (in C:\IntraForgeData\logs). This is the one test that could not be run on the
  development PC.

Not signed, not for distribution: this is a controlled pilot build for one shop. MinIO (inside) is AGPL-3.0; Docker Desktop is
subject to Docker's own licence (free for a small business): do not pass either around.
