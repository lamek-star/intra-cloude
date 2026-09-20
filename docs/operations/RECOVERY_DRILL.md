# Business recovery drill

Status: **VERIFIED at the data plane, 2026-09-19** (disposable qualification stack).
Not yet qualified end to end: see "What this does not prove".

The question a shop owner cares about is not "does the backup command exit 0"
but "after the machine is gone, do I get my business back?". This drill answers
it by measurement: it builds a real business, backs it up, copies the backups
off the stack (as an external drive would), **destroys the environment**,
initializes a fresh one, restores from the copied files alone, and compares
what came back with a snapshot taken before the disaster.

## What it does

`scripts/qualification/recovery-drill/run-drill.sh` (driver) and `drill.py`
(seed / snapshot / verify, run through `manage.py shell` with production
settings) execute, against the disposable compose project
`intraforge-local-qualification` only:

1. **destroy** — remove the project's containers and its volumes.
2. **init** — start empty Postgres ×2, Valkey, MinIO; `migrate`; `seed_permissions`.
3. **seed** — through the real services and API: a user and a restricted
   cashier, an organization, the *Spare Parts — Inventory & Sales* template
   installed and provisioned (its quantity ledger binds automatically), parts,
   part numbers, warehouses, a supplier, a customer, zero-start inventory rows;
   a purchase receipt, a two-leg transfer and a full sale (order + line +
   movement + invoice) as atomic transactions; a product image attached to a
   part and a stored invoice document; per-model sharing grants for the cashier.
   Then the **expected-state snapshot** is written.
4. **backup** — `run_backup` for `control_db`, `tenant_db`, `object_storage`,
   `configuration` (encrypted at rest, `.icb`), `verify_backup` for each, then the
   files are copied **off the stack** with SHA-256 checksums.
5. **destroy → init** again — nothing from the first environment remains, including
   every `BackupRecord` row.
6. **restore_gap** — reproduces the defect this drill found (below).
7. **restore** — `restore_backup_file` for control DB, then tenant DB, then object storage.
8. **verify** — the same `snapshot()` measures the recovered system and it is
   compared with the pre-disaster one; then behavior probes run.

## The defect it found (P0, fixed)

`restore_backup <record id>` needs a `BackupRecord` row, and those rows live in
the control database — the thing a total loss removes. On a fresh install with
the backup files in hand, the only supported restore command failed with
`No backup record found with id …`, and the "full-environment restoration drill"
in `BACKUP_RESTORE.md` §6/§8 had never been executed. A total loss could not be
recovered with the product's own tooling. Fix: `system/backups.py::
restore_backup_from_file` and `manage.py restore_backup_file <file> --type … --yes`,
which need only the file and its type (see `BACKUP_RESTORE.md` §6a). The file must sit
inside `BACKUP_DIR` (the restore reads it with the platform's database credentials,
so it is not pointed at arbitrary paths). Tests: `system/tests/test_restore_backup_file.py`
(10 tests; each deletes the `BackupRecord` a real total loss would destroy).
Reproduction → fix: `restore-file-reproduction.log` (10 failed) →
`restore-file-corrected.log` (57 passed with the existing `system` suite).

## Evidence (single clean run, all stages, one invocation)

`recovery-drill/drill.log`, `seed.log`, `verify.log`,
`restore-by-record-reproduction.log` under
`C:/Users/Hp/.codex/tmp/intraforge-local-20260918/`:

- **47 / 47 checks passed** on the restored business: organization, instance, model
  and ledger ids; every one of the 13 models has the same record ids **and byte-identical
  record content** (content hash); stock balances per (part, warehouse); the
  ledger reconciles (`reconcile() == []`); the ledger triggers exist; share grants and
  memberships; the audit trail is preserved; **every file byte-identical (SHA-256)**
  through the real download path; **both users log in** through `/api/v1/auth/login/`
  with their pre-disaster passwords.
- **Behavior, not just presence:** after the restore, overselling is still rejected, a
  direct balance edit is still rejected, a movement still cannot be deleted, the
  restricted cashier is still denied on Part, and a new receive and a new sale work
  and reconcile.
- Observed on this (tiny) dataset: control dump 357 KB, tenant dump 56 KB, object
  archive 154 KB; the three restores took ~25 s including copying files in. This is
  not a performance or RTO claim.

## Second run: a business built through the browser, restored into a clean install (2026-09-20)

The first run drilled a business seeded through services. This run drilled the **UI-built flagship**
(`e2e/spare-parts-recovery-prep.spec.ts`: supplier, warehouse, product, part number, receive 100, customer, sell 5 -> 95,
a stored document, and a restricted cashier with the 10 documented grants), in the same environment that also held the
5,000-product scale dataset (`docs/implementation/SCALE_QUALIFICATION.md`). Logs: `restore-ui/` under the private
qualification log folder (`stage1a.out` ... `stage5.out`, `post-restore-browser.log`, `post-restore-operate.log`).

1. **Snapshot** the business through the real API (`DRILL_MODE=snapshot`): record ids and content hashes of all 13
   models, balances, reconcile, ledger triggers, grants, memberships, audit count, file SHA-256.
2. **Backup** control DB, tenant DB, object storage and configuration, encrypted at rest; each restored and validated
   in an isolated throwaway target; then **copied off the stack** with checksums (control 3.8 MB, tenant 9.8 MB, objects
   0.8 MB).
3. **Destroy**: the containers and the four data volumes of the disposable stack were removed. **Proof of the empty
   state** before restoring: 0 app instances, 0 tenant schemas, none of the business users or organizations (only the two
   migration-provisioned system accounts and the catalogue-ops organization existed).
4. **Clean initialize**: empty databases, migrations, permission seed.
5. **Restore from the backup FILES** (`restore_backup_file`, newest file per type, SHA-256 matched the off-stack copy) --
   no dependence on the original `BackupRecord`: control DB, tenant DB, object storage, **44 s in total** with the scale
   dataset in the same databases.
6. **Start the whole stack** (`up -d`: backend, worker, beat, frontend, proxy): `/healthz` ok, `/readyz` ok for the control
   database, the tenant database and Valkey.
7. **Browser check** (`e2e/spare-parts-existing-business.spec.ts`, real logins with the original passwords): the owner finds
   the normalized part-number search result (`044650K290` -> `04465-0K290` preserved), the supplier, warehouse and customer,
   **stock 95**, **exactly 2 movements** (+100, -5), the sales document `INV-20260920-WXT2F`, and the stored file with its
   bytes; the cashier logs in, finds the product, is refused the supplier list and sees no filename -- 2/2.
8. **Measured comparison** (`drill.py verify`): **51/51 checks** -- org, instance, model and ledger ids; every model's record
   ids and byte-identical content; balances; reconcile `[]`; ledger triggers; grants (10) and memberships; audit trail;
   the stored file byte-identical (SHA-256); both logins; overselling still refused; a direct balance edit still refused; a
   movement still cannot be deleted; the restricted cashier still denied on Part; normalized search still finds the
   product; the invoice is still linked to its order and line; then **new operations**: a receive, a sale, a **sale by the
   restricted cashier**, the stock returned to its figure, the ledger reconciles.
9. **New operations through the browser**: the cashier sold 1 and the owner received 1 through the UI -- passed.
10. **The scale dataset that shared the database came back identical**: 5,001 balance rows, on hand 630,527 = the sum of
    10,086 movements, drift `[]` (`scale-after-restore.log`).

Writing the expected-state file was blocked once by a permissions quirk (the seeded drill's file, put back by `docker cp`, is owned by
root); the UI drill now keeps its expected state under its own path (`/backups/drill-ui/`).

## Operator procedure (total loss)

Prerequisites the operator must hold **outside** the machine: the backup files
(control DB, tenant DB, object storage — ideally from the same backup run), and the
protected secrets (`BACKUP_ENCRYPTION_KEY`, `CREDENTIAL_ENCRYPTION_KEY`,
`SECRET_KEY`). Without `BACKUP_ENCRYPTION_KEY` encrypted backups cannot be read.

1. Install IntraForge fresh (empty databases; migrations applied).
2. Stop the application containers (backend, worker, beat).
3. Copy the three backup files into `BACKUP_DIR`.
4. In order: `manage.py restore_backup_file <control file> --type control_db --yes`,
   then `--type tenant_db`, then `--type object_storage`.
5. Start the stack; check readiness; log in.

## What this does not prove

- **Not run on the Windows/WSL2 appliance.** The drill used the disposable Docker stack.
  `Invoke-IntraCloudRestore.ps1` and the Control Center still take a `BackupRecord` id;
  there is **no customer-facing restore-from-file yet** (open P1). Until then a total-loss
  recovery is an operator/technician procedure using the commands above.
- ~~The application containers were not restarted against the restored data.~~ Done in the second run: the
  whole stack was started on the restored data, health checks passed, and owner and cashier logged in through
  the browser and worked.
- **Configuration/secrets are not restored by the product**; the drill reused the same
  private env file, standing in for the operator's separately secured secret record.
- **No writes were in flight**, and the three backups came from one quiet moment.
  Matched, quiesced backups remain a requirement (`BACKUP_RESTORE.md` §5); nothing here
  claims distributed atomicity.
- The second run restored ~14 MB of dumps (with the 5,000-product dataset present) in 44 s. That is one data point on
  one machine, not an RTO/RPO claim, and the backups still came from one quiet moment.
