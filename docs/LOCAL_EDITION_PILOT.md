# Local Edition pilot guide -- one real shop, run in parallel

**Purpose:** find out whether IntraForge Spare Parts / Inventory & Sales works in a real shop **before** the shop
depends on it. The pilot is a controlled experiment, not a go-live.

**The rule:** for the whole pilot the shop keeps its **existing process** (paper, spreadsheet or current software) as
the record of truth. IntraForge runs **in parallel**. Do not replace the shop's only records with IntraForge until
the acceptance checklist below has been met. The pilot ends with a decision, not with a cutover by default.

## What has been qualified, and what has not

| Qualified (evidence in this repository) | Not qualified -- do not rely on it during the pilot |
| --- | --- |
| Spare Parts application on the supported Docker runtime: products, part numbers (typed any way), suppliers, warehouses, customers, receive, sell, sales documents, files, stock history | The **Windows installer**, automatic start after a reboot, the Control Center, and code signing |
| Restricted users: a cashier who can only sell, a receiver who can only receive | A Control Center **restore-from-file** screen |
| Nightly backups, and recovery from backup **files** on a rebuilt system | Access from a second computer on the LAN |
| Working offline | Stock transfers between warehouses, returns, quotations, reports, tax or accounting compliance |
| Small-shop size (tested at 5,000 products / 10,000 part numbers / 10,000 movements) | Anything above that size |

If the pilot needs one of the right-hand items, **stop and tell the project team** before starting.

## Before the pilot (one-time, with a technician)

1. **Choose the person responsible** (the pilot owner) and a deputy. Both know where the backups and the keys are.
2. **Install and confirm health** (the health page reports everything ok). Note the software version.
3. **Set up the organization and application:** create the organization, workspace and project; install *Spare
   Parts*. Load the **suppliers, warehouses and products** (a starting set of the fast-moving parts is enough; do not
   type the whole catalogue first). Enter opening stock as one **receive** per product, reference "OPENING".
4. **Create the people** and give each **only** what the job needs (see the roles table).
5. **Take a full backup, verify it, and copy it off the machine** ([CUSTOMER_BACKUP_POLICY.md](operations/CUSTOMER_BACKUP_POLICY.md)).
   This is the "before" picture: if the pilot goes badly, the shop returns to it and loses nothing.
6. **Do a restore rehearsal** on a spare computer with a technician, once, before real trading data is at stake.
7. **Print the exit procedure** (below) and the issue log sheet.

### Roles (grant exactly these; nothing more)

Each person needs an account first; the owner adds them to the organization, then grants:

| Role | Read access | Write access | Operation authority ("Business operations") |
| --- | --- | --- | --- |
| **Owner / manager** | everything (organization administrator) | everything | Sell, Receive (and can grant them) |
| **Cashier** | the application; products, part numbers, warehouses, customers, stock, stock history | sales orders, order lines, invoices | **Sell** |
| **Receiver / stock clerk** | the application; products, part numbers, warehouses, **suppliers**, stock, stock history | purchase orders and lines (only if recording a supplier) | **Receive** |

A person who both sells and receives gets both authorities on purpose. **Selling does not allow receiving, and
receiving does not allow selling**: the server refuses, not just the screen. Never give a cashier write access to
stock, and never make daily staff organization administrators. Review the list weekly.

## Who does what (data-entry responsibilities)

* **Cashier:** records **every sale** in IntraForge as it happens, as well as in the existing process. Never edits a
  sale afterwards; a mistake is corrected by the owner (see *Corrections*).
* **Receiver:** records every delivery the same day, with the delivery-note number in *Reference*.
* **Owner:** adds new products and part numbers, checks the daily reconciliation, keeps the backup discipline, keeps the
  issue log, and decides corrections.
* **Nobody** types a stock figure directly. Stock changes only by receiving and selling; that is what keeps the
  numbers trustworthy.

## The daily routine (15 minutes)

1. **Morning:** the system is up (health page); last night's four backups exist and the latest is *verified*.
2. **Close of day reconciliation:** compare IntraForge's *Sales* list and the day's stock movements with the
   existing process. Every difference is written in the issue log with a reason, even a trivial one.
3. **Count check:** pick 5 fast-moving items, count them on the shelf, compare with IntraForge's stock. Log any
   difference.
4. **Friday:** copy the latest verified backup set to the off-machine device and note it.

## Corrections (no editing history)

Recorded sales and receipts are not edited, and there is **no "adjust stock" screen** in this release. A wrong
receive or sale is written in the issue log and corrected **by the project team**, who record a correcting stock
movement with the owner's adjust authority (through the application's programming interface, and audited). Do not work
around this by giving staff broader access: the right to adjust stock is deliberately not part of any daily role.

## Issue log

Keep one line per issue, on paper or a spreadsheet:

| Date / time | Who | What was being done | What happened | What was expected | Severity | Screenshot / diagnostics |
| --- | --- | --- | --- | --- | --- | --- |

Severity: **A** stock or money figure is wrong, data lost, or nobody can trade; **B** a screen or step does not work but
there is a workaround; **C** confusing or slow. Report **A** the same day.

## Getting support

* Collect a **diagnostics bundle** ([DIAGNOSTICS.md](operations/DIAGNOSTICS.md)); it is redacted of secrets, but
  **review it for customer names** before sending. Send it with the issue-log line.
* Do not restart or "fix" a system you suspect of losing data; stop entering data and call.
* Updates are only ever applied by the project team, after a fresh verified backup
  ([UPDATE_POLICY.md](operations/UPDATE_POLICY.md)).

## Stop conditions (pause the pilot at once)

* Any **A** issue that is not explained within a day.
* Stock figures that drift from the shelf with no explanation for two days running.
* A backup set that fails verification, or a restore rehearsal that does not work.
* A wish to remove the parallel process "just this week".

## Acceptance checklist (suggested thresholds -- agree them before starting)

These thresholds are proposals for the first pilot, not measured limits.

- [ ] At least **20 trading days** completed in parallel.
- [ ] Every day reconciled; **no unexplained** difference in sales or stock at the end.
- [ ] Shelf counts agree with IntraForge for the sampled items on at least 90% of checks, and every disagreement was
      explained.
- [ ] **Zero A** issues open; every B issue has a workaround the shop accepts.
- [ ] Backups: 20 nightly sets verified; at least 4 weekly off-machine copies made; one real **restore rehearsal**
      passed with the checks in the backup policy.
- [ ] Staff can do their daily task without help; the cashier completes a sale in a time the shop accepts.
- [ ] No one needed to give broader access than the roles above to get work done.
- [ ] The pilot owner signs that they would run the shop on it -- and lists what is still missing.

## Rollback / exit

1. Stop entering data in IntraForge; keep the parallel process as the record (it always was).
2. Take and keep a final full backup, copied off the machine, so the pilot's data can be inspected later.
3. Ask the project team for an export of whatever the shop wants to keep (products, stock, sales); do not assume a
   screen provides one.
4. Decide with the project team: continue, extend, or stop. Stopping loses nothing, because the existing process was
   never turned off.

## Known limits to tell the staff

No transfers between warehouses, no returns or credit notes, no quotations, no reports beyond the lists, invoices are
not a tax document, and purchasing is a simple "received" record. Times are stored in UTC. Backups live on the same
computer until someone copies them.
