# Update policy (Local Edition)

There are **two different kinds of update**. Customers and supporters must not confuse them.

## 1. Application (template) upgrade -- changes what an installed application contains

A newer version of an application's *definition* (for example a new field on Part, or a new section) is applied to an
installed instance **without touching its data**. This is the three-way upgrade in `upgrades.py`:

* **Adds** what is new (fields, sections, relationships, constraints) and applies label changes the customer never
  edited.
* **Never overwrites** anything the customer changed locally, and **never applies** a structural change to an existing
  field or a removal: those are reported for manual review.
* Keeps the instance's identity, records, ledger triggers, stored files and permissions.

**Evidence:** an installed, browser-built Spare Parts business with data, a file and a restricted cashier was
customised locally, upgraded, and measured equal before and after -- 68/68 checks, plus browser checks and a real sale
and receive afterwards (`scripts/qualification/template-upgrade/upgrade_drill.py`,
[RECOVERY_DRILL.md](RECOVERY_DRILL.md), [LOCAL_EDITION_APPLICATIONS.md](../LOCAL_EDITION_APPLICATIONS.md)).

**Known gap (P2):** a newer built-in application definition reaches an organization's own template only as a side
effect of installing that application again (which also creates a second instance). There is no "update available"
notice and no way to publish just the new version. Until there is, the supporter runs the two steps: publish the new
version, then upgrade the existing instance from its page.

## 2. Product (appliance) update -- new IntraForge software

New backend, frontend and database migrations. On the Docker Compose path the sequence is in
[UPGRADE_GUIDE.md](../deployment/UPGRADE_GUIDE.md) section 1. In short:

1. **Take and verify a backup first, and copy it off the machine** ([CUSTOMER_BACKUP_POLICY.md](CUSTOMER_BACKUP_POLICY.md)).
   This is not optional: it is the only rollback.
2. Build the new images, review the new migrations, stop the application tier, run `migrate`.
3. **Run `seed_permissions`.** New permissions and role grants exist only after it runs; an upgraded system that
   skipped it will refuse operations its administrators should be able to do (this is the step that gives an
   organization administrator the `inventory.*` operation authorities of ADR-0017).
4. Start, check `/readyz`, log in, look up a product, record one test sale and receive.

**Rollback limitation.** Migrations are not reversed by hand. If an update goes wrong after step 2, the way back is to
restore the pre-update backup, which replaces everything entered since that backup. That is why updates are done at
the end of a trading day, right after a fresh backup.

**Version compatibility.** There is no version-skip policy yet (only one release line exists). Do not skip releases;
update in order. No cross-version restore guarantee is documented or tested: restore a backup with the same product
version that made it, and after any update take a fresh backup before relying on older ones.

**Changes a supporter must tell the customer about (current release):**

* Cashiers must be granted the **Sell** operation authority on the application. Write access to the stock tables no
  longer lets anyone sell or receive; the sale screens use the controlled sell/receive operations
  ([ADR-0017](../architecture/adr/0017-inventory-operation-authority.md)).
* External integrations that wrote stock movements through the record API now need an explicit `inventory.adjust`
  grant.
* Webhook receivers must deduplicate on `event_id` (delivery is at-least-once).

**Evidence for the update path:** during qualification the running stack with populated data was upgraded in place to
the current images -- migration `sharing.0002` applied, permissions re-seeded -- and the flagship, restricted-user and
recovery journeys were run against it. That is supporting evidence, **not** a formal update drill; a scripted "update a
populated deployment and prove nothing was lost" drill remains an open item, and the Windows appliance update path
(MSI and distribution) is externally blocked (no Windows environment).

## What Local Edition does not do

There is no automatic-update or version-check mechanism in the product: nothing downloads or applies a new version by
itself. Updates are a deliberate act by the person responsible, with a backup in hand.
