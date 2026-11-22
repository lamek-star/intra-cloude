# Chapter 6 — The shop kit: build, install, upgrade, operate — The Control Center (`control-center/`)

Topic for: software engineers. Source: IntraForge Engineering Handbook, Chapter 6 — The shop kit: build, install, upgrade, operate.

A native Windows program (C# 5, WinForms, GDI+ drawing in the DESIGN.md style — `Ui.cs`). It reads the installed kit's
`.env` for the port and data folder, shows status, starts and stops, backs up and restores, manages the shop network,
the media agent and the licence code, and collects diagnostics. `INTRAFORGE_CC_RENDER_UI=<folder>` renders every screen
to PNG files without changing anything (used for the guide screenshots).
