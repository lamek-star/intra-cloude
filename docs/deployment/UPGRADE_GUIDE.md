# Upgrade Guide

How to move an existing IntraForge deployment to a newer version.
Written for the Internal Pilot v0.9 mandate
(`docs/implementation/RELEASE_READINESS.md`) as the "internal
operational documentation" its priority list calls for. **Always take
a verified backup before upgrading** — see
`docs/operations/BACKUP_RESTORE.md`. This is a procedure, not a
tested-end-to-end report: v0.9 is this project's first internal
release, so there is no prior version to have actually upgraded from
yet. Each section says plainly what's real/designed vs. what's still
open, per this repo's own evidence-based documentation convention.

## 1. Linux / plain Docker Compose path

This is the path that's actually exercisable today, since it's the
same bring-up sequence `docs/deployment/LOCAL_DEPLOYMENT.md` Section 4
already runs and verifies — an upgrade is that sequence's build/
migrate/restart steps run again against newer code, not a new
mechanism.

1. **Back up first.** `manage.py run_backup` for control_db, tenant_db,
   and object_storage (or trigger the same through the scheduled
   Celery Beat job if you'd rather wait for the next automated cycle)
   — see `docs/operations/BACKUP_RESTORE.md` Section 4.
2. Pull/checkout the new version's source.
3. `docker compose build` — rebuilds `pdc-backend:latest` (shared by
   backend/worker/beat, per `docker-compose.yml`'s own comment on why
   that tag is shared) and the frontend image from the new source.
4. Review the new version's migrations before applying them (`manage.py
   showmigrations`, `manage.py sqlmigrate <app> <migration>` for
   anything that looks non-trivial) — CLAUDE.md's "no unreviewed
   dynamic SQL" principle extends to not blindly trusting a migration
   file you haven't looked at, even one this project's own tooling
   generated.
5. Stop the app tier so migrations don't race a running request:
   `docker compose stop backend worker beat frontend`.
6. `docker compose run --rm backend python manage.py migrate`
7. `docker compose run --rm backend python manage.py seed_permissions`
   — re-run on every upgrade that changes the permission catalog (a
   real gotcha this project already hit once — see
   `docs/implementation/RELEASE_READINESS.md`'s `workspace.manage`
   entry: an already-running deployment needed this re-run to pick up
   a new role-permission grant).
8. `docker compose up -d backend worker beat frontend proxy`
9. Check `/readyz` and spot-check the UI before considering the
   upgrade complete.

**Rollback:** if step 6 or later goes wrong, restore the pre-upgrade
backup taken in step 1 (`manage.py restore_backup <record_id> --yes`,
`docs/operations/BACKUP_RESTORE.md` Section 7a) rather than attempting
to hand-reverse a partially-applied migration.

## 2. Windows/WSL2 appliance path

Two genuinely separate things can be upgraded here, per ADR-0012's own
design — conflating them is the most likely real-world mistake:

### 2a. The Control Center application itself

The WiX MSI (`installer/wix/Package.wxs`) declares a real
`MajorUpgrade` element with a fixed `UpgradeCode`, which is how Windows
Installer recognizes "this is a newer version of something already
installed" and performs an in-place upgrade rather than a side-by-side
install. Per `docs/deployment/WINDOWS_QUALIFICATION_MATRIX.md` Section
6 (written, not yet executed — see blocker 1 below): installing a
newer-versioned MSI over an older one should remove the old version and
install the new one cleanly, and — **by the Phase 19 design decision —
the MSI only manages the Control Center's own application files**. It
does not touch the running WSL2 distro, its data, or
`control-center-settings.json`, which is expected to survive unchanged.

**Not yet verified by an actual run** (needs the same disposable-VM
authorization as the rest of `WINDOWS_QUALIFICATION_MATRIX.md` — see
`RELEASE_READINESS.md` blocker 1): a real "install v0.9, then install
v0.9.1 over it" cycle has never been executed. Treat this section as
designed-and-reasoned, not proven, until that run happens.

### 2b. The appliance's application content (the WSL2 distro itself)

This is a genuinely open item, not a solved problem being merely
under-documented — stated plainly rather than glossed over. ADR-0013
made a deliberate, explicit tradeoff: Docker Engine is baked into the
WSL2 rootfs at release-build time and is "release-pinned, not
live-patched inside an installed appliance." The same is true, by
extension, of everything else in that rootfs. There is currently:

- No in-place "pull new container images into an already-provisioned
  distro" mechanism, tested or otherwise.
- No documented or built process for swapping an installed distro's
  rootfs for a newer release's rootfs while preserving the named Docker
  volumes (`pdc_backups` and friends) that hold real customer data —
  `Uninstall-IntraCloudDistro.ps1`'s own pre-removal-backup logic (see
  `RELEASE_READINESS.md` item 15) is the closest existing building
  block, but a full "upgrade the appliance in place" script does not
  exist yet.

**What this means practically for v0.9**: until this is designed and
built, treat an appliance-content upgrade the same way a from-scratch
install is treated — take a full backup (`docs/operations/
BACKUP_RESTORE.md`), and be prepared to reprovision (`Uninstall` with
`-BackupDestination`, then `Import`/`Initialize` the new rootfs,
then `restore_backup` the data back in) rather than expecting an
automated in-place path. This is not a recommendation to build that
automation reflexively — per CLAUDE.md's "When Uncertain" rule, a real
in-place appliance-upgrade mechanism that preserves live customer data
correctly is exactly the kind of thing that deserves its own ADR and
deliberate design (rollback behavior on a failed mid-upgrade state,
in particular), not something to improvise inside a documentation pass.
Flagged here as this guide's most important open item, not silently
assumed solved by section 2a's MSI upgrade path.

## 3. Version compatibility

No version-skip policy exists yet (e.g., "can you go from v0.9 directly
to v1.1, or must you pass through v1.0's migrations first?") — with
only one release so far, there is nothing to have a policy about yet.
Revisit this section once a second version actually ships.

## Open items

- The appliance-content upgrade mechanism (Section 2b) — real design
  work, not yet started.
- A real MSI-over-MSI upgrade run (Section 2a) — blocked on the same
  disposable-VM authorization as the rest of the qualification matrix.
- No automated test exercises the Linux/Compose upgrade sequence in
  Section 1 end-to-end today (it's the same steps
  `LOCAL_DEPLOYMENT.md` already verifies individually, but the
  specific "upgrade an existing populated deployment" scenario, with
  real pre-existing data, has not been run as its own drill).
