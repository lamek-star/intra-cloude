# Chapter 6 — The shop kit: build, install, upgrade, operate — Day-to-day scripts

Topic for: software engineers. Source: IntraForge Engineering Handbook, Chapter 6 — The shop kit: build, install, upgrade, operate.

| Script | What it does |
|---|---|
| `Start-IntraForgeShop.ps1` | Starts IntraForge and opens the browser; runs at sign-in (`-Auto` also takes a backup if the last is older than 20 h) |
| `Stop-IntraForgeShop.ps1` | Stops IntraForge; all data kept |
| `Status-IntraForgeShop.ps1` | Health summary, also saved to a file the project team can read |
| `Backup-IntraForgeShop.ps1` | Full backup (company data, business records, files) into the backups folder; `-Prune` keeps a bounded history |
| `Restore-IntraForgeShop.ps1` | **Destructive**: puts the shop back to a saved backup (needs the original keys file) |
| `Repair-IntraForgeBackups.ps1` | Fixes "pg_dump: Permission denied" backup folders |
| `Set-IntraForgeNetwork.ps1` | Lets other PCs in the shop open IntraForge (binds to the LAN address, firewall rule, shop names) or makes it this-PC-only again |
| `Uninstall-IntraForgeShop.ps1` | Removes IntraForge in one of three ways (keep data, keep backups only, remove everything) |
| `IntraForgeShop.Common.ps1` | Shared helpers, dot-sourced by the others (Windows PowerShell 5.1) |
