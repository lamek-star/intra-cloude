# Level 1 -- roles and what they may do

Derived from the **server-side** authorization, not from hidden buttons:
- IntraForge roles and their permissions: `apps/backend/permissions/catalog.py` (SYSTEM_ROLES, PERMISSIONS).
- How IntraForge's `spareparts.*` capabilities become Spare Parts permissions: `spareparts-platform/src/server/platform/capabilities.ts`.
- Which Spare Parts action needs which permission: the Spare Parts project's generated `docs/generated/API_ROUTES.md` (every route checked on the server).

**Important:** a member added to an organization gets **no role**. Since version 1.2.0 an administrator gives one on the organization page: in the member list's **Roles** column choose **Give a role...**, pick the role, press **Give** (the **x** next to a role takes it away; the last Organization Administrator cannot be removed). The person who creates an organization automatically gets *Organization Administrator*.

## The roles a shop uses

### Owner / Admin (Organization Administrator) -- IntraForge role `organization-administrator`

- **What the role means:** The owner / administrator of the company in IntraForge. Holds every permission except the platform-wide `system.admin`, including every Spare Parts permission.
- **Normal daily tasks:** Install and configure apps, add members, see everything, settings, reports, audit.
- **Actions denied:** Nothing inside the organization is denied (platform-wide administration is Super Administrator only).
- **IntraForge capabilities:** 61 permissions (all except `system.admin`)
- **Resulting Spare Parts permissions (33 of 33):** `audit.read`, `catalogue.admin`, `catalogue.import`, `catalogue.read`, `customers.read`, `customers.write`, `documents.read`, `documents.write`, `enquiries.read`, `enquiries.write`, `inventory.read`, `inventory.write`, `invoices.read`, `invoices.write`, `orders.read`, `orders.write`, `payments.record`, `products.cost.read`, `products.read`, `products.write`, `purchasing.read`, `purchasing.write`, `quotations.read`, `quotations.write`, `reports.financial`, `reports.inventory`, `reports.sales`, `settings.manage`, `settings.read`, `suppliers.read`, `suppliers.write`, `users.manage`, `warehouses.write`

### Spare Parts Manager -- IntraForge role `spare-parts-manager`

- **What the role means:** Runs the Spare Parts application: every `spareparts.*` capability, nothing else in IntraForge.
- **Normal daily tasks:** Everything in Spare Parts: catalogue import, products with costs, stock, purchasing, sales, payments, reports, settings, audit.
- **Actions denied:** IntraForge administration (members, storage, databases...) unless also given other roles.
- **IntraForge capabilities:** `spareparts.view`, `spareparts.catalogue.read`, `spareparts.catalogue.import`, `spareparts.catalogue.manage`, `spareparts.products.read`, `spareparts.products.manage`, `spareparts.cost.read`, `spareparts.inventory.read`, `spareparts.inventory.manage`, `spareparts.sales.read`, `spareparts.sales.manage`, `spareparts.suppliers.manage`, `spareparts.purchasing.read`, `spareparts.purchasing.manage`, `spareparts.reports.inventory`, `spareparts.reports.sales`, `spareparts.reports.financial`, `spareparts.audit.read`, `spareparts.settings.manage`
- **Resulting Spare Parts permissions (33 of 33):** `audit.read`, `catalogue.admin`, `catalogue.import`, `catalogue.read`, `customers.read`, `customers.write`, `documents.read`, `documents.write`, `enquiries.read`, `enquiries.write`, `inventory.read`, `inventory.write`, `invoices.read`, `invoices.write`, `orders.read`, `orders.write`, `payments.record`, `products.cost.read`, `products.read`, `products.write`, `purchasing.read`, `purchasing.write`, `quotations.read`, `quotations.write`, `reports.financial`, `reports.inventory`, `reports.sales`, `settings.manage`, `settings.read`, `suppliers.read`, `suppliers.write`, `users.manage`, `warehouses.write`

### Sales -- IntraForge role `spare-parts-sales`

- **What the role means:** Counter / sales staff.
- **Normal daily tasks:** Search the catalogue, look up products and stock, customers, enquiries, quotations, orders, deliveries, invoices, payments, sales reports.
- **Actions denied:** Cost prices and stock value, changing products, stock changes, suppliers and purchase orders, inventory and financial reports, settings, audit.
- **IntraForge capabilities:** `spareparts.view`, `spareparts.catalogue.read`, `spareparts.products.read`, `spareparts.inventory.read`, `spareparts.sales.read`, `spareparts.sales.manage`, `spareparts.reports.sales`
- **Resulting Spare Parts permissions (18 of 33):** `catalogue.read`, `customers.read`, `customers.write`, `documents.read`, `documents.write`, `enquiries.read`, `enquiries.write`, `inventory.read`, `invoices.read`, `invoices.write`, `orders.read`, `orders.write`, `payments.record`, `products.read`, `quotations.read`, `quotations.write`, `reports.sales`, `settings.read`

### Inventory -- IntraForge role `spare-parts-inventory`

- **What the role means:** Store / purchasing staff.
- **Normal daily tasks:** Catalogue, products incl. cost prices, receive / adjust / transfer stock, warehouses and locations, suppliers (read), purchase orders, inventory reports.
- **Actions denied:** Customers and all sales documents, payments, sales and financial reports, creating suppliers, settings, audit.
- **IntraForge capabilities:** `spareparts.view`, `spareparts.catalogue.read`, `spareparts.products.read`, `spareparts.products.manage`, `spareparts.cost.read`, `spareparts.inventory.read`, `spareparts.inventory.manage`, `spareparts.purchasing.read`, `spareparts.purchasing.manage`, `spareparts.reports.inventory`
- **Resulting Spare Parts permissions (14 of 33):** `catalogue.read`, `documents.read`, `documents.write`, `inventory.read`, `inventory.write`, `products.cost.read`, `products.read`, `products.write`, `purchasing.read`, `purchasing.write`, `reports.inventory`, `settings.read`, `suppliers.read`, `warehouses.write`

### Viewer -- IntraForge role `spare-parts-viewer`

- **What the role means:** Read-only access.
- **Normal daily tasks:** Look at the catalogue, products and stock levels.
- **Actions denied:** Every change, costs, customers and sales documents, reports, settings, audit.
- **IntraForge capabilities:** `spareparts.view`, `spareparts.catalogue.read`, `spareparts.products.read`, `spareparts.inventory.read`
- **Resulting Spare Parts permissions (5 of 33):** `catalogue.read`, `documents.read`, `inventory.read`, `products.read`, `settings.read`

## Spare Parts permission matrix (what each role may do)

| Spare Parts permission | Owner/Admin | Manager | Sales | Inventory | Viewer |
|---|:-:|:-:|:-:|:-:|:-:|
| `audit.read` | yes | yes |  |  |  |
| `catalogue.admin` | yes | yes |  |  |  |
| `catalogue.import` | yes | yes |  |  |  |
| `catalogue.read` | yes | yes | yes | yes | yes |
| `customers.read` | yes | yes | yes |  |  |
| `customers.write` | yes | yes | yes |  |  |
| `documents.read` | yes | yes | yes | yes | yes |
| `documents.write` | yes | yes | yes | yes |  |
| `enquiries.read` | yes | yes | yes |  |  |
| `enquiries.write` | yes | yes | yes |  |  |
| `inventory.read` | yes | yes | yes | yes | yes |
| `inventory.write` | yes | yes |  | yes |  |
| `invoices.read` | yes | yes | yes |  |  |
| `invoices.write` | yes | yes | yes |  |  |
| `orders.read` | yes | yes | yes |  |  |
| `orders.write` | yes | yes | yes |  |  |
| `payments.record` | yes | yes | yes |  |  |
| `products.cost.read` | yes | yes |  | yes |  |
| `products.read` | yes | yes | yes | yes | yes |
| `products.write` | yes | yes |  | yes |  |
| `purchasing.read` | yes | yes |  | yes |  |
| `purchasing.write` | yes | yes |  | yes |  |
| `quotations.read` | yes | yes | yes |  |  |
| `quotations.write` | yes | yes | yes |  |  |
| `reports.financial` | yes | yes |  |  |  |
| `reports.inventory` | yes | yes |  | yes |  |
| `reports.sales` | yes | yes | yes |  |  |
| `settings.manage` | yes | yes |  |  |  |
| `settings.read` | yes | yes | yes | yes | yes |
| `suppliers.read` | yes | yes |  | yes |  |
| `suppliers.write` | yes | yes |  |  |  |
| `users.manage` | yes | yes |  |  |  |
| `warehouses.write` | yes | yes |  | yes |  |

Pages each permission opens (menu visibility, `ui/Shell.tsx`): Dashboard `settings.read`; Reference Catalogue `catalogue.read`; Import `catalogue.import`; My Products and Scan / Lookup `products.read`; Stock & Locations `inventory.read`; Purchase Orders `purchasing.read`; Enquiries `enquiries.read`; Quotations `quotations.read`; Orders `orders.read`; Invoices & Payments `invoices.read`; Customers `customers.read`; Suppliers `suppliers.read`; Reports `settings.read` (each report needs its own report permission); Users `users.manage`; Shop settings `settings.manage`; Audit log `audit.read`.

## All IntraForge roles

| Role | Name | Number of permissions |
|---|---|---|
| `super-administrator` | Super Administrator | 62 |
| `organization-administrator` | Organization Administrator | 61 |
| `storage-administrator` | Storage Administrator | 6 |
| `database-administrator` | Database Administrator | 10 |
| `developer` | Developer | 12 |
| `editor` | Editor | 5 |
| `viewer` | Viewer | 4 |
| `auditor` | Auditor | 1 |
| `guest` | Guest | 0 |
| `service-account` | Service Account | 0 |
| `spare-parts-manager` | Spare Parts Manager | 19 |
| `spare-parts-sales` | Spare Parts Sales | 7 |
| `spare-parts-inventory` | Spare Parts Inventory | 10 |
| `spare-parts-viewer` | Spare Parts Viewer | 4 |

## All IntraForge permissions (capabilities)

| Permission | Meaning |
|---|---|
| `app_template.read` | Read organization-owned business application templates and versions |
| `app_template.manage` | Create/edit/archive business application templates |
| `app_template.publish` | Publish immutable template versions |
| `app_instance.read` | Read installed business application definitions |
| `app_instance.manage` | Install, rename, archive business applications |
| `app_instance.schema.manage` | Manage installed application model, field, and relationship definitions |
| `app_instance.workflow.approve` | Apply a workflow transition marked as requiring approval, in addition to the ordinary database.write every record edit already needs |
| `inventory.sell` | Record a sale (order, lines, stock taken out, invoice) in an installed application |
| `inventory.receive` | Receive stock into a warehouse (optionally with a purchase order) in an installed application |
| `inventory.adjust` | Record arbitrary stock movements directly through the record API of an installed application (there is no adjustment workflow in v1.0) |
| `inventory.transfer` | Move stock between warehouses (authority defined; no transfer workflow exists in v1.0) |
| `workspace.manage` | Create Workspaces and Projects within an organization |
| `org_unit.read` | View an organization's structural units (branches, departments, teams, etc.) and their membership |
| `org_unit.manage` | Create/rename/reparent/delete organizational units |
| `org_unit.membership.manage` | Add/remove users from organizational units |
| `storage.read` | View/download files and folders |
| `storage.write` | Upload, create folders, rename, move |
| `storage.delete` | Delete/restore files and folders |
| `storage.share` | Create share grants for storage resources |
| `storage.manage` | Bucket-level configuration (quotas, versioning, retention) |
| `database.create` | Create a new TenantDatabase within a Project |
| `database.read` | Query/browse data in a database the actor can reach |
| `database.write` | Insert/update/delete rows |
| `database.schema.manage` | Create/alter tables, columns, constraints, relationships |
| `database.delete` | Drop a database/schema |
| `dataset.import` | Run CSV import jobs |
| `dataset.export` | Export data (CSV, API) |
| `dataset.analyze` | Create/edit saved analytics dashboards (ad-hoc analysis only needs database.read) |
| `application.read` | View an organization's registered Applications and their metadata |
| `application.create` | Register a new Application |
| `application.credentials.manage` | Issue/rotate/revoke Application credentials |
| `permissions.manage` | Create/edit Roles, assign Roles, create Resource Grants |
| `users.manage` | Invite/remove/suspend users, manage Team membership |
| `audit.read` | View audit logs |
| `backup.manage` | Trigger/inspect backup and restore operations |
| `export.manage` | Create and download portable (.icp) exports of an organization |
| `connection.manage` | Create/edit ConnectedDatabase configurations |
| `sharing.manage` | Create/revoke ShareGrants (internal/external) |
| `system.admin` | Platform-wide administrative operations (Super Administrator only) |
| `environment.read` | View an Application's Environments and their non-secret configuration/status |
| `environment.manage` | Create/update/clone/disable/delete Environments, variables, and webhooks |
| `environment.secrets.manage` | Create/rotate/delete Environment secrets and issue/revoke environment-scoped credentials |
| `environment.production.manage` | Required in addition to environment.manage/environment.secrets.manage for any mutating operation on a production-tier Environment |
| `spareparts.view` | Open an installed Spare Parts application and read its settings and documents |
| `spareparts.catalogue.read` | Search and read the Spare Parts reference catalogue |
| `spareparts.catalogue.import` | Import catalogue CSV files and offline catalogue packages |
| `spareparts.catalogue.manage` | Manage catalogue sources, verification and image rights |
| `spareparts.products.read` | Read the shop's own products (My Products) |
| `spareparts.products.manage` | Create and change products, prices, photos and part numbers |
| `spareparts.cost.read` | See purchase costs and inventory value |
| `spareparts.inventory.read` | Read stock levels and movements |
| `spareparts.inventory.manage` | Receive, adjust and transfer stock; manage warehouses and locations |
| `spareparts.sales.read` | Read customers, enquiries, quotations, orders and invoices |
| `spareparts.sales.manage` | Manage customers, enquiries, quotations, orders and invoices, and record payments |
| `spareparts.suppliers.manage` | Create and change suppliers |
| `spareparts.purchasing.read` | Read suppliers and purchase orders |
| `spareparts.purchasing.manage` | Create purchase orders and receive goods against them |
| `spareparts.reports.inventory` | Read inventory reports |
| `spareparts.reports.sales` | Read sales reports |
| `spareparts.reports.financial` | Read financial reports (outstanding invoices, payments) |
| `spareparts.audit.read` | Read the Spare Parts application's own history |
| `spareparts.settings.manage` | Change the Spare Parts application's shop and document settings |
