# Chapter 6 — The shop kit: build, install, upgrade, operate — Backups on a shop PC

Topic for: software engineers. Source: IntraForge Engineering Handbook, Chapter 6 — The shop kit: build, install, upgrade, operate.

- In the app: nightly backups of the control database, the tenant database, object storage and configuration
  (02:00–02:50), all encrypted; a weekly restore test into a throw-away target; the Backups page shows the result.
- From the kit: a daily backup at 19:00 (a shop PC is often off at 02:00), "Backup to USB", a safety backup before
  every upgrade.
- A full recovery needs all four parts from the same day **and the original `.env`**.
