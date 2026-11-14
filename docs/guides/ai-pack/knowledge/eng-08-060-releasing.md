# Chapter 8 — Working on IntraForge: setup, tests, release — Releasing

Topic for: software engineers. Source: IntraForge Engineering Handbook, Chapter 8 — Working on IntraForge: setup, tests, release.

1. Run every test and both dependency audits; fix or record anything high.
2. Commit everything — the kit is built from `HEAD` only.
3. Build the images for any changed service app (Pay, Spare Parts) from their committed revisions.
4. Build the kit and the Setup exe (Chapter 6), with a new `KIT_VERSION`.
5. Install it on a clean test copy and upgrade an existing test copy; check `/readyz`, a sale, a backup and a restore
   test.
6. Upgrade the pilot shop with the Setup exe; confirm the status file and the Backups page afterwards.
7. Record the release in `replica/build-log.md` and the checkpoint docs.
