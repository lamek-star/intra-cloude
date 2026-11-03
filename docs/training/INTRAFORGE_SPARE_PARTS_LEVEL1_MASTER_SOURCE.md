# IntraForge + Spare Parts -- Level 1 master source

*One consolidated source for a beginner training manual. It repeats only what the detailed Level-1 documents state (which are derived from the implemented code); things not implemented are said to be not implemented.*

## PART 1 -- IntraForge overview

IntraForge is a private business system that runs on the shop's own PC. In a browser on that PC it offers organizations
(companies), people, file storage, databases you design yourself, imports, analytics, applications (Spare Parts) and an
audit log. It is reached at **`https://localhost:8443`** -- from this PC only. The browser warns about the certificate the
first time because the certificate is the PC's own: *Advanced > continue*.

Next to the web interface there is a Windows program, the **IntraForge Control Center** (section 13), for starting,
stopping, backing up, restoring and removing IntraForge.

---

- **Normally automatic**: IntraForge starts when someone signs in to Windows (about 1-2 minutes).
- **By hand**: double-click the **IntraForge** shortcut (the Control Center) and press **Start**; **Open IntraForge** opens the
  browser. The Control Center shows **Healthy** when everything runs (section 13).

---

## PART 2 -- IntraForge interface

- **Sign in** (`/login`): **Email**, **Password**. If two-step sign-in is switched on for the account, an **Authenticator code**
  (6 digits from an authenticator app) is asked for as well. Too many attempts are slowed down on purpose (at most 10 a minute).
- **Create account** (`/register`): **First name**, **Email**, **Password**. Then the **Welcome** screen helps create the first
  organization.
- **Two-step sign-in** can be switched on, confirmed and switched off through the server (`auth/mfa/enroll`, `confirm`,
  `disable`), but **there is no screen to switch it on** -- IMPLEMENTED — DOCUMENTATION NEEDED (and a screen is missing).
- **Log out**: the account menu > **Log out**. Logging out of IntraForge also ends any application session (Spare Parts).
- **Quick search / command palette**: **Ctrl+K** (or Cmd+K) opens a palette to jump to pages.

---

A sidebar with three items: **Dashboard**, **Apps**, **Organizations**, and the account menu. Pages show a title, a short
description, action buttons at the top right, and breadcrumbs. IntraForge does not hide buttons by permission; if you are
not allowed, the server refuses and the page shows a "you don't have permission" message. A resource of an organization you
are not a member of is shown as "not found".

---

"An overview of your organizations and this deployment's health": your organizations with their workspace counts, the
system's **health** (`/healthz`) and **readiness** (`/readyz`), and -- when you belong to exactly one organization -- its 8
most recent audit events.

---

## PART 3 -- IntraForge pages

Every page of the IntraForge web interface:

| Page | Address | What it is for | How to get there |
|---|---|---|---|
| Landing page | `/` | Public start page shown before signing in; leads to sign-in or registration. | Open https://localhost:8443/ |
| Sign in | `/login` | Signs a person in with email and password, and asks for a 6-digit authenticator code when two-step sign-in is switched on. | Open IntraForge; you are sent here when not signed in |
| Create account | `/register` | Creates a new IntraForge account (the first account on a new installation becomes its first user). | Sign-in page > create an account |
| Welcome | `/welcome` | First-run welcome screen after creating an account. | Shown after registering |
| Dashboard | `/dashboard` | Overview after signing in: your organizations (with workspace counts), the system's health and readiness, and -- when you belong to exactly one organization -- its latest audit events. | Sidebar > Dashboard (also shown right after sign-in) |
| Apps | `/apps` | Lists the service applications installed in your organizations (today: Spare Parts) with their live status; install, open and configure them. | Sidebar > Apps |
| Open application | `/service-apps/[appId]/open` | Hand-over page: creates the app session and sends you into the application (no second sign-in). | Apps > Open |
| Application settings | `/service-apps/[appId]/settings` | Settings of one installed service application: name, shop details, availability, removal (keep data or delete data after a backup), reinstate. | Apps > Settings |
| Organizations | `/orgs` | Lists the organizations (companies) you belong to; create a new one. | Sidebar > Organizations |
| Organization | `/orgs/[orgId]` | One organization: its workspaces, members and roles, and links to teams, units, applications (developer) and the audit log. | Organizations > click an organization |
| Teams | `/orgs/[orgId]/teams` | Groups of members inside an organization; add and remove team members. | Organization > Teams |
| Organizational units | `/orgs/[orgId]/units` | The organization's structure (branches, departments...): create, rename, nest units and manage their members. | Organization > Units |
| Audit log (organization) | `/orgs/[orgId]/audit` | The unchangeable history of actions in the organization, filterable by resource type, action and result, with paging. | Organization > Audit log |
| Business app templates | `/orgs/[orgId]/app-templates` | Templates of the application platform owned by this organization; create a new template. | Organization > templates |
| Workspace | `/orgs/[orgId]/workspaces/[workspaceId]` | A workspace groups projects; create projects here. | Organization > a workspace |
| Project | `/projects/[projectId]` | A project holds file buckets, tenant databases, connected databases and dashboards; create each of them here. | Workspace > a project |
| Applications (built-in business apps) | `/projects/[projectId]/apps` | Built-in business applications of the application platform for this project, with their qualification status; install and open them. | Project > Applications |
| Bucket (files) | `/buckets/[bucketId]` | A file area: upload, download and delete files, see versions and sharing. | Project > a bucket |
| Database | `/tenant-databases/[dbId]` | A tenant database: its tables, creating tables, sharing, analytics dashboards and dropping the database. | Project > a database |
| Table | `/tables/[tableId]` | One table: its columns, rows (browse, add, edit, delete), and links to import and analytics. | Database > a table |
| CSV import | `/tables/[tableId]/import` | Import a CSV file into a table: upload or pick a stored file, preview detected encoding / delimiter / types, map columns, watch the job. | Table > Import |
| Table analytics | `/tables/[tableId]/analytics` | Automatic data-quality profile of every column and a form to run statistics (descriptive, correlation, regression, t-test, chi-square, ANOVA, time series). | Table > Analytics |
| Dashboard (analytics) | `/dashboards/[dashboardId]` | A saved analytics dashboard: widgets re-run live; add and remove widgets. | Database > a dashboard |
| Connected database | `/connected-databases/[connectedDatabaseId]` | A read-only connection to an external PostgreSQL database: test it and browse its tables. | Project > a connected database |
| Template builder | `/app-templates/[templateId]` | Design a business application template: models, fields, relationships, unique constraints, workflows; publish versions. | Organization > templates > a template |
| Template version | `/app-template-versions/[versionId]` | Read-only view of one published (immutable) template version. | Template > a version |
| Installed business app (definition) | `/app-instances/[instanceId]` | An installed application-platform instance: its definition, upgrades to newer template versions, sharing and unit grants. | Project > Applications > an instance |
| Model records | `/app-models/[modelId]` | Records of one model of an installed business app: list, add, edit, delete; schema editing for managers. | Installed app > a model |
| Record | `/app-models/[modelId]/records/[recordId]` | One record: its fields, attachments and workflow transitions. | Model > a record |
| Built-in Spare Parts business app: overview | `/apps/[instanceId]` | Overview of the application-platform Spare Parts / Inventory & Sales app (a DIFFERENT application from the Spare Parts service app opened from Apps). | Project > Applications > Open |
| Built-in app: Products | `/apps/[instanceId]/products` | Products of the built-in business app. | Built-in app > Catalogue > Products |
| Built-in app: Product | `/apps/[instanceId]/products/[partId]` | One product with its part numbers, stock and attachments. | Products > a product |
| Built-in app: Part numbers | `/apps/[instanceId]/part-numbers` | Search and add part numbers of products. | Built-in app > Part numbers |
| Built-in app: Stock | `/apps/[instanceId]/inventory` | Stock levels per product and warehouse. | Built-in app > Inventory > Stock |
| Built-in app: Warehouses | `/apps/[instanceId]/warehouses` | Warehouses of the built-in app. | Built-in app > Warehouses |
| Built-in app: Receive stock | `/apps/[instanceId]/receive` | Receive goods into a warehouse (inventory.receive). | Built-in app > Receive stock |
| Built-in app: Suppliers | `/apps/[instanceId]/suppliers` | Suppliers of the built-in app. | Built-in app > Suppliers |
| Built-in app: Customers | `/apps/[instanceId]/customers` | Customers of the built-in app. | Built-in app > Customers |
| Built-in app: Sales | `/apps/[instanceId]/sales` | Sales documents of the built-in app. | Built-in app > Sales |
| Built-in app: New sale | `/apps/[instanceId]/sales/new` | Record a sale (order, lines, stock out, invoice) -- inventory.sell. | Built-in app > New sale |
| Built-in app: Sale | `/apps/[instanceId]/sales/[orderId]` | One recorded sale with its lines and invoice; print. | Sales > a sale |
| Application (API client) | `/applications/[applicationId]` | A registered application (a program that connects to IntraForge): its credentials, resource grants and environments. | Organization > Developer > Applications > one |
| Environment | `/environments/[environmentId]` | One environment (Development / Staging / Production) of an application: variables, secrets, webhooks, bound database/bucket, credentials. | Application > an environment |
| Developer portal | `/orgs/[orgId]/developer` | Entry to the developer area: applications, environments, webhooks, docs. | Organization > Developer |
| Developer: Applications | `/orgs/[orgId]/developer/applications` | List and create registered applications (API clients). | Developer > Applications |
| Developer: Connect application | `/orgs/[orgId]/developer/applications/connect` | Step-by-step wizard to register an application, choose access and get its credential. | Developer > Applications > Connect application |
| Developer: Environments | `/orgs/[orgId]/developer/environments` | All environments of the organization's applications; create, clone, disable, delete. | Developer > Environments |
| Developer: Webhooks | `/orgs/[orgId]/developer/webhooks` | Webhook subscriptions across environments (signed event deliveries to other systems). | Developer > Webhooks |
| Developer: Docs | `/orgs/[orgId]/developer/docs` | Developer documentation links. | Developer > Docs |
| Developer: SDKs | `/orgs/[orgId]/developer/sdks` | Information about client libraries. | Developer > SDKs |
| Developer: API Keys (PLACEHOLDER) | `/orgs/[orgId]/developer/api-keys` | Placeholder page: "A cross-application key list isn't built yet". Credentials are managed per application. | Developer > API Keys |
| Developer: API Logs (PLACEHOLDER) | `/orgs/[orgId]/developer/api-logs` | Placeholder page: "A request-by-request API log isn't built yet". | Developer > API Logs |
| Developer: Auth (PLACEHOLDER) | `/orgs/[orgId]/developer/auth` | Placeholder page: "Letting applications authenticate end users isn't built yet". | Developer > Auth |
| Developer: Database (PLACEHOLDER) | `/orgs/[orgId]/developer/database` | Placeholder page: "An organization-wide database view isn't built yet". | Developer > Database |
| Developer: Storage (PLACEHOLDER) | `/orgs/[orgId]/developer/storage` | Placeholder page: "An organization-wide storage view isn't built yet". | Developer > Storage |
| Developer: Usage (PLACEHOLDER) | `/orgs/[orgId]/developer/usage` | Placeholder page: "Per-application usage metering isn't built yet". | Developer > Usage |

- **Organizations** (`/orgs`): "Every organization you're an active member of." **New organization** (Name). The person who
  creates an organization becomes its **Organization Administrator**.
- **Organization page**: its workspaces (**New workspace**), its **members** (Email, Name, Status, Team) and **Add member**
  (*Email of an existing user* -- the person must have created an account first), and buttons to **Apps**, **Teams**, **Units**,
  **Developer** and **Audit log**. Without `users.manage` the page says: "No member list visible — you may not hold
  users.manage in this organization."
- **Roles**: a newly added member gets **no role**, so by default they can do nothing (everything is denied unless a role or
  a share allows it). Since version 1.2.0 the member list has a **Roles** column (shown to people who hold
  `permissions.manage`): **Give a role...**, pick one (the line below it says what it allows), **Give**; the small **x** takes
  a role away. The organization's last Organization Administrator cannot be removed. (Before 1.2.0 this was server-only.)
- **Teams** (`/orgs/<id>/teams`): **New team**, **Add member**, **Remove** -- used for sharing with a group.
- **Units** (`/orgs/<id>/units`): the organization's structure (branches, departments): **New unit**, **Add sub-unit**,
  **Edit**, **Members**, **Delete**.

---

The structure is: **Organization > Workspace > Project**. A project holds the actual things:

| In a project | What it is | Main actions |
|---|---|---|
| **Bucket** | A file area | **Upload files**, download, **Delete**, **Share** ("Files are streamed through the backend and checksummed/MIME-sniffed on upload.") |
| **Database** | "A real, isolated PostgreSQL schema — each table below is a genuine table in it." | **New table**, **New dashboard**, **Share**, **Drop database** (asks you to type its name: "Permanently DROP the …") |
| **Connected database** | A read-only link to an external PostgreSQL | **Test connection**, browse tables, **Disconnect** |
| **Applications** | Built-in business apps of the application platform (section 9) | **Install** |

- **Table** (`/tables/<id>`): columns (**Add column**: Name, Type, Max length, Precision, Scale, Nullable, Unique) and rows
  (**Add row**, **Edit**, **Delete** -- "Delete this row?"), paging **Previous / Next**, links to **Import** and **Analytics**.
- **CSV import** (`/tables/<id>/import`): upload a CSV or pick one already in a bucket, preview (detected encoding, delimiter,
  headers, types: CSV column, Inferred type, Sample values, Import into), map columns, then watch the job (pending, running,
  completed; rejected rows with Row and Reason).
- **Analytics** (`/tables/<id>/analytics`): an automatic quality profile of every column and statistics (descriptive,
  correlation, regression, t-test, chi-square, ANOVA, time series). **Dashboards** keep widgets that re-run live.
- **Sharing** (buckets, databases, ...): **Share** with a member or team, **Read only** or **Read & write**; **Revoke** removes it.

---

**Apps** (sidebar) -- "Applications installed in your organizations. Open one to work in it with your IntraForge sign-in."

- **Install** (administrators): choose the **Organization**, the **Shop name** and **Currency**. IntraForge creates the
  application's storage and keeps its data in IntraForge's backups.
- **Open**: opens Spare Parts with your IntraForge sign-in -- **no second sign-in**. You only see apps you may open.
- **Settings** (`/service-apps/<id>/settings`): **Name in Apps**, shop details (Currency, Default tax rate, Quotations valid for
  (days), Invoices due after (days)), availability, and **Remove...**: without deleting data the app is closed and hidden and
  can be **Reinstate**d later; or tick "Also delete all of its data … A backup is taken first; nothing is deleted if the backup
  fails." and type the name to confirm. "Removing it never touches IntraForge itself, other applications, or your backup files."

How to use Spare Parts itself: SPARE_PARTS_LEVEL1_GUIDE.md.

---

Separate from the Spare Parts application, IntraForge can **build** business applications from **templates**:

- **Templates** (`Organization > templates`): models, fields (type, required, unique, default...), relationships, unique
  constraints and workflows (states, transitions, "Requires approval"); **published versions** never change.
- **Installed apps** (`Project > Applications`): built-in business applications with a qualification status; **Install**,
  **Open**; upgrades to newer template versions never overwrite your own changes.
- **Records**: list, add, edit, delete records; attachments; workflow steps.

**Do not confuse** the built-in *Spare Parts / Inventory & Sales* business app made from a template (`/apps/<instance>/...`:
Products, Part numbers, Stock, Warehouses, Receive stock, Suppliers, Customers, Sales, New sale) with the **Spare Parts
application** opened from **Apps** (`/apps/spare-parts/`). The shop uses the one from **Apps**.

---

`Organization > Developer`:
- **Applications**: register a program that connects to IntraForge (**New application**, the **Connect application** wizard);
  on its page issue **credentials** (tokens shown once; **Rotate**, **Revoke**) and **Grant permission** to specific resources.
- **Environments**: Development / Staging / Production, each with tabs **Overview, Configuration, Database, Storage, Auth,
  API Keys, Secrets, Webhooks, Logs, Activity, Settings**; **Connect** binds a database or bucket; secrets are encrypted and shown
  once; deleting a production environment needs a second explicit confirmation.
- **Webhooks**: signed event deliveries to other systems (at least once).
- **Docs**, **SDKs**: information pages.
- **API Keys, API Logs, Auth, Database, Storage, Usage**: **placeholders** -- the pages say these are not built yet.

---

## PART 4 -- IntraForge fields and buttons (the ones a beginner uses)

- **Sign in:** Email, Password, (Authenticator code). **Create account:** First name, Email, Password.
- **New organization:** Name. **Add member:** Email of an existing user. **New workspace / project / bucket / database / table:** Name.
- **Upload files**, **Share** (Share with a member or team, Read only / Read & write), **Revoke**, **Delete**.
- **Apps:** **Install** (Organization, Shop name, Currency), **Open**, **Settings** (Name in Apps, Currency, Default tax rate, Quotations valid for (days), Invoices due after (days)), **Remove...** (keep data, or delete data after a backup), **Reinstate**.
- **Audit log:** filters Resource type, Action, Result; **Apply**, **Clear**, **Previous / Next**.
- **Account menu:** **Log out**. **Ctrl+K:** command palette.
- Every field and button with its details: INTRAFORGE_FIELD_REFERENCE.md and INTRAFORGE_BUTTON_REFERENCE.md.

`Organization > Audit log` -- "A record of security-relevant actions taken in this organization." Columns Time, Action,
Resource, Result, Request ID; filters **Resource type**, **Action**, **Result** with **Apply** / **Clear**; paging. Needs
`audit.read` (otherwise a "you don't have permission" message). Entries cannot be edited. Spare Parts' actions appear here too
(`spareparts.…`).

---

The **IntraForge** shortcut opens the Control Center -- also when IntraForge or Docker is not running. It shows one status
(**Healthy, Starting, Degraded, Stopped, Failed, Repair required**), the installed apps with **Open**, each check (disk,
memory, Docker, services, IntraForge, Spare Parts, last backup) and buttons: **Open IntraForge, Start, Restart services, Stop,
Backup now, Backup to a folder / USB..., Restore..., Settings, Diagnostics..., Uninstall...**

- **Backup**: automatic every day at 19:00 and a weekly restore test; three encrypted files per backup in
  `C:\IntraForgeData\backups`; **Backup to a folder / USB** copies them to a drive.
- **Restore**: choose a backup, **Check this backup** (nothing changes yet), type `RESTORE`; a safety backup is taken first,
  and if anything fails the safety backup is put back automatically.
- **Diagnostics**: a zip for support without passwords or keys.
- **Uninstall**: A keep data / B back up first / C complete removal (typed confirmation); backups, keys and logs are kept.

There is **no backup or restore page in the IntraForge web interface**; these live in the Control Center.

---

## PART 5 -- Spare Parts overview

Spare Parts / Inventory & Sales is the shop's daily program for **parts, stock, customers and sales**. It runs **inside
IntraForge**: you sign in to IntraForge once, open **Apps**, and press **Open** next to Spare Parts. You never sign in to
Spare Parts separately. Its address is `https://localhost:8443/apps/spare-parts/`.

What you can do in it (each area only if your role allows -- see section 12):

| Area | In one sentence |
|---|---|
| Dashboard | Today's figures and what needs attention |
| Reference Catalogue | Look up any manufacturer part: numbers, which vehicles it fits, drawings |
| Import | Load a supplier's / manufacturer's parts list into the catalogue |
| My Products | The parts the shop actually sells: own code, prices, photos, stock |
| Stock & Locations | How many are where; receive, correct and move stock |
| Scan / Lookup | Scan a label or type a code to open the product |
| Purchase Orders | What the shop orders from suppliers, and receiving it |
| Enquiries, Quotations, Orders, Invoices & Payments | Selling, from the customer's question to the money |
| Customers, Suppliers | Who you sell to and buy from |
| Reports | Live figures from stock, invoices and payments |
| Users, Shop settings, Audit log | Administration |

---

## PART 6 -- Spare Parts navigation

- **Left menu**, in groups: *Overview* (Dashboard), *Catalogue* (Reference Catalogue, Import), *Inventory* (My Products,
  Stock & Locations, Scan / Lookup, Purchase Orders), *Sales* (Enquiries, Quotations, Orders, Invoices & Payments),
  *Contacts* (Customers, Suppliers), *Insights* (Reports), *Administration* (Users, Shop settings, Audit log).
  **You only see the items your permissions allow** (each menu item has its own permission, `ui/Shell.tsx`). The menu
  can be collapsed.
- **Top bar**: a search box *"Scan or type a SKU / part number…"* (opens the product), and your name and role; the
  account menu has **Sign out**.
- **Sign out** (since 1.2.0) signs you out of IntraForge as well and shows the shop's own sign-in page ("Spare Parts --
  <shop name>"), so on a shared counter PC the next person signs in as themselves. Signing out of IntraForge also ends
  your Spare Parts session (within about 5 seconds).
- If your Spare Parts session is missing or expired, the app sends you back through IntraForge's **Open** automatically
  (straight back in while you are still signed in to IntraForge; otherwise to that sign-in page).
- Most lists share the same controls: a **search box**, a **status filter** where the list has statuses, **paging**, and the
  number / name as a link that opens the record. Success and error messages appear as short notices.

---

Shows, as your permissions allow: **Products**, **Low stock**, **Stock value (cost)**, **Sales this month**; **Open enquiries**,
**Open quotations**, **Open orders**, **Outstanding invoices**; and the panels **New enquiries**, **Needs reordering**
("Nothing is below its reorder level." when all is fine) and **Unpaid invoices** (Invoice, Customer, Overdue, Balance).
The subtitle shows who is signed in and their role. Next step: open a list or search.

---

Every Spare Parts page:

| Page | Address (inside IntraForge) | What it is for | How to get there |
|---|---|---|---|
| Dashboard (Business overview) | `/apps/spare-parts/` | Today's business at a glance, as your permissions allow: figures (Products, Low stock, Stock value at cost, Sales this month; Open enquiries, Open quotations, Open orders, Outstanding invoices) and panels New enquiries, Needs reordering and Unpaid invoices. | Menu > Overview > Dashboard (first page after Open) |
| Reference Catalogue | `/apps/spare-parts/catalogue` | Search the reference (OEM / supplier) parts catalogue by part number in any format, or browse with filters (manufacturer, model, engine, market, status...). | Menu > Catalogue > Reference Catalogue |
| Reference part details | `/apps/spare-parts/catalogue/parts/[id]` | One reference part: description, numbers, fitment (vehicles), drawings, supersessions, source; whether it is already in My Products; import it to My Products; add it to an enquiry. | Catalogue > click a part number |
| Drawing | `/apps/spare-parts/catalogue/drawings/[id]` | An exploded-view drawing with its numbered callouts and the parts on it. | Part details > a drawing |
| Import reference catalogue | `/apps/spare-parts/catalogue/import` | Upload a CSV (or an offline catalogue package): detect columns, match them to catalogue fields, confirm you may use the data, preview every row, then import. | Menu > Catalogue > Import |
| Import job | `/apps/spare-parts/catalogue/import/[jobId]` | One import job: row-by-row status (new, updated, unchanged, invalid, duplicate...), counts, and the button to import or continue. | Import > after preview |
| My Products | `/apps/spare-parts/products` | The shop's own products (SKU, name, brand, category, prices, stock) with search and filters; create a product; receive / adjust / transfer stock. | Menu > Inventory > My Products |
| Product details | `/apps/spare-parts/products/[id]` | One shop product: details, prices (cost only with products.cost.read), photos, part numbers, suppliers, stock by location, movements, labels (barcode / QR), the linked reference part, history. | My Products > a product |
| Stock & Locations | `/apps/spare-parts/inventory` | Stock levels per product and location; warehouses and their racks / shelves / bins; receive, adjust and transfer stock; movements. | Menu > Inventory > Stock & Locations |
| Scan / Lookup | `/apps/spare-parts/scan` | Scan a barcode or QR label, or type a SKU or any part number and press Enter, to open the product. | Menu > Inventory > Scan / Lookup (or the search box in the top bar) |
| Purchase Orders | `/apps/spare-parts/purchasing` | List of purchase orders to suppliers with their status; create a new one. | Menu > Inventory > Purchase Orders |
| New purchase order | `/apps/spare-parts/purchasing/new` | Create a draft purchase order: supplier, expected date, lines. | Purchase Orders > New |
| Purchase order | `/apps/spare-parts/purchasing/[id]` | One purchase order: confirm it, receive the goods that arrived (stock increases), see what is outstanding. | Purchase Orders > a PO |
| Enquiries | `/apps/spare-parts/enquiries` | Customer enquiries (what a customer asked for) with status; open one to quote it. | Menu > Sales > Enquiries |
| Enquiry cart | `/apps/spare-parts/enquiries/cart` | Your current, not yet submitted enquiry: the parts you added from the catalogue or products; choose the customer / contact and submit. | Add to enquiry (catalogue, part, drawing) > the cart |
| Enquiry | `/apps/spare-parts/enquiries/[id]` | One submitted enquiry: its items and customer; create a quotation from it (lines are priced from My Products when the part number matches). | Enquiries > an enquiry |
| Quotations | `/apps/spare-parts/quotations` | Quotations with status (draft, issued, accepted, rejected, expired, cancelled); create one. | Menu > Sales > Quotations |
| New quotation | `/apps/spare-parts/quotations/new` | Create a draft quotation directly (customer, lines, validity). | Quotations > New |
| Quotation | `/apps/spare-parts/quotations/[id]` | One quotation: edit lines while draft, issue it to the customer (PDF), mark accepted or rejected, cancel, create the order. | Quotations > a quotation |
| Orders | `/apps/spare-parts/orders` | Sales orders with status (confirmed, partially fulfilled, fulfilled, invoiced, cancelled). | Menu > Sales > Orders |
| Sales order | `/apps/spare-parts/orders/[id]` | One order: reserve available stock, record delivery (stock goes out), record returns, invoice the delivered items, cancel. | Orders > an order |
| Invoices & Payments | `/apps/spare-parts/invoices` | Invoices with status (issued, partially paid, paid, void) and outstanding balance. | Menu > Sales > Invoices & Payments |
| Invoice | `/apps/spare-parts/invoices/[id]` | One invoice: lines, totals, payments; record a payment, print / PDF, void. | Invoices > an invoice |
| Customers | `/apps/spare-parts/customers` | Customer list with search and status; create a customer. | Menu > Contacts > Customers |
| Customer | `/apps/spare-parts/customers/[id]` | One customer: details and their quotations, orders and invoices; edit. | Customers > a customer |
| Suppliers | `/apps/spare-parts/suppliers` | Supplier list with search and status; create a supplier. | Menu > Contacts > Suppliers |
| Supplier | `/apps/spare-parts/suppliers/[id]` | One supplier: details and purchase orders; edit. | Suppliers > a supplier |
| Reports | `/apps/spare-parts/reports` | Nine live reports, each shown only with its permission: Stock on hand, Low stock, Inventory valuation (cost), Sales by month, Sales by product, Customer activity, Outstanding invoices, Quotation conversion, Supplier overview; a From / To period. | Menu > Insights > Reports |
| Users | `/apps/spare-parts/admin/users` | Who has access. Inside IntraForge, people, passwords and roles are managed in IntraForge (Organization > Members and Roles); adding or changing users here is refused with that message. | Menu > Administration > Users |
| Shop settings | `/apps/spare-parts/admin/settings` | Shop name, tax registration number, phone, email, address, currency, default tax rate, how many days a quotation is valid, after how many days an invoice is due, and the standard quotation terms and invoice notes printed on documents. | Menu > Administration > Shop settings |
| Audit log (Spare Parts) | `/apps/spare-parts/admin/audit` | The application's own history: who did what and when (also relayed to IntraForge's audit log). | Menu > Administration > Audit log |

## PART 7 -- Reference Catalogue

The application keeps **two different kinds of part information**. Mixing them up is the most common beginner mistake.

| | REFERENCE CATALOGUE | MY PRODUCTS |
|---|---|---|
| What it is | Manufacturer / supplier **reference data** about parts that exist in the world | The parts **your shop** stocks and sells |
| The page says | "Manufacturer part numbers, fitment and drawings. This is reference data — it holds no shop prices or stock." | Your own codes, prices, photos, stock |
| Contains | OEM number, OEM description, manufacturer, PNC, vehicle (make, model, chassis, engine), fitment, production dates, market, catalogue / section, drawings and callouts, supersessions (status *Superseded*), source, external ID, reference price (**info only**) | Shop **SKU** (your own code), name, brand, manufacturer, category, condition, **selling price**, **cost price**, unit, reorder level, photos, extra part numbers, suppliers (their part number, their cost, preferred), **stock** per warehouse location (rack / shelf / bin) |
| Prices | Reference prices from the source -- "**not your selling prices**" | Your selling price and cost price |
| Stock | None | On hand, reserved, available per location |
| Who changes it | Imported by administrators (Import) | Inventory staff and managers |

**How a reference part becomes something you sell:**

```
Reference Catalogue  (find the part, check fitment)
        ↓   IMPORT TO MY PRODUCTS  (on the part's page)
Shop product in My Products  (your SKU, name, prices, reorder level, supplier, location, stock now)
        ↓   Receive stock / opening stock
Inventory  (on hand / reserved / available per location)
        ↓
Quotations, orders, invoices use the shop product
```

The shop product stays **linked** to its reference part ("Linked to the Reference Catalogue"), so its fitment can be shown
(product page, *Fitment* and *OEM Reference* tabs). A product can also be created directly with **New product**, without a
reference part, and linked later ("Link to a reference part").

---

**Searching.** Type a part number **in any format** -- the page explains: "“90915-10009”, “9091510009” and “90915 10009” all
find the same part" -- or a description, vehicle or chassis ("Part number (any format), description, vehicle or chassis…").
Press **Search**. Results: Part number, Description, Fits, Drawings, Status, My Products (whether the shop already stocks it).

**Browsing with filters** (when not searching): Manufacturer, Model, Chassis / frame (example "AT151"), Engine, Market,
Part status (Active, Ended / discontinued, Superseded), "Only parts that appear on a drawing".

**Part details** (click a part number) shows the description and numbers, **Fitment** (Make, Model, Chassis, Engine,
Production, Market, Catalogue / section, Notes), **drawings** with the callout, **source records** (Source, Description,
Status, Reference price *info only*, Recorded, Source record, External ID, Catalogue, Imported, Link), whether it is
already **in My Products**, and buttons **Add to enquiry** and **IMPORT TO MY PRODUCTS**. Catalogue administrators also see
*Verification*.

**Drawings** show the exploded view with numbered callouts and the list of parts on it (No., Part number, Description,
Qty, Status) with a filter "Filter by number, name or callout"; **Add to enquiry** works from here too.

#### Import to My Products

On a part's page press **IMPORT TO MY PRODUCTS**. The dialog asks:
- **Your SKU** (required) -- the shop's own unique code; an existing SKU is refused ("SKU … already exists.").
- **Product name** (required).
- **Selling price**, **Cost price** (cost only if your role may see costs), **Reorder level**.
- **Supplier**, **Store in** (a location) and **Quantity in stock now** (recorded as an opening balance).

Saving creates the product, linked to the reference part (permission `products.write`). Next: open the product and complete
it (photos, more part numbers, suppliers).

#### Catalogue Import (administrators)

*Catalogue > Import* has three tabs: **CSV import**, **Offline package**, **History**.

1. **CSV import**: choose a UTF-8 CSV with a header row (quoted fields, commas and line breaks in quotes, and a byte-order mark
   are allowed). The app reports how many data rows it found and **suggests a match for each column** -- check them.
2. Optional defaults: **Default manufacturer**, **Default source name**, **Default market**.
3. Tick **"I confirm that my organisation is allowed to use this data."** -- required; without it the import is refused.
4. Every row is checked before anything is stored: new, already present, changed, duplicated or invalid, with problems listed.
5. The **job page** shows counts (New, Updated, Unchanged, Skipped, Errors) and row-by-row status; start the import there.
   Big imports continue in the background. Measured: 20,000 rows in about 2 minutes inside IntraForge.
6. **Offline package**: a zip with parts, drawings and images; images are kept only if you confirm the shop is licensed to store
   and display them ("Without this, images are skipped and only their source links are kept.").

---

## PART 8 -- My Products

The list shows Product, Category, Available, On hand, Price, Cost (only with the cost permission), Status, with search
("Search name, SKU, brand or part number"), **Low stock only** and an Active / Inactive status filter.

**New product** asks: **SKU (your own code)** (required), **Name** (required), Brand, Manufacturer, Category, **Condition**
(New, Used, Remanufactured, Other), **Selling price**, **Cost price**, Unit, Description, Status, **Default supplier**,
**Opening stock location**, **Opening stock quantity** (the shelf count when you create it; needs a location).

**Product details** has tabs:
- **Overview** -- details and prices, photos, labels.
- **Fitment** -- vehicles (from the linked reference part; link it on *OEM Reference* to see it).
- **Stock** -- per warehouse / location: On hand, Reserved, Available; buttons Receive, Transfer, Adjust; movements.
- **Supplier** -- suppliers of this product: their part number, cost, preferred; **Add / update supplier**.
- **OEM Reference** -- extra part numbers (Number, Type: OEM, Aftermarket, Supplier, Cross reference, Replacement, Previous,
  Interchange, Other; Brand, Source, Notes) via **Add number**, and the linked reference part.
- **Sales** -- invoices with this product ("Your role cannot see sales figures." if not allowed).
- **History** -- who changed what ("Your role cannot see history." if not allowed).

**Photos (product images):** PNG, JPEG, GIF or WebP only; **Make primary** chooses the main photo; **← Earlier / Later →**
reorder them. They are stored in IntraForge's file storage and are part of its backups.

**Labels:** choose **Barcode label** (Code 128) or **QR label**, then **Open to print**. "Scanning this label in
“Scan / Lookup” opens this product."

**Edit product** changes the details; cost prices can only be changed with the cost permission ("You may not change cost
prices." otherwise). The shop SKU cannot be removed from the product's numbers.

---

## PART 9 -- Inventory

#### Words you will see

| Term | Meaning (as implemented) |
|---|---|
| **On hand** | Units physically there (sum of all stock movements for that product and location) |
| **Reserved** | Units set aside for confirmed sales orders not yet delivered |
| **Available** | `available = on_hand − reserved` -- what you can still sell or move |
| **Reorder level** | A product at or below it shows as *Low stock* / *Needs reordering* |
| **Warehouse** | A store or building (name, address) |
| **Location** | A place in a warehouse made of **Rack**, **Shelf** and **Bin** (and a description); its location code must be unique in the warehouse |

Where a product is: product page *Stock* tab, or *Stock & Locations > Stock* (Product, SKU, Warehouse, Location, On hand,
Reserved, Available).

#### Stock movement types (the only ones that exist)

| Type | Created by |
|---|---|
| `OPENING_BALANCE` | Opening stock when a product is created / imported |
| `RECEIPT` | **Receive** (with or without a purchase order) |
| `SALE` | **Save delivery** on a sales order (stock leaves) |
| `RETURN_IN` | **Record return** (customer brings goods back) |
| `RETURN_OUT` | Allowed by the database, but no screen or operation in the code creates it (return to a supplier is NOT IMPLEMENTED in the user interface) |
| `TRANSFER_OUT` + `TRANSFER_IN` | **Transfer** between two locations |
| `ADJUSTMENT_IN` / `ADJUSTMENT_OUT` | **Adjust** (with a required reason) |

**Reservation and release** are not movements: confirming an order **reserves** (reserved goes up), cancelling **releases**
(reserved goes down), delivering reduces both on hand and reserved.

#### Stock & Locations page

Tabs: **Stock**, **Warehouses & locations** (**New warehouse**, **Add rack / shelf / bin**, **Edit**), **Movements** (When,
Product, Type, Location, Change, Note), **Integrity check** (only with `inventory.write`: proves the ledger adds up).

- **Receive**: Location, **Quantity received** (required), Note (delivery note, source) -> stock goes up.
- **Adjust**: Location, **Change in quantity** (required, + or −, not zero), **Reason** (required: "Give a reason for the stock
  adjustment.") -> refused if it would drop below what is reserved ("… of the stock here is reserved for orders; release those first.").
- **Transfer**: **From**, **To** (must be different: "Choose two different locations."), **Quantity** (at most what is available
  there: "Only … available to transfer from this location."), Note.

Stock is never typed in directly; every change is a recorded movement with your name and the time.

#### Scan / Lookup

"Scan a barcode or QR label with a scanner, or type a SKU or any part number, then press Enter." The product opens. If
nothing matches: "No product in My Products matches that code. Search the Reference Catalogue instead."

#### Purchase Orders

Statuses: `DRAFT`, `CONFIRMED`, `PARTIALLY_RECEIVED`, `RECEIVED`, `CLOSED`, `CANCELLED`.
1. **New purchase order**: Supplier, Expected date, Receive into (location), Notes, lines (products or a free-text line; at
   most 200 lines) -> **Save draft**.
2. **Confirm** -> `CONFIRMED`.
3. When goods arrive: **Receive goods** (quantity per line, pre-filled with what is outstanding) -> **Receive into stock**:
   stock goes up ("Enter what actually arrived. Stock increases when you save.") -> `PARTIALLY_RECEIVED` or `RECEIVED`.

---

## PART 10 -- Customers and suppliers

Lists: Code, Name, Contact, Phone, Email, Status, with search ("Search name, code, phone or email") and Active / Inactive.
**New customer**: Name (required), Contact person, Phone, Email, Country, Tax number, Currency (3 letters, e.g. AED), Payment
terms, Billing address, Shipping address, Credit limit, Notes, Status. **New supplier**: the same without addresses / credit
limit. A customer's page shows their quotations, orders and invoices; a supplier's page their purchase orders. Inactive
customers cannot be used on new documents ("That customer is inactive.").

---

## PART 11 -- Sales workflow (enquiry to delivery)

```
Customer ─► Enquiry ─► Quotation ─► Sales order ─► Delivery ─► Invoice ─► Payment
            (cart)      (PDF)        (reserves)     (stock out)   (PDF)     (paid)
```

#### Stage 1 -- Enquiry (what the customer asked for)
- **Start**: **Add to enquiry** on a catalogue result, a part page or a drawing. The part goes into **your enquiry cart**
  (only yours: "This enquiry cart belongs to another user.").
- **Cart** ("Parts collected for one customer request. Submit it to start a quotation."): columns Part number, Description,
  Vehicle, Qty; fields **Existing customer (optional)** or **Contact name** (one of them is needed: "Choose a customer or
  enter a contact name."), Phone, Email, **VIN / chassis number**, Notes; **Remove** an item; **Submit enquiry** (at least one
  part: "Add at least one part before submitting.").
- **Statuses**: `DRAFT` (the cart) → `SUBMITTED` → `QUOTED` (a quotation was made) / `CLOSED` / `CANCELLED`.
- **Permission**: `enquiries.write`. **Next**: open the enquiry, **Create quotation**.

#### Stage 2 -- Quotation (the offer)
- **From an enquiry**: **Create quotation** (choose the customer if the enquiry has none: "Not listed? Add the customer first.").
  "Quotation lines are priced automatically from My Products when the part number matches a product you stock."
- **Directly**: *Quotations > New quotation* (Customer, lines; a free-text line for an item not in My Products) → **Save draft**.
- **Rules**: at least one line; every line needs a description and a price above zero; at most 200 lines; the valid-until date
  cannot be in the past (validity comes from Shop settings, "Quotation valid for (days)").
- **Statuses**: `DRAFT` → **Issue to customer** → `ISSUED` → **Customer accepted** → `ACCEPTED` or **Customer rejected** →
  `REJECTED`; `EXPIRED` -- set automatically when quotations are listed or opened after the valid-until date; `CANCELLED`. **Edit lines** only while draft.
- **PDF**: the quotation page has a PDF link (`/quotations/:id/pdf`); whether it is offered before issuing is NOT CONFIRMED.
- **Permission**: `quotations.write`. **Next**: **Create order**.

#### Stage 3 -- Sales order
- **Create order** from an accepted quotation asks **"If there is not enough stock"**: *Do not create the order* or *Create it
  and back-order the shortfall*. The order **reserves** available stock.
- **Statuses**: `CONFIRMED` → `PARTIALLY_FULFILLED` → `FULFILLED` → `INVOICED`; `CANCELLED`.
- **Buttons**: **Reserve available stock** (try again for short lines), **Record delivery**, **Record return**, **Invoice delivered
  items**, **Cancel order** (releases reservations; a cancelled order cannot be invoiced).
- **Permission**: `orders.write`.

#### Stage 4 -- Delivery
- **Record delivery**: "Enter the quantity delivered now for each line. Stock is deducted when you save." → **Save delivery**:
  a `SALE` movement; on hand and reserved go down. Nothing to deliver: "Nothing to fulfil."
- **Record return**: the quantity returned and where to put it (**Return to location**) → `RETURN_IN`.



## PART 12 -- Invoices and payments

#### Stage 5 -- Invoice
- **Invoice delivered items** creates an invoice for what was delivered and not yet invoiced. Statuses: `ISSUED`,
  `PARTIALLY_PAID`, `PAID`, `VOID`. Due date from Shop settings ("Invoice due after (days)"). The invoice page has a PDF link (`/invoices/:id/pdf`).
- **Void** (with a **Reason**) cancels an invoice; a void invoice cannot take payments.
- **Permission**: `invoices.write`.

#### Stage 6 -- Payment
- On the invoice, **Record payment**: **Amount** (the label shows the current balance), **Method** (Cash, Bank transfer, Card,
  Other), **Reference (receipt / transfer no.)**, **Notes**. The invoice becomes `PARTIALLY_PAID` or `PAID` ("This invoice is
  already paid in full." if you try again).
- "Payments are permanent records. To correct a mistake, contact an administrator."
- **Permission**: `payments.record`.

**Finding an old transaction:** each list (Enquiries, Quotations, Orders, Invoices & Payments, Purchase Orders) has a search box
and status filter; a customer's page lists their documents; *Invoices* can show **Unpaid only**.

---

*Insights > Reports* -- "Calculated live from your stock movements, invoices and payments." Choose a report and a period
(**From**, **To**). Each report needs its permission:

| Report | Permission |
|---|---|
| Stock on hand, Low stock | `reports.inventory` |
| Inventory valuation (cost) | `reports.financial` |
| Sales by month, Sales by product, Customer activity, Outstanding invoices, Quotation conversion | `reports.sales` |
| Supplier overview | `suppliers.read` |

---

## PART 13 -- Audit

`Organization > Audit log` -- "A record of security-relevant actions taken in this organization." Columns Time, Action,
Resource, Result, Request ID; filters **Resource type**, **Action**, **Result** with **Apply** / **Clear**; paging. Needs
`audit.read` (otherwise a "you don't have permission" message). Entries cannot be edited. Spare Parts' actions appear here too
(`spareparts.…`).

---

Spare Parts' own audit log: (`audit.read`): who did what and when, with **Older / Newer** paging. The same events also appear in
  IntraForge's organization audit log (names starting with `spareparts.`).

---

## PART 14 -- Roles

Derived from the **server-side** authorization, not from hidden buttons:
- IntraForge roles and their permissions: `apps/backend/permissions/catalog.py` (SYSTEM_ROLES, PERMISSIONS).
- How IntraForge's `spareparts.*` capabilities become Spare Parts permissions: `spareparts-platform/src/server/platform/capabilities.ts`.
- Which Spare Parts action needs which permission: the Spare Parts project's generated `docs/generated/API_ROUTES.md` (every route checked on the server).

**Important:** a member added to an organization gets **no role**. Since version 1.2.0 an administrator gives one on the organization page: in the member list's **Roles** column choose **Give a role...**, pick the role, press **Give** (the **x** next to a role takes it away; the last Organization Administrator cannot be removed). The person who creates an organization automatically gets *Organization Administrator*.

#### Owner / Admin (Organization Administrator) -- IntraForge role `organization-administrator`

- **What the role means:** The owner / administrator of the company in IntraForge. Holds every permission except the platform-wide `system.admin`, including every Spare Parts permission.
- **Normal daily tasks:** Install and configure apps, add members, see everything, settings, reports, audit.
- **Actions denied:** Nothing inside the organization is denied (platform-wide administration is Super Administrator only).
- **IntraForge capabilities:** 61 permissions (all except `system.admin`)
- **Resulting Spare Parts permissions (33 of 33):** `audit.read`, `catalogue.admin`, `catalogue.import`, `catalogue.read`, `customers.read`, `customers.write`, `documents.read`, `documents.write`, `enquiries.read`, `enquiries.write`, `inventory.read`, `inventory.write`, `invoices.read`, `invoices.write`, `orders.read`, `orders.write`, `payments.record`, `products.cost.read`, `products.read`, `products.write`, `purchasing.read`, `purchasing.write`, `quotations.read`, `quotations.write`, `reports.financial`, `reports.inventory`, `reports.sales`, `settings.manage`, `settings.read`, `suppliers.read`, `suppliers.write`, `users.manage`, `warehouses.write`

#### Spare Parts Manager -- IntraForge role `spare-parts-manager`

- **What the role means:** Runs the Spare Parts application: every `spareparts.*` capability, nothing else in IntraForge.
- **Normal daily tasks:** Everything in Spare Parts: catalogue import, products with costs, stock, purchasing, sales, payments, reports, settings, audit.
- **Actions denied:** IntraForge administration (members, storage, databases...) unless also given other roles.
- **IntraForge capabilities:** `spareparts.view`, `spareparts.catalogue.read`, `spareparts.catalogue.import`, `spareparts.catalogue.manage`, `spareparts.products.read`, `spareparts.products.manage`, `spareparts.cost.read`, `spareparts.inventory.read`, `spareparts.inventory.manage`, `spareparts.sales.read`, `spareparts.sales.manage`, `spareparts.suppliers.manage`, `spareparts.purchasing.read`, `spareparts.purchasing.manage`, `spareparts.reports.inventory`, `spareparts.reports.sales`, `spareparts.reports.financial`, `spareparts.audit.read`, `spareparts.settings.manage`
- **Resulting Spare Parts permissions (33 of 33):** `audit.read`, `catalogue.admin`, `catalogue.import`, `catalogue.read`, `customers.read`, `customers.write`, `documents.read`, `documents.write`, `enquiries.read`, `enquiries.write`, `inventory.read`, `inventory.write`, `invoices.read`, `invoices.write`, `orders.read`, `orders.write`, `payments.record`, `products.cost.read`, `products.read`, `products.write`, `purchasing.read`, `purchasing.write`, `quotations.read`, `quotations.write`, `reports.financial`, `reports.inventory`, `reports.sales`, `settings.manage`, `settings.read`, `suppliers.read`, `suppliers.write`, `users.manage`, `warehouses.write`

#### Sales -- IntraForge role `spare-parts-sales`

- **What the role means:** Counter / sales staff.
- **Normal daily tasks:** Search the catalogue, look up products and stock, customers, enquiries, quotations, orders, deliveries, invoices, payments, sales reports.
- **Actions denied:** Cost prices and stock value, changing products, stock changes, suppliers and purchase orders, inventory and financial reports, settings, audit.
- **IntraForge capabilities:** `spareparts.view`, `spareparts.catalogue.read`, `spareparts.products.read`, `spareparts.inventory.read`, `spareparts.sales.read`, `spareparts.sales.manage`, `spareparts.reports.sales`
- **Resulting Spare Parts permissions (18 of 33):** `catalogue.read`, `customers.read`, `customers.write`, `documents.read`, `documents.write`, `enquiries.read`, `enquiries.write`, `inventory.read`, `invoices.read`, `invoices.write`, `orders.read`, `orders.write`, `payments.record`, `products.read`, `quotations.read`, `quotations.write`, `reports.sales`, `settings.read`

#### Inventory -- IntraForge role `spare-parts-inventory`

- **What the role means:** Store / purchasing staff.
- **Normal daily tasks:** Catalogue, products incl. cost prices, receive / adjust / transfer stock, warehouses and locations, suppliers (read), purchase orders, inventory reports.
- **Actions denied:** Customers and all sales documents, payments, sales and financial reports, creating suppliers, settings, audit.
- **IntraForge capabilities:** `spareparts.view`, `spareparts.catalogue.read`, `spareparts.products.read`, `spareparts.products.manage`, `spareparts.cost.read`, `spareparts.inventory.read`, `spareparts.inventory.manage`, `spareparts.purchasing.read`, `spareparts.purchasing.manage`, `spareparts.reports.inventory`
- **Resulting Spare Parts permissions (14 of 33):** `catalogue.read`, `documents.read`, `documents.write`, `inventory.read`, `inventory.write`, `products.cost.read`, `products.read`, `products.write`, `purchasing.read`, `purchasing.write`, `reports.inventory`, `settings.read`, `suppliers.read`, `warehouses.write`

#### Viewer -- IntraForge role `spare-parts-viewer`

- **What the role means:** Read-only access.
- **Normal daily tasks:** Look at the catalogue, products and stock levels.
- **Actions denied:** Every change, costs, customers and sales documents, reports, settings, audit.
- **IntraForge capabilities:** `spareparts.view`, `spareparts.catalogue.read`, `spareparts.products.read`, `spareparts.inventory.read`
- **Resulting Spare Parts permissions (5 of 33):** `catalogue.read`, `documents.read`, `inventory.read`, `products.read`, `settings.read`

## PART 15 -- Complete beginner workflow

A numbered sequence of screenshots that tells the story of one sale from start to finish. Every step below is supported by
the implementation (verified end to end by the automated browser test `apps/frontend/e2e/spare-parts-service-app.spec.ts`
and on the clean Windows test PC). Capture it in a **test organization with sample data**, not with real customers.

Prerequisite: an administrator has installed Spare Parts and the person capturing has the Spare Parts Manager (or Organization
Administrator) role, so every step is visible.

| # | Step | How to get there | What must be visible | Dialog open | File name |
|---|---|---|---|---|---|
| 01 | Start IntraForge | Double-click the **IntraForge** shortcut | Control Center status **Healthy**, Spare Parts listed with **Open** | -- | `WF-01-Control-Center-Healthy.png` |
| 02 | Login | Open IntraForge (`https://localhost:8443/login`) | Email, Password, sign-in button | -- | `WF-02-Login.png` |
| 03 | Dashboard | After signing in | Organizations, system health | -- | `WF-03-Dashboard.png` |
| 04 | Open the organization | Sidebar **Organizations** > the organization | Workspaces, members, buttons Apps / Teams / Units / Developer / Audit log | -- | `WF-04-Organization.png` |
| 05 | Applications | Sidebar **Apps** | Spare Parts card with status **Running**, **Open**, **Settings** | -- | `WF-05-Apps.png` |
| 06 | Open Spare Parts | **Open** | Spare Parts **Business overview** (no second sign-in) | -- | `WF-06-Spare-Parts-Dashboard.png` |
| 07 | Reference Catalogue | Menu **Reference Catalogue** | Search box, filters | -- | `WF-07-Reference-Catalogue.png` |
| 08 | Search OEM | Type a number without dashes, e.g. `1111036F00` > **Search** | Results with the formatted number `11110-36F00` | -- | `WF-08-Search-OEM.png` |
| 09 | Open the part | Click the part number | Part details, fitment, drawings, **IMPORT TO MY PRODUCTS**, **Add to enquiry** | -- | `WF-09-Part-Details.png` |
| 10 | Import to My Products | **IMPORT TO MY PRODUCTS** | Your SKU, Product name, Selling price, Cost price, Reorder level, Supplier, Store in, Quantity in stock now | **Import … to My Products** | `WF-10-Import-To-My-Products.png` |
| 11 | Complete the product | The new product page | Tabs Overview / Fitment / Stock / Supplier / OEM Reference / Sales / History; "Linked to the Reference Catalogue"; photo added | -- | `WF-11-Product-Details.png` |
| 12 | Receive stock | Product > **Stock** tab > **Receive** | Location, Quantity received, Note | **Receive stock — …** | `WF-12-Receive-Stock.png` |
| 13 | Stock after receiving | Product > **Stock** tab | On hand / Reserved / Available | -- | `WF-13-Stock-Levels.png` |
| 14 | Create customer | **Customers** > **New customer** | Name and details | **New customer** | `WF-14-New-Customer.png` |
| 15 | Create enquiry | Catalogue > **Add to enquiry**, then the cart | Cart lines; Existing customer / Contact name; **Submit enquiry** | -- | `WF-15-Enquiry-Cart.png` |
| 16 | Enquiry submitted | After **Submit enquiry** | Enquiry `ENQ-…` with **Create quotation** | -- | `WF-16-Enquiry.png` |
| 17 | Create quotation | **Create quotation** | Quotation `QUO-…`, lines priced from My Products, **Issue to customer** | -- | `WF-17-Quotation-Draft.png` |
| 18 | Quotation issued | **Issue to customer** | Status Issued, PDF link, **Customer accepted / rejected** | -- | `WF-18-Quotation-Issued.png` |
| 19 | Create order | **Customer accepted** > **Create order** | "If there is not enough stock" choice | **Create order** | `WF-19-Create-Order.png` |
| 20 | Order | After creating | Order `SO-…`/`ORD-…`, **Record delivery** | -- | `WF-20-Order.png` |
| 21 | Record delivery | **Record delivery** | Quantity per line | **Record delivery** | `WF-21-Record-Delivery.png` |
| 22 | Create invoice | **Invoice delivered items** | Invoice `INV-…` | -- | `WF-22-Invoice.png` |
| 23 | Record payment | **Record payment** | Amount (balance), Method, Reference, Notes | **Record payment** | `WF-23-Record-Payment.png` |
| 24 | Paid | After saving | Status **Paid** | -- | `WF-24-Invoice-Paid.png` |
| 25 | Review audit (app) | Menu **Audit log** | The day's actions | -- | `WF-25-Spare-Parts-Audit.png` |
| 26 | Review audit (IntraForge) | Organization > **Audit log** | `spareparts.…` events, filters | -- | `WF-26-IntraForge-Audit.png` |
| 27 | Logout | Spare Parts account menu > **Sign out**; IntraForge account menu > **Log out** | The sign-in page | -- | `WF-27-Logged-Out.png` |

Not included because it is not implemented in the user interface: switching on two-step sign-in (server API only), returning
goods to a supplier. (Assigning a role to a member has a screen since version 1.2.0: the Roles column of the member list.)

### First-day questions

Short answers to the first-day questions. Each answer is what the applications actually do. Words in **bold** are the exact
button or menu names on screen.

**How do I start IntraForge?**
It normally starts by itself when someone signs in to Windows (1-2 minutes). Otherwise double-click the **IntraForge**
shortcut (the Control Center) and press **Start**; when the status says **Healthy**, press **Open IntraForge**.

**How do I log in?**
In the browser at `https://localhost:8443`: **Email** and **Password**, then sign in. If your account has two-step sign-in,
also enter the 6-digit **Authenticator code**. (First time on this PC the browser warns about the certificate: *Advanced >
continue*.) New staff first create their own account (**Create account**: First name, Email, Password); an administrator then
adds them to the company and gives them a role.

**How do I open Spare Parts?**
Sidebar **Apps** > **Open** next to Spare Parts. No second sign-in. If Spare Parts is not listed, you have no role that allows
it yet -- ask the administrator.

**How do I search for an OEM part?**
Spare Parts > **Reference Catalogue** > type the part number in any format (with or without dashes or spaces) or a
description, vehicle or chassis > **Search**. Click a part number to see its fitment and drawings.

**How do I add a reference part to My Products?**
On the part's page press **IMPORT TO MY PRODUCTS**, fill **Your SKU** and **Product name** (required), selling price (and cost
price if you may see costs), reorder level, supplier, where it is stored and how many are on the shelf now, then save. (Needs
the inventory / manager role.)

**How do I check stock?**
**My Products** (columns Available and On hand), or open the product > **Stock** tab, or **Stock & Locations > Stock**
(On hand, Reserved, Available per location). *Available = on hand − reserved.*

**How do I receive stock?**
With a purchase order: **Purchase Orders** > the order > **Receive goods** > enter what arrived > **Receive into stock**.
Without one: on the product (or Stock & Locations) press **Receive**, choose the location, **Quantity received**, a note
(delivery note number) > save. Stock goes up.

**How do I find a product's location?**
Open the product > **Stock** tab: warehouse and location (rack / shelf / bin) with the quantities. Or scan its label in
**Scan / Lookup** to open it.

**How do I add a customer?**
**Customers** > **New customer** > **Name** (required) and the details you have > save.

**How do I create an enquiry?**
In the Reference Catalogue (a result, a part page or a drawing) press **Add to enquiry** for each part. Open the enquiry cart,
choose the **Existing customer** or type a **Contact name**, add phone / email / VIN if useful > **Submit enquiry**.

**How do I create a quotation?**
**Enquiries** > open the enquiry > **Create quotation** (lines are priced from My Products when the part number matches). Check
it, then **Issue to customer**; the quotation has a PDF. Or **Quotations** > **New quotation** directly.

**How do I create an order?**
When the customer agrees: on the quotation press **Customer accepted**, then **Create order**, and choose what to do if stock
is short. The order reserves the stock. When the goods leave: **Record delivery** > enter quantities > **Save delivery**.

**How do I create an invoice?**
On the order: **Invoice delivered items**. The invoice is created for what was delivered; it has a PDF.

**How do I record payment?**
On the invoice: **Record payment** > **Amount**, **Method** (Cash, Bank transfer, Card, Other), **Reference**, notes > save. The
invoice becomes *Partially paid* or *Paid*. Payments cannot be undone -- if you made a mistake, tell an administrator.

**How do I find an old transaction?**
Open the list (**Enquiries**, **Quotations**, **Orders**, **Invoices & Payments**, **Purchase Orders**) and use the search box and
the status filter; or open the **customer** to see all their quotations, orders and invoices. Managers can also look in the
**Audit log**.

**How do I log out?**
In Spare Parts: account menu > **Sign out** (since 1.2.0 this also signs you out of IntraForge and shows the shop's sign-in
page). In IntraForge: account menu > **Log out** (this also ends your Spare Parts session).

**Something does not work?** See LEVEL1_TROUBLESHOOTING.md.

## PART 16 -- Glossary

Simple meanings of the words used in IntraForge and Spare Parts, as the applications use them.

### IntraForge

| Term | Meaning |
|---|---|
| **IntraForge** | The private business system on the shop's PC (`https://localhost:8443`). |
| **Control Center** | The Windows program behind the **IntraForge** shortcut: status, start / stop, backup, restore, diagnostics, uninstall. Works even when IntraForge is not running. |
| **Organization** | A company inside IntraForge. Everything belongs to one organization; organizations are kept apart. |
| **Member** | A person who belongs to an organization. Must have an IntraForge account first. |
| **Account** | A person's sign-in (email + password, optionally a two-step code). |
| **Two-step sign-in (MFA)** | A 6-digit code from an authenticator app asked for at sign-in, when switched on for the account. |
| **Role** | A named set of permissions given to a member (for example *Organization Administrator*, *Spare Parts Sales*). |
| **Permission / Capability** | One specific right, for example `storage.write` or `spareparts.sales.manage`. The server checks it for every action. |
| **Default-deny** | Without a role or share that allows something, it is not allowed. |
| **Team** | A group of members, used to share with several people at once. |
| **Unit (organizational unit)** | A part of the organization's structure, such as a branch or department. |
| **Workspace** | A group of projects inside an organization. |
| **Project** | Holds buckets, databases, connected databases and dashboards. |
| **Bucket / Storage** | A file area for uploading and downloading files. |
| **Database (tenant database)** | A real database of the organization where you design tables. |
| **Table, column, row** | A table holds data in rows; columns are its fields. |
| **Connected database** | A read-only link to an external PostgreSQL database. |
| **CSV import** | Loading a CSV file into a table. |
| **Analytics / Dashboard** | Statistics on a table; a dashboard keeps live widgets. |
| **Share** | Giving one member or team access (read only or read & write) to one thing. |
| **Audit / Audit log** | The unchangeable history of who did what, when, and whether it was allowed. |
| **Apps** | The page where installed applications (Spare Parts) are opened and installed. |
| **Service application** | A separate program IntraForge installs, opens and backs up (Spare Parts). |
| **Template / Installed app (application platform)** | A design for a business application, and a copy of it installed in a project. Different from the Spare Parts service application. |
| **Application (developer)** | A registered outside program that connects to IntraForge with a credential. |
| **Credential / token** | The secret an outside program uses; shown only once; can be rotated or revoked. |
| **Environment** | Development, Staging or Production setup of an application, with its variables, secrets and webhooks. |
| **Webhook** | IntraForge sending an event message to another system (signed, at least once). |
| **Backup** | Three encrypted files (company data, business records, stored files) made daily. |
| **Restore** | Putting the shop back to a backup; a safety backup is taken first. |
| **Diagnostics** | A zip for support without passwords or keys. |
| **Keys file** | The shop's secret key file; needed to read its backups. |

### Spare Parts

| Term | Meaning |
|---|---|
| **Reference Catalogue** | Manufacturer / supplier reference data: part numbers, fitment, drawings. No shop prices or stock. |
| **OEM** | Original Equipment Manufacturer -- the vehicle maker's own part number and part. |
| **OEM number** | The manufacturer's part number. Search finds it with or without dashes or spaces. |
| **PNC** | The part group code from the manufacturer's catalogue (the import calls it "PNC / part group code"); it groups the same part on drawings. |
| **Fitment** | Which vehicles a part fits: make, model, chassis, engine, production dates, market. |
| **Chassis / frame** | A vehicle's model code (for example AT151). |
| **VIN** | Vehicle identification number. |
| **Drawing, callout** | An exploded-view picture of an assembly; callouts are the numbers pointing to parts. |
| **Supersession / superseded** | A part replaced by a newer number; status *Superseded*. |
| **Source** | Where catalogue data came from. |
| **Reference price** | A price from the source -- information only, not the shop's selling price. |
| **Import to My Products** | Creating a shop product from a reference part. |
| **My Products** | The parts the shop stocks and sells. |
| **SKU** | The shop's own unique product code. |
| **Part number types** | OEM, Aftermarket, Supplier, Cross reference, Replacement, Previous, Interchange, Other. |
| **Selling price / Cost price** | What the customer pays / what the shop pays (cost visible only with the cost permission). |
| **Reorder level** | At or below this, a product is *Low stock* / *Needs reordering*. |
| **Warehouse** | A store or building. |
| **Location; Rack, Shelf, Bin** | A place in a warehouse, made of rack, shelf and bin. |
| **On hand** | Units physically there. |
| **Reserved** | Units set aside for confirmed orders not yet delivered. |
| **Available** | On hand minus reserved. |
| **Stock movement** | A recorded change of stock: opening balance, receipt, sale, return in, transfer out / in, adjustment in / out. |
| **Receive** | Recording goods that arrived (stock goes up). |
| **Adjustment** | A correction of the stock count, always with a reason. |
| **Transfer** | Moving stock from one location to another. |
| **Reservation / release** | Setting stock aside for an order / freeing it when the order is cancelled. |
| **Integrity check** | A check that the stock ledger adds up. |
| **Supplier** | A company the shop buys from. |
| **Purchase order (PO)** | What the shop orders from a supplier; received when goods arrive. |
| **Customer** | A person or company the shop sells to. |
| **Enquiry** | What a customer asked for (parts, vehicle); collected in the enquiry cart. |
| **Quotation** | The price offer to the customer, issued as a PDF; accepted or rejected. |
| **Sales order** | The confirmed order; reserves stock. |
| **Delivery** | Goods leaving the shop for an order (stock goes down). |
| **Return** | Goods the customer brings back (stock goes up). |
| **Invoice** | The bill for delivered items. |
| **Payment** | Money received for an invoice (cash, bank transfer, card, other). Payments are permanent. |
| **Void** | Cancelling an invoice (with a reason). |
| **Back-order** | Creating an order although part of it is not in stock yet. |
| **Scan / Lookup** | Opening a product by scanning its barcode / QR label or typing a code. |
| **Label (barcode / QR)** | A printable product label; scanning it opens the product. |
| **Audit log (Spare Parts)** | The app's own history; also sent to IntraForge's audit log. |
| **Statuses** | Enquiry: Draft, Submitted, Quoted, Closed, Cancelled. Quotation: Draft, Issued, Accepted, Rejected, Expired, Cancelled. Order: Confirmed, Partially fulfilled, Fulfilled, Invoiced, Cancelled. Invoice: Issued, Partially paid, Paid, Void. Purchase order: Draft, Confirmed, Partially received, Received, Closed, Cancelled. Customer / supplier / product: Active, Inactive. |

## PART 17 -- Troubleshooting

Real messages from the applications and what to do. Fixes are only those the applications support. Appendix: every message found in the code.

### IntraForge does not open in the browser

- **What it means:** IntraForge (or Docker, which it runs on) is not running, or still starting.
- **What to check:** Open the **IntraForge** shortcut (Control Center): what is the status? Starting / Stopped / Failed / Degraded?
- **How to fix:** Stopped: press **Start**. Starting: wait 1-2 minutes. Degraded or Failed: **Restart services**.
- **When to contact an administrator:** If it stays Failed or Repair required: press **Diagnostics** and send the zip (no passwords or keys inside).

### The browser says the connection is not private / certificate warning

- **What it means:** IntraForge uses the PC's own certificate.
- **What to check:** The address is `https://localhost:8443`.
- **How to fix:** Choose *Advanced > continue*. This is expected on this PC.
- **When to contact an administrator:** If the address is different from localhost.

### "Invalid credentials." when signing in

- **What it means:** The email or password is wrong.
- **What to check:** Caps Lock; the email you registered with.
- **How to fix:** Type them again. There is no password-reset screen in IntraForge.
- **When to contact an administrator:** If you forgot the password: an administrator. (A reset screen is NOT IMPLEMENTED.)

### Signing in is refused after several tries

- **What it means:** Sign-in is limited to 10 attempts per minute on purpose (security).
- **What to check:** How many attempts in the last minute.
- **How to fix:** Wait one minute, then try once more carefully.
- **When to contact an administrator:** If it continues after waiting.

### "This account has MFA enabled — enter the 6-digit code from your authenticator app."

- **What it means:** Two-step sign-in is on for your account.
- **What to check:** The 6-digit code in your authenticator app (it changes every 30 seconds) and the phone's clock.
- **How to fix:** Enter the current code.
- **When to contact an administrator:** If you lost the phone with the authenticator.

### "You don't have permission …" (IntraForge pages)

- **What it means:** Your role does not include the permission this action needs; the server refused it.
- **What to check:** Which action / page; see LEVEL1_ROLES.md.
- **How to fix:** Ask an administrator to give you the right role.
- **When to contact an administrator:** Always -- roles are given by an administrator (organization page > member list > Roles column, since 1.2.0).

### A page says something "wasn't found" / "not found"

- **What it means:** The item does not exist, or it belongs to an organization you are not a member of (shown as not found on purpose).
- **What to check:** The link / address; your organization.
- **How to fix:** Open it from the lists instead of an old link.
- **When to contact an administrator:** If you should be a member of that organization.

### Spare Parts is not in Apps

- **What it means:** It is not installed in your organization, or you have no role that allows opening it.
- **What to check:** Apps page; ask whether Spare Parts is installed.
- **How to fix:** An administrator installs it (Apps > Install) or gives you a Spare Parts role.
- **When to contact an administrator:** Yes.

### A Spare Parts menu item is missing

- **What it means:** Each menu item needs its own permission; your role does not include it.
- **What to check:** LEVEL1_ROLES.md for your role.
- **How to fix:** Nothing to fix -- it is by design.
- **When to contact an administrator:** If your work needs it.

### "People, passwords and roles are managed in IntraForge (Organization > Members and Roles)."

- **What it means:** Inside IntraForge, Spare Parts' Users page cannot add or change people.
- **What to check:** --
- **How to fix:** Use IntraForge (add the member there).
- **When to contact an administrator:** To give roles (organization page > Roles column).

### Spare Parts says "Insufficient available stock for … requested, … available."

- **What it means:** More is ordered than is available (on hand minus reserved).
- **What to check:** Stock & Locations: On hand, Reserved, Available.
- **How to fix:** Receive stock first, or create the order with *Create it and back-order the shortfall*.
- **When to contact an administrator:** If the stock count looks wrong.

### "Give a reason for the stock adjustment."

- **What it means:** An adjustment always needs a reason.
- **What to check:** The Reason field.
- **How to fix:** Write why (count difference, damage...).
- **When to contact an administrator:** --

### "… of the stock here is reserved for orders; release those first."

- **What it means:** The adjustment would leave less than what is reserved.
- **What to check:** Reserved on that location.
- **How to fix:** Deliver or cancel the order first, or adjust a smaller amount.
- **When to contact an administrator:** If unsure which order.

### "Choose two different locations." / "Only … available to transfer from this location."

- **What it means:** A transfer needs different From / To and at most the available quantity.
- **What to check:** From, To, Quantity.
- **How to fix:** Correct them.
- **When to contact an administrator:** --

### "SKU … already exists."

- **What it means:** Every shop product needs a unique SKU.
- **What to check:** Search My Products for that SKU.
- **How to fix:** Use a different SKU or open the existing product.
- **When to contact an administrator:** --

### "Choose a customer or enter a contact name."

- **What it means:** An enquiry needs a customer or a contact name.
- **What to check:** Existing customer / Contact name.
- **How to fix:** Fill one of them.
- **When to contact an administrator:** --

### "Add at least one part before submitting."

- **What it means:** The enquiry cart is empty.
- **What to check:** The cart.
- **How to fix:** Add parts with *Add to enquiry*.
- **When to contact an administrator:** --

### "Line … needs a description." / "Line … needs a price greater than zero."

- **What it means:** Every document line needs a description and a price above zero.
- **What to check:** The lines of the quotation / purchase order.
- **How to fix:** Complete the line or remove it.
- **When to contact an administrator:** --

### "The valid-until date is in the past."

- **What it means:** A quotation cannot be issued after its validity ended.
- **What to check:** Valid until.
- **How to fix:** Edit the quotation's validity, then issue.
- **When to contact an administrator:** --

### "That customer is inactive."

- **What it means:** Inactive customers cannot be used on new documents.
- **What to check:** The customer's status.
- **How to fix:** Set the customer Active (Edit).
- **When to contact an administrator:** --

### "A cancelled order cannot be invoiced."

- **What it means:** The order was cancelled.
- **What to check:** Order status.
- **How to fix:** Create a new quotation / order.
- **When to contact an administrator:** --

### "A void invoice cannot take payments." / "This invoice is already paid in full."

- **What it means:** The invoice is void or already paid.
- **What to check:** Invoice status and balance.
- **How to fix:** Nothing to pay.
- **When to contact an administrator:** If a payment was recorded by mistake: "Payments are permanent records. To correct a mistake, contact an administrator."

### "You may not change cost prices."

- **What it means:** Your role cannot see / change costs.
- **What to check:** --
- **How to fix:** Ask someone with the cost permission (Inventory / Manager).
- **When to contact an administrator:** --

### "Only PNG, JPEG, GIF or WebP images are accepted."

- **What it means:** Product photos must be one of these formats.
- **What to check:** The file type.
- **How to fix:** Save the photo as JPEG or PNG.
- **When to contact an administrator:** --

### Catalogue import refused without the confirmation

- **What it means:** You must confirm the organisation may use the data.
- **What to check:** The confirmation checkbox.
- **How to fix:** Tick it if true.
- **When to contact an administrator:** If you are not sure you may use the data.

### "No product in My Products matches that code. Search the Reference Catalogue instead."

- **What it means:** The scanned / typed code is not a shop product.
- **What to check:** The code.
- **How to fix:** Search the Reference Catalogue; import the part to My Products if the shop sells it.
- **When to contact an administrator:** --

### Stopped working after Windows restarted

- **What it means:** IntraForge starts at Windows **sign-in**, not at boot.
- **What to check:** Is someone signed in to Windows?
- **How to fix:** Sign in; wait 1-2 minutes.
- **When to contact an administrator:** If it does not come back: Diagnostics.

### A backup failed (Control Center shows the last backup in red)

- **What it means:** The daily backup did not complete.
- **What to check:** Free disk space; the message in the Control Center.
- **How to fix:** Press **Backup now**.
- **When to contact an administrator:** If it fails again: Diagnostics.

### A restore failed

- **What it means:** The chosen backup could not be restored; the shop was put back as it was automatically.
- **What to check:** The message: "Nothing was lost: IntraForge is running again with the data it had before this restore."
- **How to fix:** Use another backup; check it first with *Check this backup*.
- **When to contact an administrator:** Send Diagnostics.

The full list of messages from the code: LEVEL1_TROUBLESHOOTING.md, appendices A and B.
