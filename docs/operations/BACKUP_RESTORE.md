# Backup & Restore Strategy — Private Data Cloud

Status: DRAFT (Phase 0 — strategy defined ahead of implementation, to be
built out starting Phase 1 and hardened in Phase 11)
Last updated: 2026-08-07

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

## 6. Restoration Procedure (target outline — to be turned into a tested
   script during Phase 1/11)

1. Provision a clean target environment (or a dedicated restore-test
   environment — never restore-test against production).
2. Restore control-plane PostgreSQL from the chosen backup point.
3. Restore tenant PostgreSQL from the chosen backup point.
4. Restore/replicate object storage data.
5. Restore configuration and secrets from the encrypted secret backup.
6. Bring the stack up pointed at restored data; run health checks.
7. Run a scripted validation pass: can a known test user log in, can a
   known test file be downloaded and its checksum verified, can a known
   test table be queried and row counts compared against the pre-backup
   snapshot's recorded counts.
8. Record the restoration test result (`BackupRecord.verified_restorable`)
   with timestamp and outcome.

## 7. Automated Restoration Testing

A recurring (e.g. weekly) job restores the latest backup set into an
isolated, non-production environment and runs the validation pass in
Section 6 automatically, alerting if it fails. This is the concrete
mechanism that satisfies "a backup strategy is not complete until
restoration is tested" — it is a scheduled Celery Beat / cron job, not a
manual checklist item that quietly stops happening.

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

## 9. Open Items for Later Phases

- Choice of concrete backup tooling (e.g. `pgBackRest` vs plain
  `pg_dump`/WAL scripts; `restic`/`borg` vs `mc mirror` for object storage)
  is deferred to Phase 1 implementation and will be recorded as an ADR once
  selected, per Section 27 of the master prompt (version/tooling policy).
- Backup encryption-at-rest key management (where the encryption key for
  backups themselves is stored) needs a concrete decision before Phase 11.
