# Backup & Restore Strategy — Private Data Cloud

Status: IMPLEMENTED (Phase 11 — `pg_dump`/`pg_restore` automation and the
automated restoration test job described in Sections 6/7 are real,
scheduled via Celery Beat, and verified against the live Docker stack;
see `system/backups.py`, `system/tasks.py`, and
`docs/architecture/ROADMAP.md` Phase 11 for what was actually built and
how it was verified). Object storage replication/`mc mirror` (Section 2)
and off-host shipping (Section 4) remain deployment-time operator
responsibilities, not automated by the platform itself — see Section 9.
Last updated: 2026-08-09

## 1. Principle

**RAID/ZFS redundancy is not a backup.** It protects against disk failure,
not against accidental deletion, application bugs, ransomware, or operator
error. Backups are a separate, independently verified process, and a backup
strategy is not considered complete until restoration has actually been
tested — an untested backup is an assumption, not a guarantee.

## 2. What Must Be Backed Up

| Asset | Method | Frequency (target) | Notes |
|---|---|---|---|
| Control-plane PostgreSQL | `pg_dump` (logical) + WAL archiving (physical, once volume justifies it) | Nightly full + continuous WAL | Contains users, orgs, permissions, file/schema catalog, audit |
| Tenant PostgreSQL | `pg_dump` per schema/org or physical base backup + WAL | Nightly full + continuous WAL | Larger, may need physical backups (`pg_basebackup`) as data grows |
| Object storage | MinIO server-side replication or `mc mirror` to backup target | Continuous/near-continuous | Content-addressed/UUID keys make incremental sync efficient |
| Configuration | Version-controlled `.env.example`, compose files, infra-as-code | On every change (git) | Actual `.env` secrets excluded from git; backed up via the secrets mechanism below |
| Secrets (Django `SECRET_KEY`, credential-encryption key, DB passwords, object storage root keys) | Encrypted secret backup (e.g. age/gpg-encrypted archive) stored separately from the primary backup target | On rotation/change | Losing the credential-encryption key makes stored `ConnectedDatabase` credentials unrecoverable — treat its backup as highest priority |
| Audit logs | Included in control-plane DB backup; consider separate export/archive for long retention if compliance requires it | Nightly (bundled) | |

## 3. Retention (initial target, adjust per organizational policy)

- Daily backups retained 14 days.
- Weekly backups retained 8 weeks.
- Monthly backups retained 12 months.
- WAL archives retained long enough to cover the daily backup window
  (point-in-time recovery to any moment in the last 24–48h).

## 4. Off-Machine / Off-Host Backup

- Primary backup target: a secondary backup server or NAS on the same
  private network (per ARCHITECTURE.md Section 5), not the same physical
  disk pool as production.
- Recommended: at least one copy that is offline or on separate
  infrastructure from the production host, to survive a full host
  compromise or hardware loss (the "3-2-1" pattern: 3 copies, 2 media
  types, 1 off-site/offline).
- Local-first does not mean single-copy; it means the *primary* copy and
  normal operation don't depend on the internet — off-host backup can still
  be a second local machine.

## 5. Snapshot Strategy

Where the underlying storage supports it (ZFS, LVM), periodic filesystem
snapshots provide fast point-in-time recovery for accidental-deletion
scenarios and complement, but do not replace, `pg_dump`/object-storage
backups (snapshots are not portable off-host on their own without being
shipped elsewhere).

## 6. Restoration Procedure

Steps 2/3/7/8 below are implemented and automated (`system/backups.py`:
`run_backup`/`verify_backup_restorable`); steps 1/4/5/6 are deployment-
level operator responsibility, not something application code can safely
automate (see Section 9).

1. Provision a clean target environment (or a dedicated restore-test
   environment — never restore-test against production). **Implemented,
   scoped down for the automated job**: rather than a whole separate
   environment, `verify_backup_restorable` creates a throwaway, isolated
   database (`restore_test_<id>`) on the *same* Postgres server for each
   verification run and drops it immediately after — genuinely isolated
   from production data (a fresh database, not a copy touched by
   anything else), without needing a second environment for the
   automated check specifically. Full-environment restoration drills
   (rebuilding onto new/different hardware) remain a manual/operator
   exercise per Section 8.
2. Restore control-plane PostgreSQL from the chosen backup point. **Implemented** (`pg_restore`, custom-format dump).
3. Restore tenant PostgreSQL from the chosen backup point. **Implemented.**
4. Restore/replicate object storage data. Not automated by the platform — MinIO replication/`mc mirror` is an operator-configured, infrastructure-level concern (Section 9).
5. Restore configuration and secrets from the encrypted secret backup. Operator responsibility — secrets never pass through application code to be backed up by it (Section 2).
6. Bring the stack up pointed at restored data; run health checks. Use `/readyz` (Phase 1) — already checks exactly this (control-plane DB, tenant DB, Valkey reachability).
7. Run a scripted validation pass: can a known test user log in, can a
   known test file be downloaded and its checksum verified, can a known
   test table be queried and row counts compared against the pre-backup
   snapshot's recorded counts. **Implemented, scoped to what a restored
   database alone can prove**: the automated job queries known
   control-plane tables (`organizations_organization`, `accounts_user`,
   `permissions_permission`) or, for a tenant backup, the per-organization
   schema catalog — proving the restore is a real, structurally intact,
   *queryable* database, not exact-count comparison against a live
   database whose data keeps changing after the dump is taken. File-
   checksum and full end-to-end login checks would require also restoring
   object storage and standing up the whole application stack against the
   restored data — a heavier, environment-level drill (Section 8), not
   part of the lightweight, frequent automated check.
8. Record the restoration test result (`BackupRecord.verified_restorable`)
   with timestamp and outcome. **Implemented** — `verified_restorable`,
   `verified_at`, `verification_error`.

## 7. Automated Restoration Testing — IMPLEMENTED

`CELERY_BEAT_SCHEDULE` (`config/settings/base.py`) schedules
`system.tasks.verify_latest_backup_task` weekly for both the
control-plane and tenant backup types, restoring the latest successful
backup of each into an isolated database and running the Section 6
validation pass automatically — the concrete mechanism that satisfies "a
backup strategy is not complete until restoration is tested." Manual
triggers also exist (`python manage.py verify_backup <control_db|
tenant_db>`) for ops use outside the schedule. Verified for real against
the live Docker stack in Phase 11 (see `docs/architecture/ROADMAP.md`
Phase 11) — not just unit-tested.

## 8. Disaster Recovery Scenarios to Document (Phase 11 deliverable,
   tracked here so it isn't forgotten)

- Total loss of the primary host (hardware failure): restore onto new
  hardware from off-host backups; expected RTO/RPO to be defined once
  backup infrastructure sizing is known.
- Corrupted control-plane database only: restore control-plane DB alone
  while tenant DB/object storage remain intact, verifying referential
  consistency against the catalog.
- Accidental destructive operation by an administrator (e.g. dropped
  database): point-in-time recovery via WAL replay to just before the
  operation, using the audit log to identify the exact moment.
- Ransomware/ compromise scenario: restore from an offline/immutable backup
  copy, rotate all credentials and the credential-encryption key, invalidate
  all sessions and application credentials.

## 9. Open Items (post-Phase-11)

- **Database backup tooling: decided.** Plain `pg_dump`/`pg_restore`
  (custom format, `-Fc`) — "boring technology first" (CLAUDE.md); no
  concrete requirement surfaced during implementation that plain
  `pg_dump` couldn't satisfy. `pgBackRest`/WAL archiving remain a future
  upgrade if continuous point-in-time recovery (rather than nightly full
  dumps) becomes a real requirement — not needed to satisfy this phase's
  exit criteria.
- **Object storage backup tooling: not yet chosen.** MinIO server-side
  replication vs `mc mirror` vs `restic`/`borg` — still an operator
  decision, not automated by the platform. Object storage content is
  already content-addressed/UUID-keyed (`storage/backends.py`), which
  makes any of these viable; picking one is deferred until a concrete
  deployment needs it, per "avoid adding dependencies/infrastructure
  before they're needed."
- **Backup file encryption at rest: not yet implemented.** `pg_dump`
  output currently sits unencrypted in `BACKUP_DIR`/the `pdc_backups`
  volume — relying on filesystem/volume-level access control, not
  independent encryption. Encrypting backup files themselves (and
  managing that key, distinct from `CREDENTIAL_ENCRYPTION_KEY`/
  `SECRET_KEY`) is a real gap for the "ransomware/compromise" scenario in
  Section 8 and is the most concrete remaining item in this document.
- Off-host/off-machine shipping (Section 4) and object storage
  replication remain manual operator setup — the platform produces
  correct, verified local backups; getting a copy off-host is
  infrastructure the operator wires up (rsync/NAS mount/cloud sync
  pointed at the `pdc_backups` volume), matching "local-first... backups
  don't require internet dependency for the platform itself to keep
  operating."
