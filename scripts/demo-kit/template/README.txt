INTRAFORGE OFFLINE INVESTOR-DEMO KIT
====================================

What this is: a private business system running on THIS computer only, with a fictional auto-parts company already
in it. It needs no internet. It is a demonstration on the Docker runtime: the Windows installer, automatic start and
code signing are NOT part of this kit and have not been qualified.

WHAT THE COMPUTER NEEDS (install these BEFORE you go offline)
  * Windows 10/11, at least 8 GB of memory (close other programs), about 3 GB of free disk space.
  * Docker Desktop, installed, started, and showing "running". It is not part of this kit.
  * Chrome or Edge.

FIRST TIME (about 5 minutes; no internet needed)
  1. Copy this whole folder to the computer (for example C:\IntraForgeDemo) - or unpack the .zip package there.
     Optional check of the package: in PowerShell run  Get-FileHash IntraForge-Demo-Kit-*.zip  and compare it with the
     number in the .sha256 file next to it. (The installer also checks every file inside by itself.)
  2. Start Docker Desktop and wait until it says it is running.
  3. Right-click Install-IntraForgeDemo.ps1 > "Run with PowerShell".
     (If Windows blocks it: open PowerShell in this folder and run
      powershell -ExecutionPolicy Bypass -File .\Install-IntraForgeDemo.ps1 )
  4. When it says "IntraForge demo is ready", open https://localhost:8443
     The browser warns about the certificate: Advanced > continue. Logins: DEMO_LOGINS.txt.

EVERY DEMO AFTER THAT
  Start:  Start-IntraForgeDemo.ps1      Stop:  Stop-IntraForgeDemo.ps1 (data is kept)
  Back to the starting state (deletes what you entered): Reset-IntraForgeDemo.ps1   (do this before each demo)
  Remove the demo from this computer when you are done: Uninstall-IntraForgeDemo.ps1

THE DEMO SCRIPT: INVESTOR_DEMO_SCRIPT.md in this folder (15 steps). Start at step 5: the company is already set up
and the stock is 95. Read its sections "What NOT to claim" and "Rules for the presenter" once before the meeting.

IF SOMETHING GOES WRONG
  * "Docker is not running": start Docker Desktop and wait.
  * "Port 8443 is already used": run Install/Start with -Port 8453 and open https://localhost:8453 instead.
  * "does not match its checksum" or "is missing": the folder was damaged while copying; copy it again.
  * ".env is missing": the file .env holds the demo's keys and its name starts with a dot, so some copy tools and zip
    programs skip it. Copy the whole folder again. Never delete it: the demo data needs it.
  * Anything else: open PowerShell in this folder and run   docker compose logs backend

Everything here is fictional. Never put real business data in this demo, and do not send this folder to anyone: it
contains the demo's keys. This kit includes MinIO (AGPL-3.0); see IMAGES.txt.
