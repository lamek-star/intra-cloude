# Chapter 6 — The shop kit: build, install, upgrade, operate — Installing on a shop PC

Topic for: software engineers. Source: IntraForge Engineering Handbook, Chapter 6 — The shop kit: build, install, upgrade, operate.

`Setup-IntraForge.ps1` (run by the Setup window) does, in order: check the PC (Windows version, memory, disk,
virtualization) → switch on the Windows features Docker needs and restart (`Prepare-WindowsFeatures.ps1`) → install WSL
and Docker Desktop after checking their signatures (`Install-Prerequisites.ps1`) → `Install-IntraForgeShop.ps1`:

1. Check the kit is complete and unchanged (SHA-256).
2. Create the data folder (`C:\IntraForgeData`) and **fresh random secret keys** in `.env` (a copy goes to the data
   folder; the owner must keep a copy off the PC).
3. Load the images from the kit (no download).
4. Start the databases and storage; run migrations and `seed_permissions`.
5. Start IntraForge and wait until `/readyz` answers.
6. Register start at Windows sign-in (`HKCU\...\Run`), the daily backup task (19:00), desktop shortcuts and the
   Windows "Apps" uninstall entry.
