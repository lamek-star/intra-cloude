# Backup policy for a Local Edition customer

This is the plain-language policy a shop should adopt. The engineering detail is in
[BACKUP_RESTORE.md](BACKUP_RESTORE.md); the evidence that it works is in [RECOVERY_DRILL.md](RECOVERY_DRILL.md).

## What is backed up

Four separate backups, made automatically every night by the application's own scheduler:

| Backup | Time (server clock) | What it holds |
| --- | --- | --- |
| Control database | 02:00 | Users, organizations, permissions and sharing, installed applications and their definitions, audit trail |
| Business data | 02:30 | Every record of every installed application: products, part numbers, stock, movements, sales, invoices |
| Files | 02:45 | Every uploaded file (documents, images) |
| Configuration | 02:50 | The application's settings (secret values only when backup encryption is on) |

**All four are needed for a full recovery**, and they should come from the same night. A copy of only the business
data will not bring back users, permissions or files.

Every Sunday (03:00-04:15) the system restores the latest backup of each kind into an isolated throwaway target and
checks it. A backup the system has never test-restored is marked *unverified* in the backup list; treat only
*verified* backups as good.

## Where backups are kept

In the appliance's backup folder (`BACKUP_DIR`), on the **same machine and disk** as the business. That protects
against a mistake, not against a failed disk, theft, fire or ransomware.

## The rule that makes it a policy: keep a copy somewhere else

**A backup stored only on the disk that fails is not a backup.** At the end of every working week, and before any
upgrade, copy the latest set of four files to a device that is **not** the shop computer: a USB drive kept off-site,
a second PC or a NAS on the network. Keep at least one copy that is disconnected from the computer most of the time.

The system does not copy backups off the machine by itself and has no internet dependency; the off-machine copy is a
human step, so it needs a named person and a day. Record it (date, who, which drive).

## Encryption and the one key you must never lose

Backups can be encrypted at rest (`BACKUP_ENCRYPTION_KEY`). Encrypted backups cannot be read without that key, and
the key is **not inside the backup**. Store the encryption key, the application secret key and the credential key
**separately from the backups** (a sealed envelope in a safe is fine). Losing the encryption key makes every
encrypted backup permanently unreadable. Backups made without the key have their secret values removed.

## How long to keep them

The engineering target is 14 daily, 8 weekly and 12 monthly backups. **The system does not delete old backups**
(deliberately: nothing destructive happens silently). The backup folder grows until someone removes old files, so
check free disk space monthly and remove the oldest backups only after a newer verified set exists off the machine.

## Restore: what to do when it goes wrong

1. Stop and do **not** keep entering data into a damaged system.
2. Get the latest good set of four backup files (from the off-machine copy if the disk failed).
3. Have a technician follow the total-loss recovery procedure (BACKUP_RESTORE.md section 6a): install fresh, restore
   the control database, then the business data, then the files, then start the system and check it.
4. Verify before trading again: log in, look up a known product, check a known stock figure, open a recent sales
   document, open a recent file. Then record one test sale and one test receive.

Restoring a backup **replaces** the current data with the state at the time of that backup; anything entered after
that night is lost and must be re-entered from paper. That is why the pilot runs alongside the shop's existing records.

**Windows Control Center restore:** the button currently asks for a backup record number from the database, which
does not exist after a total loss. Restore from a backup file is done with the command-line procedure above; a
Control Center restore-from-file screen is **not qualified** (no Windows environment was available).

## Full backup versus portable export (`.icp`)

They are different things and do not replace each other.

| | Full backup | Portable export (`.icp`) |
| --- | --- | --- |
| Purpose | Disaster recovery of the whole installation | Move or copy one organization's generic data to another installation |
| Restores | The same installation, with its users, permissions and audit trail | Creates a **new** organization; never overwrites |
| Includes | Everything in the four backups above | Workspace and project tree, business databases (tables and rows), stored files (structure and bytes), membership and system-role metadata, applications and their environments (configuration and secret *names* only) |
| Does **not** include (the package's own manifest lists these) | - | Installed application definitions and runtime (`app_platform`), sharing grants, application credentials, secret values, webhook signing secrets, connected-database definitions, analytics, password hashes; the audit trail is not part of the package |

**An installed application such as Spare Parts cannot be moved with a `.icp` export.** Its definition, its permissions
and its stock ledger live in the control database, which only a full backup carries; an export would recreate raw
tables without the application around them. Use a full backup to recover or migrate a business.

Never rely on a `.icp` export as your backup.

## Checklist for the person responsible

- [ ] Every Monday: the last night's four backups exist and the latest set is *verified*.
- [ ] Every Friday: a copy of the latest set is on the off-machine device.
- [ ] Monthly: free disk space checked; oldest backups removed only if newer verified ones exist off-machine.
- [ ] Quarterly: a real restore test on a spare computer, with the checks above.
- [ ] The encryption, application and credential keys are stored separately and a second person knows where.
