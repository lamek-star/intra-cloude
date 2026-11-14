# Chapter 6 — The shop kit: build, install, upgrade, operate — Upgrading

Topic for: software engineers. Source: IntraForge Engineering Handbook, Chapter 6 — The shop kit: build, install, upgrade, operate.

`IntraForge-Setup-<new>.exe /quiet "/dir=C:\IntraForge"` (or double-click) runs `Upgrade-IntraForgeShop.ps1`:

1. **Safety backup of everything** with the installed version.
2. Keep the previous program files in `.previous`.
3. Stop the previous version (data stays), install the new files, add any settings the new version needs to `.env`.
4. Load the new images, run migrations and update the applications.
5. Start the new version and wait for `/readyz`.
6. **If anything fails: automatic rollback** — the previous files and keys are put back and the previous version is
   started with the same data. This is why new columns need `db_default` (Chapter 2).

The media agent is stopped to replace its program and restarted afterwards, from the install folder (started from the
staging folder it would hold that folder open and block the next upgrade).
