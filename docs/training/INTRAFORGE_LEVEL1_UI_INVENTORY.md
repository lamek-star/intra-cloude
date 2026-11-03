# IntraForge -- Level-1 UI inventory

Every page of the IntraForge web interface (`apps/frontend/src/app`, commit `cb32c20`). IntraForge pages do not hide controls by permission in the browser; **the server decides**: a refused action shows a "you don't have permission" message (HTTP 403); a resource of an organization you are not a member of is answered as not found (HTTP 404). For each page the backend areas it calls and the permission codes those areas check are listed (evidence: the Django apps' code).

Generated from the code by an evidence extractor; counts are of controls found in the source. Marked **NOT CONFIRMED** where the code alone does not establish something.

## Landing page

**ROUTE:** `/`  
**PURPOSE:** Public start page shown before signing in; leads to sign-in or registration.  
**WHO USES IT:** Anyone opening IntraForge  
**PERMISSION / CAPABILITY:** public; membership of the organization  
**HOW USER GETS THERE:** Open https://localhost:8443/  
**BUTTONS:** Get Started, View Demo, Go home  
**ACTIONS:**  
- Get Started -- Navigates to registration / sign-in.
- View Demo -- Navigates.
- Go home -- Navigates.
**RELATED PAGES (links on the page):** `/login`, `/register`, `/dashboard`  
**NORMAL NEXT STEP:** Sign in  
**EVIDENCE:** `app/page.tsx`, `app/not-found.tsx`, `lib/auth-context.tsx`

## Sign in

**ROUTE:** `/login`  
**PURPOSE:** Signs a person in with email and password, and asks for a 6-digit authenticator code when two-step sign-in is switched on.  
**WHO USES IT:** Every user  
**PERMISSION / CAPABILITY:** public; membership of the organization  
**HOW USER GETS THERE:** Open IntraForge; you are sent here when not signed in  
**FIELDS:** Email (email, required); Password (password, required); Authenticator code (text, required)  
**BUTTONS:** Verify / Sign in  
**FILTERS / SEARCH:** search box "you@example.com"; search box "••••••••"; search box "123456"  
**ACTIONS:**  
- Verify / Sign in -- Checks email and password (and the authenticator code when asked); max 10 attempts a minute.
**NORMAL NEXT STEP:** Dashboard  
**EVIDENCE:** `app/login/page.tsx`, `lib/auth-context.tsx`, `lib/safe-next.ts`

## Create account

**ROUTE:** `/register`  
**PURPOSE:** Creates a new IntraForge account (the first account on a new installation becomes its first user).  
**WHO USES IT:** New users  
**PERMISSION / CAPABILITY:** public; membership of the organization  
**HOW USER GETS THERE:** Sign-in page > create an account  
**FIELDS:** First name (text); Email (email, required); Password (password, required)  
**BUTTONS:** Create account  
**FILTERS / SEARCH:** search box "Ada"; search box "you@example.com"; search box "At least 12 characters"  
**ACTIONS:**  
- Create account -- Registers the account with first name, email and password, and signs you in.
**NORMAL NEXT STEP:** Welcome / create an organization  
**EVIDENCE:** `app/register/page.tsx`, `lib/auth-context.tsx`, `lib/safe-next.ts`

## Welcome

**ROUTE:** `/welcome`  
**PURPOSE:** First-run welcome screen after creating an account.  
**WHO USES IT:** New users  
**PERMISSION / CAPABILITY:** signed-in user; membership of the organization  
**HOW USER GETS THERE:** Shown after registering  
**BUTTONS:** Continue, Create, Hide / How?, Organizations  
**ACTIONS:**  
- Continue -- --
- Create -- Creates it.
- Hide / How? -- Shows help text.
- Organizations -- Navigates.
**NORMAL NEXT STEP:** Create an organization  
**EVIDENCE:** `app/welcome/page.tsx`, `lib/auth-context.tsx`, `lib/safe-next.ts`

## Dashboard

**ROUTE:** `/dashboard`  
**PURPOSE:** Overview after signing in: your organizations (with workspace counts), the system's health and readiness, and -- when you belong to exactly one organization -- its latest audit events.  
**WHO USES IT:** Every signed-in user  
**PERMISSION / CAPABILITY:** signed-in user; server areas `accounts, organizations, workspaces` check: `permissions.manage`, `users.manage`, `workspace.manage`  
**HOW USER GETS THERE:** Sidebar > Dashboard (also shown right after sign-in)  
**RELATED PAGES (links on the page):** `/orgs/:id`  
**NORMAL NEXT STEP:** Open an organization or Apps  
**EVIDENCE:** `app/(app)/dashboard/page.tsx`, `lib/auth-context.tsx`

## Apps

**ROUTE:** `/apps`  
**PURPOSE:** Lists the service applications installed in your organizations (today: Spare Parts) with their live status; install, open and configure them.  
**WHO USES IT:** Everyone who may open an app; administrators to install  
**PERMISSION / CAPABILITY:** signed-in user; server areas `organizations, service_apps` check: `app_instance.manage`, `permissions.manage`, `spareparts.settings.manage`, `spareparts.view`, `users.manage`  
**HOW USER GETS THERE:** Sidebar > Apps  
**FIELDS:** Organization (select, in dialog: Install …); Shop name (text, required, in dialog: Install …); Currency (text, required, in dialog: Install …)  
**BUTTONS:** Open, Settings, Install, Cancel  
**FILTERS / SEARCH:** search box "The name on your quotations and invoices"  
**DIALOGS:** Install …  
**ACTIONS:**  
- Open -- Navigates to it.
- Settings -- Navigates to Settings.
- Install -- Installs it into the chosen organization / project.
- Cancel -- Nothing is saved.
**RELATED PAGES (links on the page):** `/service-apps/:id/settings`  
**NORMAL NEXT STEP:** Open Spare Parts  
**EVIDENCE:** `app/(app)/apps/page.tsx`, `app/(app)/apps/_client.tsx`, `lib/service-apps.ts`

## Open application

**ROUTE:** `/service-apps/[appId]/open`  
**PURPOSE:** Hand-over page: creates the app session and sends you into the application (no second sign-in).  
**WHO USES IT:** App users  
**PERMISSION / CAPABILITY:** signed-in user; server areas `service_apps` check: `app_instance.manage`, `spareparts.settings.manage`, `spareparts.view`  
**HOW USER GETS THERE:** Apps > Open  
**BUTTONS:** Back to Apps  
**ACTIONS:**  
- Back to Apps -- Navigates.
**RELATED PAGES (links on the page):** `/apps`  
**NORMAL NEXT STEP:** The application opens  
**EVIDENCE:** `app/(app)/service-apps/[appId]/open/page.tsx`, `app/(app)/service-apps/[appId]/open/_client.tsx`, `lib/service-apps.ts`

## Application settings

**ROUTE:** `/service-apps/[appId]/settings`  
**PURPOSE:** Settings of one installed service application: name, shop details, availability, removal (keep data or delete data after a backup), reinstate.  
**WHO USES IT:** Organization administrators / app managers  
**PERMISSION / CAPABILITY:** signed-in user; server areas `service_apps` check: `app_instance.manage`, `spareparts.settings.manage`, `spareparts.view`  
**HOW USER GETS THERE:** Apps > Settings  
**FIELDS:** Name in Apps (text, required); Currency (text); Default tax rate (%) (number); Quotations valid for (days) (number); Invoices due after (days) (number); Also delete all of its data (products, stock, customers, documents, catalogue and files). A backup is taken first; nothing is deleted if the backup fails. (checkbox); Type … to confirm (text)  
**BUTTONS:** Save, Disable / Enable, Remove..., Back up, then delete everything / Remove, keep data, Cancel, Reinstate  
**ACTIONS:**  
- Save -- The values are sent to the server and validated; on success the dialog closes and the list refreshes; on a validation error the message is shown and nothing is saved.
- Disable / Enable -- Re-enables it.
- Remove... -- Shows a preview of what is affected; keep data, or (option) delete data after a backup -- nothing is deleted if the backup fails.
- Back up, then delete everything / Remove, keep data -- Closes and hides it; Reinstate brings it back with everything.
- Cancel -- Nothing is saved.
- Reinstate -- Reinstates it.
**NORMAL NEXT STEP:** Back to Apps  
**EVIDENCE:** `app/(app)/service-apps/[appId]/settings/page.tsx`, `app/(app)/service-apps/[appId]/settings/_client.tsx`, `lib/service-apps.ts`

## Organizations

**ROUTE:** `/orgs`  
**PURPOSE:** Lists the organizations (companies) you belong to; create a new one.  
**WHO USES IT:** Every user  
**PERMISSION / CAPABILITY:** signed-in user; server areas `organizations` check: `permissions.manage`, `users.manage`  
**HOW USER GETS THERE:** Sidebar > Organizations  
**FIELDS:** Name (text, required, in dialog: New organization)  
**BUTTONS:** New organization, Cancel, Create  
**FILTERS / SEARCH:** search box "Acme Corp"  
**DIALOGS:** New organization  
**ACTIONS:**  
- New organization -- Opens the New organization dialog (Name).
- Cancel -- Nothing is saved.
- Create -- Creates it.
**RELATED PAGES (links on the page):** `/orgs/:id`  
**NORMAL NEXT STEP:** Open an organization  
**EVIDENCE:** `app/(app)/orgs/page.tsx`, `lib/safe-next.ts`

## Organization

**ROUTE:** `/orgs/[orgId]`  
**PURPOSE:** One organization: its workspaces, members and roles, and links to teams, units, applications (developer) and the audit log.  
**WHO USES IT:** Members; administrators manage members and roles  
**PERMISSION / CAPABILITY:** signed-in user; server areas `organizations, workspaces` check: `permissions.manage`, `users.manage`, `workspace.manage`  
**HOW USER GETS THERE:** Organizations > click an organization  
**FIELDS:** Name (text, required, in dialog: New workspace); Email of an existing user (email, required, in dialog: Add member)  
**BUTTONS:** Apps, Developer, Teams, Units, Audit log, New workspace, Add member, Cancel, Create, Add  
**TABLE 1:** columns Email | Name | Status | Team  (`app/(app)/orgs/[orgId]/_client.tsx:147`)  
**FILTERS / SEARCH:** search box "Engineering"; search box "teammate@example.com"  
**DIALOGS:** New workspace, Add member  
**ACTIONS:**  
- Apps -- Navigates.
- Developer -- Navigates.
- Teams -- Navigates.
- Units -- Navigates.
- Audit log -- Navigates (audit.read).
- New workspace -- Opens the dialog (workspace.manage).
- Add member -- Opens the dialog: email of an existing user / member.
- Cancel -- Nothing is saved.
- Create -- Creates it.
- Add -- Adds it.
**RELATED PAGES (links on the page):** `/orgs/:id/app-templates`, `/orgs/:id/developer`, `/orgs/:id/teams`, `/orgs/:id/units`, `/orgs/:id/audit`, `/orgs/:id/workspaces/:id`  
**NORMAL NEXT STEP:** Open a workspace or manage members  
**EVIDENCE:** `app/(app)/orgs/[orgId]/page.tsx`, `app/(app)/orgs/[orgId]/_client.tsx`

## Teams

**ROUTE:** `/orgs/[orgId]/teams`  
**PURPOSE:** Groups of members inside an organization; add and remove team members.  
**WHO USES IT:** Administrators  
**PERMISSION / CAPABILITY:** signed-in user; server areas `organizations` check: `permissions.manage`, `users.manage`  
**HOW USER GETS THERE:** Organization > Teams  
**FIELDS:** Name (text, required, in dialog: New team); Member (select, in dialog: Add member to …)  
**BUTTONS:** New team, Add member, Remove, Cancel, Create, Add  
**FILTERS / SEARCH:** search box "Platform"  
**DIALOGS:** New team, Add member to …  
**ACTIONS:**  
- New team -- Opens the dialog (users.manage).
- Add member -- Opens the dialog: email of an existing user / member.
- Remove -- The item is removed.
- Cancel -- Nothing is saved.
- Create -- Creates it.
- Add -- Adds it.
**NORMAL NEXT STEP:** Share resources with a team  
**EVIDENCE:** `app/(app)/orgs/[orgId]/teams/page.tsx`, `app/(app)/orgs/[orgId]/teams/_client.tsx`

## Organizational units

**ROUTE:** `/orgs/[orgId]/units`  
**PURPOSE:** The organization's structure (branches, departments...): create, rename, nest units and manage their members.  
**WHO USES IT:** Administrators  
**PERMISSION / CAPABILITY:** signed-in user; server areas `org_units, organizations` check: `org_unit.manage`, `org_unit.membership.manage`, `org_unit.read`, `permissions.manage`, `users.manage`  
**HOW USER GETS THERE:** Organization > Units  
**FIELDS:** Name (text, required); Type (text, required); Name (text, required, in dialog: Edit …); Type (text, required, in dialog: Edit …); Parent (select, in dialog: Edit …); Add member (select, in dialog: Members of …)  
**BUTTONS:** Add sub-unit, Members, Edit, Delete, New unit, Cancel, Create, Save, Remove, Add  
**FILTERS / SEARCH:** search box "Downtown Branch"; search box "branch, department, warehouse, team..."  
**DIALOGS:** Edit …, Members of …  
**CONFIRMATIONS:** "Delete "  
**ACTIONS:**  
- Add sub-unit -- Opens the dialog.
- Members -- Opens the members dialog.
- Edit -- Opens a dialog with the current values.
- Delete -- The item is deleted on the server.
- New unit -- Opens the dialog (org_unit.manage).
- Cancel -- Nothing is saved.
- Create -- Creates it.
- Save -- The values are sent to the server and validated; on success the dialog closes and the list refreshes; on a validation error the message is shown and nothing is saved.
- Remove -- The item is removed.
- Add -- Adds it.
**NORMAL NEXT STEP:** Give unit-scoped access  
**EVIDENCE:** `app/(app)/orgs/[orgId]/units/page.tsx`, `app/(app)/orgs/[orgId]/units/_client.tsx`

## Audit log (organization)

**ROUTE:** `/orgs/[orgId]/audit`  
**PURPOSE:** The unchangeable history of actions in the organization, filterable by resource type, action and result, with paging.  
**WHO USES IT:** Administrators and auditors (audit.read)  
**PERMISSION / CAPABILITY:** signed-in user; server areas `organizations` check: `permissions.manage`, `users.manage`  
**HOW USER GETS THERE:** Organization > Audit log  
**FIELDS:** Resource type (text); Action (text); Result (select)  
**BUTTONS:** Apply, Clear, Previous, Next  
**TABLE 1:** columns Time | Action | Resource | Result | Request ID  (`app/(app)/orgs/[orgId]/audit/_client.tsx:201`)  
**FILTERS / SEARCH:** search box "e.g. bucket, file, organization"; search box "e.g. file.upload"  
**ACTIONS:**  
- Apply -- Applies it (safe additions only; local changes are never overwritten).
- Clear -- All filters reset.
- Previous -- Loads the previous page.
- Next -- Loads the next page.
**NORMAL NEXT STEP:** Investigate an event  
**EVIDENCE:** `app/(app)/orgs/[orgId]/audit/page.tsx`, `app/(app)/orgs/[orgId]/audit/_client.tsx`

## Business app templates

**ROUTE:** `/orgs/[orgId]/app-templates`  
**PURPOSE:** Templates of the application platform owned by this organization; create a new template.  
**WHO USES IT:** Administrators / builders  
**PERMISSION / CAPABILITY:** signed-in user; server areas `app_platform, organizations` check: `app_instance.manage`, `app_instance.read`, `app_instance.schema.manage`, `app_instance.workflow.approve`, `app_template.manage`, `app_template.publish`, `app_template.read`, `database.create`, `database.read`, `database.schema.manage`, `database.write`, `inventory.adjust`, `inventory.receive`, `inventory.sell`, `inventory.transfer`, `permissions.manage`, `sharing.manage`, `storage.read`, `users.manage`  
**HOW USER GETS THERE:** Organization > templates  
**FIELDS:** Name (text, required, in dialog: New app template); Description (textarea, in dialog: New app template)  
**BUTTONS:** New template, Cancel, Create  
**FILTERS / SEARCH:** search box "Inventory tracker"; status filter (warning)  
**DIALOGS:** New app template  
**STATUSES:** warning  
**ACTIONS:**  
- New template -- Opens the dialog (app_template.manage).
- Cancel -- Nothing is saved.
- Create -- Creates it.
**RELATED PAGES (links on the page):** `/app-templates/:id`  
**NORMAL NEXT STEP:** Open a template  
**EVIDENCE:** `app/(app)/orgs/[orgId]/app-templates/page.tsx`, `app/(app)/orgs/[orgId]/app-templates/_client.tsx`

## Workspace

**ROUTE:** `/orgs/[orgId]/workspaces/[workspaceId]`  
**PURPOSE:** A workspace groups projects; create projects here.  
**WHO USES IT:** Members  
**PERMISSION / CAPABILITY:** signed-in user; server areas `organizations, workspaces` check: `permissions.manage`, `users.manage`, `workspace.manage`  
**HOW USER GETS THERE:** Organization > a workspace  
**FIELDS:** Name (text, required, in dialog: New project)  
**BUTTONS:** New project, Cancel, Create  
**FILTERS / SEARCH:** search box "Demo Project"  
**DIALOGS:** New project  
**ACTIONS:**  
- New project -- Opens the dialog (workspace.manage).
- Cancel -- Nothing is saved.
- Create -- Creates it.
**RELATED PAGES (links on the page):** `/projects/:id`  
**NORMAL NEXT STEP:** Open a project  
**EVIDENCE:** `app/(app)/orgs/[orgId]/workspaces/[workspaceId]/page.tsx`, `app/(app)/orgs/[orgId]/workspaces/[workspaceId]/_client.tsx`

## Project

**ROUTE:** `/projects/[projectId]`  
**PURPOSE:** A project holds file buckets, tenant databases, connected databases and dashboards; create each of them here.  
**WHO USES IT:** Members with the matching permissions  
**PERMISSION / CAPABILITY:** signed-in user; server areas `app_platform, databases, organizations, storage, workspaces` check: `app_instance.manage`, `app_instance.read`, `app_instance.schema.manage`, `app_instance.workflow.approve`, `app_template.manage`, `app_template.publish`, `app_template.read`, `connection.manage`, `database.create`, `database.delete`, `database.read`, `database.schema.manage`, `database.write`, `dataset.export`, `inventory.adjust`, `inventory.receive`, `inventory.sell`, `inventory.transfer`, `permissions.manage`, `sharing.manage`, `storage.delete`, `storage.manage`, `storage.read`, `storage.write`, `users.manage`, `workspace.manage`  
**HOW USER GETS THERE:** Workspace > a project  
**FIELDS:** Template (select, in dialog: Install app); Version (select, in dialog: Install app); Name this installed app (text, required, in dialog: Install app); Name (text, required, in dialog: New bucket); Name (text, required, in dialog: New database); Name (text, required, in dialog: Connect a database); Host (text, required, in dialog: Connect a database); Port (number, required, in dialog: Connect a database); Database name (text, required, in dialog: Connect a database); Username (text, required, in dialog: Connect a database); Password (password, required, in dialog: Connect a database); SSL mode (select, in dialog: Connect a database)  
**BUTTONS:** Applications, New bucket, New database, New connection, Install app, Cancel, Install, Create, Connect  
**FILTERS / SEARCH:** search box "Warehouse inventory"; search box "shared-docs"; search box "CRM"; search box "Analytics warehouse"; search box "db.example.com"; search box "warehouse"; status filter (warning)  
**DIALOGS:** Install app, New bucket, New database, Connect a database  
**STATUSES:** warning  
**ACTIONS:**  
- Applications -- Navigates.
- New bucket -- Opens the dialog (storage.manage).
- New database -- Opens the dialog (database.create).
- New connection -- Opens the dialog: host, port, database, username, SSL mode (connection.manage).
- Install app -- Opens the install dialog: organization, name in Apps, shop name.
- Cancel -- Nothing is saved.
- Install -- Installs it into the chosen organization / project.
- Create -- Creates it.
- Connect -- Credentials scoped to this environment can then reach that resource and no other environment's (environment.manage).
**RELATED PAGES (links on the page):** `/projects/:id/apps`, `/buckets/:id?name=:id&project=:id`, `/tenant-databases/:id`, `/connected-databases/:id`, `/app-instances/:id`  
**NORMAL NEXT STEP:** Open a bucket or database  
**EVIDENCE:** `app/(app)/projects/[projectId]/page.tsx`, `app/(app)/projects/[projectId]/_client.tsx`

## Applications (built-in business apps)

**ROUTE:** `/projects/[projectId]/apps`  
**PURPOSE:** Built-in business applications of the application platform for this project, with their qualification status; install and open them.  
**WHO USES IT:** Administrators  
**PERMISSION / CAPABILITY:** signed-in user; server areas `app_platform, workspaces` check: `app_instance.manage`, `app_instance.read`, `app_instance.schema.manage`, `app_instance.workflow.approve`, `app_template.manage`, `app_template.publish`, `app_template.read`, `database.create`, `database.read`, `database.schema.manage`, `database.write`, `inventory.adjust`, `inventory.receive`, `inventory.sell`, `inventory.transfer`, `sharing.manage`, `storage.read`, `workspace.manage`  
**HOW USER GETS THERE:** Project > Applications  
**FIELDS:** Application name (text, in dialog: Install …); I understand this is a … that has not completed production qualification, and I will keep my existing records alongside it. (checkbox, in dialog: Install …)  
**BUTTONS:** Open, Finishing… / Finish setup, Install another copy, Install, Close, Open application, Cancel, Try again / Install  
**DIALOGS:** Install …  
**ACTIONS:**  
- Open -- Navigates to it.
- Finishing… / Finish setup -- Completes the registration.
- Install another copy -- Opens the install dialog.
- Install -- Installs it into the chosen organization / project.
- Close -- The dialog closes.
- Open application -- Navigates to it (service apps: no second sign-in).
- Cancel -- Nothing is saved.
- Try again / Install -- Installs it into the chosen organization / project.
**NORMAL NEXT STEP:** Open an installed business app  
**EVIDENCE:** `app/(app)/projects/[projectId]/apps/page.tsx`, `app/(app)/projects/[projectId]/apps/_client.tsx`, `lib/built-in-apps.ts`

## Bucket (files)

**ROUTE:** `/buckets/[bucketId]`  
**PURPOSE:** A file area: upload, download and delete files, see versions and sharing.  
**WHO USES IT:** Members with storage permissions  
**PERMISSION / CAPABILITY:** signed-in user; server areas `organizations, sharing, storage, workspaces` check: `permissions.manage`, `sharing.manage`, `storage.delete`, `storage.manage`, `storage.read`, `storage.write`, `users.manage`, `workspace.manage`  
**HOW USER GETS THERE:** Project > a bucket  
**FIELDS:** Share with (select, in dialog: Share); Member (select, in dialog: Share); Team (select, in dialog: Share); Access level (select, in dialog: Share)  
**BUTTONS:** Upload files, Delete, Share, Revoke, Cancel  
**TABLE 1:** columns Name | Size | Type | Uploaded | Actions  (`app/(app)/buckets/[bucketId]/_client.tsx:188`)  
**TABLE 2:** columns Shared with | Level | Expires | Actions  (`components/ShareSection.tsx:148`)  
**FILTERS / SEARCH:** search box "Search files…"  
**DIALOGS:** Share  
**CONFIRMATIONS:** "Delete "  
**ACTIONS:**  
- Upload files -- Files go to object storage (storage.write).
- Delete -- The item is deleted on the server.
- Share -- Opens the share dialog: who, read only / read & write (sharing.manage).
- Revoke -- Access ends immediately.
- Cancel -- Nothing is saved.
**RELATED PAGES (links on the page):** `/api/v1/files/:id/download/`  
**NORMAL NEXT STEP:** Share or upload files  
**EVIDENCE:** `app/(app)/buckets/[bucketId]/page.tsx`, `app/(app)/buckets/[bucketId]/_client.tsx`, `components/ShareSection.tsx`

## Database

**ROUTE:** `/tenant-databases/[dbId]`  
**PURPOSE:** A tenant database: its tables, creating tables, sharing, analytics dashboards and dropping the database.  
**WHO USES IT:** Members with database permissions  
**PERMISSION / CAPABILITY:** signed-in user; server areas `analytics, databases, organizations, sharing, workspaces` check: `connection.manage`, `database.create`, `database.delete`, `database.read`, `database.schema.manage`, `database.write`, `dataset.analyze`, `dataset.export`, `permissions.manage`, `sharing.manage`, `users.manage`, `workspace.manage`  
**HOW USER GETS THERE:** Project > a database  
**FIELDS:** Name (text, required, in dialog: New table); Name (text, required, in dialog: New dashboard); Share with (select, in dialog: Share); Member (select, in dialog: Share); Team (select, in dialog: Share); Access level (select, in dialog: Share)  
**BUTTONS:** Drop database, New table, New dashboard, Cancel, Create, Share, Revoke  
**TABLE 1:** columns Shared with | Level | Expires | Actions  (`components/ShareSection.tsx:148`)  
**FILTERS / SEARCH:** search box "contacts"; search box "Orders overview"  
**DIALOGS:** New table, New dashboard, Share  
**CONFIRMATIONS:** "Permanently DROP the "  
**ACTIONS:**  
- Drop database -- Asks to type the name to confirm (database.delete).
- New table -- Opens the dialog (database.schema.manage).
- New dashboard -- Opens the dialog (dataset.analyze).
- Cancel -- Nothing is saved.
- Create -- Creates it.
- Share -- Opens the share dialog: who, read only / read & write (sharing.manage).
- Revoke -- Access ends immediately.
**RELATED PAGES (links on the page):** `/tables/:id`, `/dashboards/:id`  
**NORMAL NEXT STEP:** Open a table  
**EVIDENCE:** `app/(app)/tenant-databases/[dbId]/page.tsx`, `app/(app)/tenant-databases/[dbId]/_client.tsx`, `components/ShareSection.tsx`

## Table

**ROUTE:** `/tables/[tableId]`  
**PURPOSE:** One table: its columns, rows (browse, add, edit, delete), and links to import and analytics.  
**WHO USES IT:** Members with database.read / database.write  
**PERMISSION / CAPABILITY:** signed-in user; server areas `databases` check: `connection.manage`, `database.create`, `database.delete`, `database.read`, `database.schema.manage`, `database.write`, `dataset.export`  
**HOW USER GETS THERE:** Database > a table  
**FIELDS:** Name (text, required, in dialog: Add column); Type (select, in dialog: Add column); Max length (number, in dialog: Add column); Precision (number, in dialog: Add column); Scale (number, in dialog: Add column); Nullable (checkbox, in dialog: Add column); Unique (checkbox, in dialog: Add column)  
**BUTTONS:** Add column, Add row, Edit, Delete, Previous, Next, Cancel, Save / Add row  
**TABLE 1:** columns Actions  (`app/(app)/tables/[tableId]/_client.tsx:206`)  
**FILTERS / SEARCH:** search box "Search text columns…"; search box "email"; search box "{}"  
**DIALOGS:** Add column  
**CONFIRMATIONS:** "Delete this row?"  
**ACTIONS:**  
- Add column -- Opens the dialog (database.schema.manage).
- Add row -- Saves it (database.write).
- Edit -- Opens a dialog with the current values.
- Delete -- The item is deleted on the server.
- Previous -- Loads the previous page.
- Next -- Loads the next page.
- Cancel -- Nothing is saved.
- Save / Add row -- Saves it (database.write).
**RELATED PAGES (links on the page):** `/tables/:id/analytics`, `/tables/:id/import`, `/api/v1/tables/:id/rows/export/`  
**NORMAL NEXT STEP:** Import CSV or analyse  
**EVIDENCE:** `app/(app)/tables/[tableId]/page.tsx`, `app/(app)/tables/[tableId]/_client.tsx`

## CSV import

**ROUTE:** `/tables/[tableId]/import`  
**PURPOSE:** Import a CSV file into a table: upload or pick a stored file, preview detected encoding / delimiter / types, map columns, watch the job.  
**WHO USES IT:** Members with dataset.import  
**PERMISSION / CAPABILITY:** signed-in user; server areas `databases, imports, storage` check: `connection.manage`, `database.create`, `database.delete`, `database.read`, `database.schema.manage`, `database.write`, `dataset.export`, `dataset.import`, `storage.delete`, `storage.manage`, `storage.read`, `storage.write`  
**HOW USER GETS THERE:** Table > Import  
**FIELDS:** Storage bucket (select); New bucket name (text); Upload a CSV, or pick one already in this bucket (file)  
**BUTTONS:** Create bucket, Use this file, Back, Starting… / Start import, Import another file  
**TABLE 1:** columns File | Size | Action  (`app/(app)/tables/[tableId]/import/_client.tsx:303`)  
**TABLE 2:** columns CSV column | Inferred type | Sample values | Import into  (`app/(app)/tables/[tableId]/import/_client.tsx:348`)  
**TABLE 3:** columns Row | Reason  (`app/(app)/tables/[tableId]/import/_client.tsx:444`)  
**FILTERS / SEARCH:** search box "imports"  
**ACTIONS:**  
- Create bucket -- Creates it (storage.manage).
- Use this file -- Selects the file.
- Back -- Returns to the previous step.
- Starting… / Start import -- Rows are inserted in the background; the job shows pending / running / completed and rejected rows (dataset.import).
- Import another file -- Resets the import form.
**RELATED PAGES (links on the page):** `/tables/:id`  
**NORMAL NEXT STEP:** Check the imported rows  
**EVIDENCE:** `app/(app)/tables/[tableId]/import/page.tsx`, `app/(app)/tables/[tableId]/import/_client.tsx`

## Table analytics

**ROUTE:** `/tables/[tableId]/analytics`  
**PURPOSE:** Automatic data-quality profile of every column and a form to run statistics (descriptive, correlation, regression, t-test, chi-square, ANOVA, time series).  
**WHO USES IT:** Members with database.read  
**PERMISSION / CAPABILITY:** signed-in user; server areas `analytics, databases` check: `connection.manage`, `database.create`, `database.delete`, `database.read`, `database.schema.manage`, `database.write`, `dataset.analyze`, `dataset.export`  
**HOW USER GETS THERE:** Table > Analytics  
**FIELDS:** Operation (select)  
**BUTTONS:** Run  
**TABLE 1:** columns Field | Value  (`components/AnalyticsResult.tsx:81`)  
**FILTERS / SEARCH:** status filter (info)  
**STATUSES:** info  
**ACTIONS:**  
- Run -- Shows the result (database.read).
**NORMAL NEXT STEP:** Save a dashboard  
**EVIDENCE:** `app/(app)/tables/[tableId]/analytics/page.tsx`, `app/(app)/tables/[tableId]/analytics/_client.tsx`, `lib/analytics-operations.ts`, `components/AnalyticsResult.tsx`

## Dashboard (analytics)

**ROUTE:** `/dashboards/[dashboardId]`  
**PURPOSE:** A saved analytics dashboard: widgets re-run live; add and remove widgets.  
**WHO USES IT:** Members with database.read; dataset.analyze to edit  
**PERMISSION / CAPABILITY:** signed-in user; server areas `analytics, databases` check: `connection.manage`, `database.create`, `database.delete`, `database.read`, `database.schema.manage`, `database.write`, `dataset.analyze`, `dataset.export`  
**HOW USER GETS THERE:** Database > a dashboard  
**FIELDS:** Table (select, in dialog: Add widget); Operation (select, in dialog: Add widget); Title (optional) (text, in dialog: Add widget); Display as (select, in dialog: Add widget)  
**BUTTONS:** Delete, Refresh, Add widget, Add one, Remove widget, Cancel  
**TABLE 1:** columns Field | Value  (`components/AnalyticsResult.tsx:81`)  
**FILTERS / SEARCH:** status filter (info)  
**DIALOGS:** Add widget  
**CONFIRMATIONS:** "Remove this widget from the dashboard?" / "Delete the dashboard "  
**STATUSES:** info  
**ACTIONS:**  
- Delete -- The item is deleted on the server.
- Refresh -- Fetches the latest values.
- Add widget -- Opens the widget dialog (dataset.analyze).
- Add one -- Opens the create form.
- Remove widget -- Removes it from the dashboard.
- Cancel -- Nothing is saved.
**NORMAL NEXT STEP:** Add widgets  
**EVIDENCE:** `app/(app)/dashboards/[dashboardId]/page.tsx`, `app/(app)/dashboards/[dashboardId]/_client.tsx`, `lib/analytics-operations.ts`, `components/AnalyticsResult.tsx`

## Connected database

**ROUTE:** `/connected-databases/[connectedDatabaseId]`  
**PURPOSE:** A read-only connection to an external PostgreSQL database: test it and browse its tables.  
**WHO USES IT:** Members with connection.manage / database.read  
**PERMISSION / CAPABILITY:** signed-in user; server areas `databases, organizations, sharing, workspaces` check: `connection.manage`, `database.create`, `database.delete`, `database.read`, `database.schema.manage`, `database.write`, `dataset.export`, `permissions.manage`, `sharing.manage`, `users.manage`, `workspace.manage`  
**HOW USER GETS THERE:** Project > a connected database  
**FIELDS:** Share with (select, in dialog: Share); Member (select, in dialog: Share); Team (select, in dialog: Share); Access level (select, in dialog: Share)  
**BUTTONS:** Remove, Previous, Next, Share, Revoke, Cancel  
**TABLE 1:** columns Shared with | Level | Expires | Actions  (`components/ShareSection.tsx:148`)  
**DIALOGS:** Share  
**CONFIRMATIONS:** "Remove the connection "  
**ACTIONS:**  
- Remove -- The item is removed.
- Previous -- Loads the previous page.
- Next -- Loads the next page.
- Share -- Opens the share dialog: who, read only / read & write (sharing.manage).
- Revoke -- Access ends immediately.
- Cancel -- Nothing is saved.
**NORMAL NEXT STEP:** Browse a table  
**EVIDENCE:** `app/(app)/connected-databases/[connectedDatabaseId]/page.tsx`, `app/(app)/connected-databases/[connectedDatabaseId]/_client.tsx`, `components/ShareSection.tsx`

## Template builder

**ROUTE:** `/app-templates/[templateId]`  
**PURPOSE:** Design a business application template: models, fields, relationships, unique constraints, workflows; publish versions.  
**WHO USES IT:** Builders (app_template.manage / publish)  
**PERMISSION / CAPABILITY:** signed-in user; server areas `app_platform, organizations` check: `app_instance.manage`, `app_instance.read`, `app_instance.schema.manage`, `app_instance.workflow.approve`, `app_template.manage`, `app_template.publish`, `app_template.read`, `database.create`, `database.read`, `database.schema.manage`, `database.write`, `inventory.adjust`, `inventory.receive`, `inventory.sell`, `inventory.transfer`, `permissions.manage`, `sharing.manage`, `storage.read`, `users.manage`  
**HOW USER GETS THERE:** Organization > templates > a template  
**FIELDS:** Required (checkbox); New model name (text); Key (text); New field name (text); Type (select); Default (checkbox, required); Unique constraint name (text); Fields and relationships (select 2 or more) (checkbox); (relationship) (checkbox); New workflow name (text); State field (select); New state name (text); New transition name (text); From (select); To (select); Requires approval (checkbox); Notify URL (optional) (text); New relationship name (text); References (select); On delete (select); Default to current time (checkbox); Label (text, in dialog: Rename); Label (text, in dialog: Edit field); Default value (text, in dialog: Edit field); Name (text, required, in dialog: Edit template details); Description (textarea, in dialog: Edit template details); Archived (checkbox, in dialog: Edit template details)  
**BUTTONS:** Edit details, Publish version, Rename, Delete, Edit, Add model, Add field, Add unique constraint, Add workflow, Add state, Add transition, Add relationship, ▲, ▼, Cancel, Save  
**FILTERS / SEARCH:** search box "Item"; search box "item"; search box "Name"; search box "name"; search box "Unique combination"; search box "unique_combination"; search box "Lifecycle"; search box "lifecycle"; search box "Draft"; search box "draft"; search box "Submit"; search box "submit"; search box "https://..."; search box "Group"; search box "group"; status filter (info, warning)  
**DIALOGS:** Rename, Edit field, Edit template details  
**CONFIRMATIONS:** "Delete model " / "Delete field " / "Delete constraint " / "Delete relationship "  
**STATUSES:** info, warning  
**ACTIONS:**  
- Edit details -- Opens the dialog.
- Publish version -- The version can be installed; it never changes afterwards (app_template.publish).
- Rename -- Opens the rename dialog.
- Delete -- The item is deleted on the server.
- Edit -- Opens a dialog with the current values.
- Add model -- Creates it (app_template.manage).
- Add field -- Creates it.
- Add unique constraint -- Creates it.
- Add workflow -- Creates it.
- Add state -- Creates it.
- Add transition -- Creates it.
- Add relationship -- Creates it.
- ▲ -- Changes the order.
- ▼ -- Changes the order.
- Cancel -- Nothing is saved.
- Save -- The values are sent to the server and validated; on success the dialog closes and the list refreshes; on a validation error the message is shown and nothing is saved.
**RELATED PAGES (links on the page):** `/app-template-versions/:id`  
**NORMAL NEXT STEP:** Publish a version and install it  
**EVIDENCE:** `app/(app)/app-templates/[templateId]/page.tsx`, `app/(app)/app-templates/[templateId]/_client.tsx`

## Template version

**ROUTE:** `/app-template-versions/[versionId]`  
**PURPOSE:** Read-only view of one published (immutable) template version.  
**WHO USES IT:** Builders  
**PERMISSION / CAPABILITY:** signed-in user; server areas `app_platform` check: `app_instance.manage`, `app_instance.read`, `app_instance.schema.manage`, `app_instance.workflow.approve`, `app_template.manage`, `app_template.publish`, `app_template.read`, `database.create`, `database.read`, `database.schema.manage`, `database.write`, `inventory.adjust`, `inventory.receive`, `inventory.sell`, `inventory.transfer`, `sharing.manage`, `storage.read`  
**HOW USER GETS THERE:** Template > a version  
**NORMAL NEXT STEP:** Install  
**EVIDENCE:** `app/(app)/app-template-versions/[versionId]/page.tsx`, `app/(app)/app-template-versions/[versionId]/_client.tsx`

## Installed business app (definition)

**ROUTE:** `/app-instances/[instanceId]`  
**PURPOSE:** An installed application-platform instance: its definition, upgrades to newer template versions, sharing and unit grants.  
**WHO USES IT:** Administrators  
**PERMISSION / CAPABILITY:** signed-in user; server areas `app_platform, organizations, sharing, workspaces` check: `app_instance.manage`, `app_instance.read`, `app_instance.schema.manage`, `app_instance.workflow.approve`, `app_template.manage`, `app_template.publish`, `app_template.read`, `database.create`, `database.read`, `database.schema.manage`, `database.write`, `inventory.adjust`, `inventory.receive`, `inventory.sell`, `inventory.transfer`, `permissions.manage`, `sharing.manage`, `storage.read`, `users.manage`, `workspace.manage`  
**HOW USER GETS THERE:** Project > Applications > an instance  
**FIELDS:** Name (text, required, in dialog: Edit app); Archived (checkbox, in dialog: Edit app); New model name (text); Key (text); New relationship name (text); From (select); References (select); Type (select); On delete (select); Target version (select); Share with (select, in dialog: Share); Member (select, in dialog: Share); Team (select, in dialog: Share); Access level (select, in dialog: Share)  
**BUTTONS:** Edit, Starting… / Provision runtime, Retrying… / Retry, Cancel, Save, Add model, Add relationship, Comparing… / Preview, Applying… / Apply upgrade, Upgrade history ( … ), Share, Revoke  
**TABLE 1:** columns From | To | When  (`app/(app)/app-instances/[instanceId]/_client.tsx:781`)  
**TABLE 2:** columns Shared with | Level | Expires | Actions  (`components/ShareSection.tsx:148`)  
**FILTERS / SEARCH:** search box "Item"; search box "item"; search box "Group"; search box "group"; status filter (danger, info, success, warning)  
**DIALOGS:** Edit app, Share  
**STATUSES:** danger, info, success, warning  
**ACTIONS:**  
- Edit -- Opens a dialog with the current values.
- Starting… / Provision runtime -- Builds its tables through the validated provisioning service.
- Retrying… / Retry -- Repeats it.
- Cancel -- Nothing is saved.
- Save -- The values are sent to the server and validated; on success the dialog closes and the list refreshes; on a validation error the message is shown and nothing is saved.
- Add model -- Creates it (app_template.manage).
- Add relationship -- Creates it.
- Comparing… / Preview -- Shows what would be added and any conflicts with your own changes (three-way comparison).
- Applying… / Apply upgrade -- Adds what is safe; never silently overwrites your own changes.
- Upgrade history ( … ) -- Expands the list.
- Share -- Opens the share dialog: who, read only / read & write (sharing.manage).
- Revoke -- Access ends immediately.
**RELATED PAGES (links on the page):** `/app-models/:id`  
**NORMAL NEXT STEP:** Open its models  
**EVIDENCE:** `app/(app)/app-instances/[instanceId]/page.tsx`, `app/(app)/app-instances/[instanceId]/_client.tsx`, `components/ShareSection.tsx`

## Model records

**ROUTE:** `/app-models/[modelId]`  
**PURPOSE:** Records of one model of an installed business app: list, add, edit, delete; schema editing for managers.  
**WHO USES IT:** Members with database.read / write  
**PERMISSION / CAPABILITY:** signed-in user; server areas `app_platform, org_units, organizations, sharing` check: `app_instance.manage`, `app_instance.read`, `app_instance.schema.manage`, `app_instance.workflow.approve`, `app_template.manage`, `app_template.publish`, `app_template.read`, `database.create`, `database.read`, `database.schema.manage`, `database.write`, `inventory.adjust`, `inventory.receive`, `inventory.sell`, `inventory.transfer`, `org_unit.manage`, `org_unit.membership.manage`, `org_unit.read`, `permissions.manage`, `sharing.manage`, `storage.read`, `users.manage`  
**HOW USER GETS THERE:** Installed app > a model  
**FIELDS:** (read-only) (text); New field name (text); Key (text); Type (select); Default (checkbox, required); Required (checkbox); New workflow name (text); State field (select); New state name (text); New transition name (text); From (select); To (select); Requires approval (checkbox); Notify URL (optional) (text); Unique constraint name (text); Fields and relationships (select 2 or more) (checkbox); (relationship) (checkbox); Default to current time (checkbox); Member (select, required); Organizational unit (select, required); Access level (select); Expires at (optional, local time) (datetime-local); Share with (select, in dialog: Share); Member (select, in dialog: Share); Team (select, in dialog: Share); Access level (select, in dialog: Share)  
**BUTTONS:** Add record, Edit, Delete, Previous, Next, Cancel, Save / Add record, Add field, Add workflow, Add state, Add transition, Add unique constraint, Revoke unit grant, Saving… / Grant unit access, Share, Revoke  
**TABLE 1:** columns Actions  (`app/(app)/app-models/[modelId]/_client.tsx:492`)  
**TABLE 2:** columns Shared with | Level | Expires | Actions  (`components/ShareSection.tsx:148`)  
**FILTERS / SEARCH:** search box "Search text fields…"; search box "Name"; search box "name"; search box "Lifecycle"; search box "lifecycle"; search box "Draft"; search box "draft"; search box "Submit"; search box "submit"; search box "https://..."; search box "Unique combination"; search box "unique_combination"; filter (read-only); status filter (default, info, warning)  
**DIALOGS:** Share  
**CONFIRMATIONS:** "Delete this record?"  
**STATUSES:** default, info, warning  
**ACTIONS:**  
- Add record -- Saves it (database.write).
- Edit -- Opens a dialog with the current values.
- Delete -- The item is deleted on the server.
- Previous -- Loads the previous page.
- Next -- Loads the next page.
- Cancel -- Nothing is saved.
- Save / Add record -- Saves it (database.write).
- Add field -- Creates it.
- Add workflow -- Creates it.
- Add state -- Creates it.
- Add transition -- Creates it.
- Add unique constraint -- Creates it.
- Revoke unit grant -- Access through the unit ends.
- Saving… / Grant unit access -- Creates a unit-scoped grant.
- Share -- Opens the share dialog: who, read only / read & write (sharing.manage).
- Revoke -- Access ends immediately.
**RELATED PAGES (links on the page):** `/app-models/:id/records/:id`  
**NORMAL NEXT STEP:** Open a record  
**EVIDENCE:** `app/(app)/app-models/[modelId]/page.tsx`, `app/(app)/app-models/[modelId]/_client.tsx`, `components/AppModelAccess.tsx`, `components/ShareSection.tsx`

## Record

**ROUTE:** `/app-models/[modelId]/records/[recordId]`  
**PURPOSE:** One record: its fields, attachments and workflow transitions.  
**WHO USES IT:** Members  
**PERMISSION / CAPABILITY:** signed-in user; server areas `app_platform, storage` check: `app_instance.manage`, `app_instance.read`, `app_instance.schema.manage`, `app_instance.workflow.approve`, `app_template.manage`, `app_template.publish`, `app_template.read`, `database.create`, `database.read`, `database.schema.manage`, `database.write`, `inventory.adjust`, `inventory.receive`, `inventory.sell`, `inventory.transfer`, `sharing.manage`, `storage.delete`, `storage.manage`, `storage.read`, `storage.write`  
**HOW USER GETS THERE:** Model > a record  
**FIELDS:** (read-only) (text); Bucket (select, in dialog: Attach a file); File (select, in dialog: Attach a file)  
**BUTTONS:** Save, Attach file, Detach, Cancel, Attach  
**FILTERS / SEARCH:** filter (read-only); status filter (info, warning)  
**DIALOGS:** Attach a file  
**CONFIRMATIONS:** "Detach "  
**STATUSES:** info, warning  
**ACTIONS:**  
- Save -- The values are sent to the server and validated; on success the dialog closes and the list refreshes; on a validation error the message is shown and nothing is saved.
- Attach file -- Opens the attach dialog.
- Detach -- The link is removed.
- Cancel -- Nothing is saved.
- Attach -- Links the file (stored in a bucket) to the record.
**RELATED PAGES (links on the page):** `/api/v1/app-models/:id/records/:id/attachments/:id/download/`  
**NORMAL NEXT STEP:** Apply a workflow step  
**EVIDENCE:** `app/(app)/app-models/[modelId]/records/[recordId]/page.tsx`, `app/(app)/app-models/[modelId]/records/[recordId]/_client.tsx`

## Built-in Spare Parts business app: overview

**ROUTE:** `/apps/[instanceId]`  
**PURPOSE:** Overview of the application-platform Spare Parts / Inventory & Sales app (a DIFFERENT application from the Spare Parts service app opened from Apps).  
**WHO USES IT:** Users of that built-in app  
**PERMISSION / CAPABILITY:** signed-in user; server areas `app_platform` check: `app_instance.manage`, `app_instance.read`, `app_instance.schema.manage`, `app_instance.workflow.approve`, `app_template.manage`, `app_template.publish`, `app_template.read`, `database.create`, `database.read`, `database.schema.manage`, `database.write`, `inventory.adjust`, `inventory.receive`, `inventory.sell`, `inventory.transfer`, `sharing.manage`, `storage.read`  
**HOW USER GETS THERE:** Project > Applications > Open  
**FIELDS:** Find a part number (search)  
**BUTTONS:** Go to Applications, Search  
**FILTERS / SEARCH:** search box "Search a part number, e.g. 04465-0K290"  
**ACTIONS:**  
- Go to Applications -- Navigates.
- Search -- Shows matching results.
**NORMAL NEXT STEP:** Products or Sales  
**EVIDENCE:** `app/(app)/apps/[instanceId]/page.tsx`, `components/business/Overview.tsx`, `lib/business.ts`, `components/business/BusinessApp.tsx`

## Built-in app: Products

**ROUTE:** `/apps/[instanceId]/products`  
**PURPOSE:** Products of the built-in business app.  
**WHO USES IT:** Its users  
**PERMISSION / CAPABILITY:** signed-in user; server areas `app_platform` check: `app_instance.manage`, `app_instance.read`, `app_instance.schema.manage`, `app_instance.workflow.approve`, `app_template.manage`, `app_template.publish`, `app_template.read`, `database.create`, `database.read`, `database.schema.manage`, `database.write`, `inventory.adjust`, `inventory.receive`, `inventory.sell`, `inventory.transfer`, `sharing.manage`, `storage.read`  
**HOW USER GETS THERE:** Built-in app > Catalogue > Products  
**FIELDS:** Find a part number (search); Search (search); * (text)  
**BUTTONS:** Go to Applications, Search, Previous, Next, Add, Cancel, Adding… / Add  
**FILTERS / SEARCH:** search box "Search products by name"; search box "Search suppliers by name"; search box "Search customers by name"; search box "Search warehouses"; search box "Search a part number, e.g. 04465-0K290"  
**ACTIONS:**  
- Go to Applications -- Navigates.
- Search -- Shows matching results.
- Previous -- Loads the previous page.
- Next -- Loads the next page.
- Add -- Adds it.
- Cancel -- Nothing is saved.
- Adding… / Add -- Adds it.
**NORMAL NEXT STEP:** Open a product  
**EVIDENCE:** `app/(app)/apps/[instanceId]/products/page.tsx`, `components/business/Sections.tsx`, `components/business/BusinessApp.tsx`, `components/business/RecordSection.tsx`, `lib/business.ts`

## Built-in app: Product

**ROUTE:** `/apps/[instanceId]/products/[partId]`  
**PURPOSE:** One product with its part numbers, stock and attachments.  
**WHO USES IT:** Its users  
**PERMISSION / CAPABILITY:** signed-in user; server areas `app_platform, storage` check: `app_instance.manage`, `app_instance.read`, `app_instance.schema.manage`, `app_instance.workflow.approve`, `app_template.manage`, `app_template.publish`, `app_template.read`, `database.create`, `database.read`, `database.schema.manage`, `database.write`, `inventory.adjust`, `inventory.receive`, `inventory.sell`, `inventory.transfer`, `sharing.manage`, `storage.delete`, `storage.manage`, `storage.read`, `storage.write`  
**HOW USER GETS THERE:** Products > a product  
**TABS:** Overview, Part numbers, Stock, Movements, Files  
**FIELDS:** Add an image or document (file); Find a part number (search); Warehouse (select); Search part numbers (search); Part number * (text, in dialog: Add part number); Source (text, in dialog: Add part number); Search (search); * (text)  
**BUTTONS:** Add part number, Go to Applications, Search, Receive stock, Cancel, Adding… / Add, Previous, Next, Add, Change  
**TABLE 1:** columns Part number | Source  (`components/business/ProductDetail.tsx:157`)  
**TABLE 2:** columns Product | Warehouse | On hand  (`components/business/Inventory.tsx:87`)  
**TABLE 3:** columns When | Product | Warehouse | Change | Type | Reference  (`components/business/Inventory.tsx:158`)  
**TABLE 4:** columns Part number | Source | Product  (`components/business/PartNumbers.tsx:141`)  
**FILTERS / SEARCH:** search box "Search a part number, e.g. 04465-0K290"; search box "Search a part number, e.g. 044650K290"; search box "e.g. 04465-0K290"; search box "e.g. OEM, aftermarket, supplier"; search box "Type a product name or part number"; status filter (success)  
**DIALOGS:** Add part number  
**STATUSES:** success  
**ACTIONS:**  
- Add part number -- Opens the dialog.
- Go to Applications -- Navigates.
- Search -- Shows matching results.
- Receive stock -- Opens Receive stock (inventory.receive).
- Cancel -- Nothing is saved.
- Adding… / Add -- Adds it.
- Previous -- Loads the previous page.
- Next -- Loads the next page.
- Add -- Adds it.
- Change -- Lets you pick again.
**RELATED PAGES (links on the page):** `/apps/:id/products`, `/apps/:id/receive`, `/apps/:id/products/:id`  
**NORMAL NEXT STEP:** Receive stock  
**EVIDENCE:** `app/(app)/apps/[instanceId]/products/[partId]/page.tsx`, `components/business/ProductDetail.tsx`, `lib/business.ts`, `lib/format.ts`, `components/business/BusinessApp.tsx`, `components/business/Inventory.tsx`, `components/business/PartNumbers.tsx`, `components/business/RecordSection.tsx`, `components/business/hooks.ts`, `components/business/ProductPicker.tsx`

## Built-in app: Part numbers

**ROUTE:** `/apps/[instanceId]/part-numbers`  
**PURPOSE:** Search and add part numbers of products.  
**WHO USES IT:** Its users  
**PERMISSION / CAPABILITY:** signed-in user; server areas `app_platform` check: `app_instance.manage`, `app_instance.read`, `app_instance.schema.manage`, `app_instance.workflow.approve`, `app_template.manage`, `app_template.publish`, `app_template.read`, `database.create`, `database.read`, `database.schema.manage`, `database.write`, `inventory.adjust`, `inventory.receive`, `inventory.sell`, `inventory.transfer`, `sharing.manage`, `storage.read`  
**HOW USER GETS THERE:** Built-in app > Part numbers  
**FIELDS:** Search part numbers (search); Part number * (text, in dialog: Add part number); Source (text, in dialog: Add part number); Find a part number (search); Search (search); * (text)  
**BUTTONS:** Add part number, Search, Cancel, Adding… / Add, Go to Applications, Change, Previous, Next, Add  
**TABLE 1:** columns Part number | Source | Product  (`components/business/PartNumbers.tsx:141`)  
**FILTERS / SEARCH:** search box "Search a part number, e.g. 044650K290"; search box "e.g. 04465-0K290"; search box "e.g. OEM, aftermarket, supplier"; search box "Search a part number, e.g. 04465-0K290"; search box "Type a product name or part number"; status filter (success)  
**DIALOGS:** Add part number  
**STATUSES:** success  
**ACTIONS:**  
- Add part number -- Opens the dialog.
- Search -- Shows matching results.
- Cancel -- Nothing is saved.
- Adding… / Add -- Adds it.
- Go to Applications -- Navigates.
- Change -- Lets you pick again.
- Previous -- Loads the previous page.
- Next -- Loads the next page.
- Add -- Adds it.
**RELATED PAGES (links on the page):** `/apps/:id/products/:id`  
**NORMAL NEXT STEP:** Open a product  
**EVIDENCE:** `app/(app)/apps/[instanceId]/part-numbers/page.tsx`, `components/business/PartNumbers.tsx`, `lib/business.ts`, `components/business/BusinessApp.tsx`, `components/business/hooks.ts`, `components/business/ProductPicker.tsx`, `components/business/RecordSection.tsx`

## Built-in app: Stock

**ROUTE:** `/apps/[instanceId]/inventory`  
**PURPOSE:** Stock levels per product and warehouse.  
**WHO USES IT:** Its users  
**PERMISSION / CAPABILITY:** signed-in user; server areas `app_platform` check: `app_instance.manage`, `app_instance.read`, `app_instance.schema.manage`, `app_instance.workflow.approve`, `app_template.manage`, `app_template.publish`, `app_template.read`, `database.create`, `database.read`, `database.schema.manage`, `database.write`, `inventory.adjust`, `inventory.receive`, `inventory.sell`, `inventory.transfer`, `sharing.manage`, `storage.read`  
**HOW USER GETS THERE:** Built-in app > Inventory > Stock  
**FIELDS:** Warehouse (select); Find a part number (search); Search (search); * (text)  
**BUTTONS:** Receive stock, Go to Applications, Search, Previous, Next, Add, Cancel, Adding… / Add  
**TABLE 1:** columns Product | Warehouse | On hand  (`components/business/Inventory.tsx:87`)  
**TABLE 2:** columns When | Product | Warehouse | Change | Type | Reference  (`components/business/Inventory.tsx:158`)  
**FILTERS / SEARCH:** search box "Search a part number, e.g. 04465-0K290"  
**ACTIONS:**  
- Receive stock -- Opens Receive stock (inventory.receive).
- Go to Applications -- Navigates.
- Search -- Shows matching results.
- Previous -- Loads the previous page.
- Next -- Loads the next page.
- Add -- Adds it.
- Cancel -- Nothing is saved.
- Adding… / Add -- Adds it.
**RELATED PAGES (links on the page):** `/apps/:id/receive`, `/apps/:id/products/:id`  
**NORMAL NEXT STEP:** Receive stock  
**EVIDENCE:** `app/(app)/apps/[instanceId]/inventory/page.tsx`, `components/business/Inventory.tsx`, `lib/business.ts`, `lib/format.ts`, `components/business/BusinessApp.tsx`, `components/business/hooks.ts`, `components/business/RecordSection.tsx`

## Built-in app: Warehouses

**ROUTE:** `/apps/[instanceId]/warehouses`  
**PURPOSE:** Warehouses of the built-in app.  
**WHO USES IT:** Its users  
**PERMISSION / CAPABILITY:** signed-in user; server areas `app_platform` check: `app_instance.manage`, `app_instance.read`, `app_instance.schema.manage`, `app_instance.workflow.approve`, `app_template.manage`, `app_template.publish`, `app_template.read`, `database.create`, `database.read`, `database.schema.manage`, `database.write`, `inventory.adjust`, `inventory.receive`, `inventory.sell`, `inventory.transfer`, `sharing.manage`, `storage.read`  
**HOW USER GETS THERE:** Built-in app > Warehouses  
**FIELDS:** Find a part number (search); Search (search); * (text)  
**BUTTONS:** Go to Applications, Search, Previous, Next, Add, Cancel, Adding… / Add  
**FILTERS / SEARCH:** search box "Search products by name"; search box "Search suppliers by name"; search box "Search customers by name"; search box "Search warehouses"; search box "Search a part number, e.g. 04465-0K290"  
**ACTIONS:**  
- Go to Applications -- Navigates.
- Search -- Shows matching results.
- Previous -- Loads the previous page.
- Next -- Loads the next page.
- Add -- Adds it.
- Cancel -- Nothing is saved.
- Adding… / Add -- Adds it.
**NORMAL NEXT STEP:** Receive stock  
**EVIDENCE:** `app/(app)/apps/[instanceId]/warehouses/page.tsx`, `components/business/Sections.tsx`, `components/business/BusinessApp.tsx`, `components/business/RecordSection.tsx`, `lib/business.ts`

## Built-in app: Receive stock

**ROUTE:** `/apps/[instanceId]/receive`  
**PURPOSE:** Receive goods into a warehouse (inventory.receive).  
**WHO USES IT:** Inventory staff  
**PERMISSION / CAPABILITY:** signed-in user; server areas `app_platform` check: `app_instance.manage`, `app_instance.read`, `app_instance.schema.manage`, `app_instance.workflow.approve`, `app_template.manage`, `app_template.publish`, `app_template.read`, `database.create`, `database.read`, `database.schema.manage`, `database.write`, `inventory.adjust`, `inventory.receive`, `inventory.sell`, `inventory.transfer`, `sharing.manage`, `storage.read`  
**HOW USER GETS THERE:** Built-in app > Receive stock  
**FIELDS:** Warehouse (select); Quantity (text); Supplier (select); Unit cost (text); Reference (text); Find a part number (search)  
**BUTTONS:** Receive more, View stock, Receiving… / Confirm receive, Go to Applications, Search, Change  
**FILTERS / SEARCH:** search box "Delivery note or invoice number"; search box "Search a part number, e.g. 04465-0K290"; search box "Type a product name or part number"  
**ACTIONS:**  
- Receive more -- Resets the form.
- View stock -- Navigates.
- Receiving… / Confirm receive -- Stock goes up (inventory.receive).
- Go to Applications -- Navigates.
- Search -- Shows matching results.
- Change -- Lets you pick again.
**RELATED PAGES (links on the page):** `/apps/:id/inventory`, `/apps/:id/warehouses`  
**NORMAL NEXT STEP:** View stock  
**EVIDENCE:** `app/(app)/apps/[instanceId]/receive/page.tsx`, `components/business/ReceiveStock.tsx`, `lib/business.ts`, `lib/format.ts`, `components/business/BusinessApp.tsx`, `components/business/hooks.ts`, `components/business/ProductPicker.tsx`

## Built-in app: Suppliers

**ROUTE:** `/apps/[instanceId]/suppliers`  
**PURPOSE:** Suppliers of the built-in app.  
**WHO USES IT:** Its users  
**PERMISSION / CAPABILITY:** signed-in user; server areas `app_platform` check: `app_instance.manage`, `app_instance.read`, `app_instance.schema.manage`, `app_instance.workflow.approve`, `app_template.manage`, `app_template.publish`, `app_template.read`, `database.create`, `database.read`, `database.schema.manage`, `database.write`, `inventory.adjust`, `inventory.receive`, `inventory.sell`, `inventory.transfer`, `sharing.manage`, `storage.read`  
**HOW USER GETS THERE:** Built-in app > Suppliers  
**FIELDS:** Find a part number (search); Search (search); * (text)  
**BUTTONS:** Go to Applications, Search, Previous, Next, Add, Cancel, Adding… / Add  
**FILTERS / SEARCH:** search box "Search products by name"; search box "Search suppliers by name"; search box "Search customers by name"; search box "Search warehouses"; search box "Search a part number, e.g. 04465-0K290"  
**ACTIONS:**  
- Go to Applications -- Navigates.
- Search -- Shows matching results.
- Previous -- Loads the previous page.
- Next -- Loads the next page.
- Add -- Adds it.
- Cancel -- Nothing is saved.
- Adding… / Add -- Adds it.
**NORMAL NEXT STEP:** Receive stock  
**EVIDENCE:** `app/(app)/apps/[instanceId]/suppliers/page.tsx`, `components/business/Sections.tsx`, `components/business/BusinessApp.tsx`, `components/business/RecordSection.tsx`, `lib/business.ts`

## Built-in app: Customers

**ROUTE:** `/apps/[instanceId]/customers`  
**PURPOSE:** Customers of the built-in app.  
**WHO USES IT:** Its users  
**PERMISSION / CAPABILITY:** signed-in user; server areas `app_platform` check: `app_instance.manage`, `app_instance.read`, `app_instance.schema.manage`, `app_instance.workflow.approve`, `app_template.manage`, `app_template.publish`, `app_template.read`, `database.create`, `database.read`, `database.schema.manage`, `database.write`, `inventory.adjust`, `inventory.receive`, `inventory.sell`, `inventory.transfer`, `sharing.manage`, `storage.read`  
**HOW USER GETS THERE:** Built-in app > Customers  
**FIELDS:** Find a part number (search); Search (search); * (text)  
**BUTTONS:** Go to Applications, Search, Previous, Next, Add, Cancel, Adding… / Add  
**FILTERS / SEARCH:** search box "Search products by name"; search box "Search suppliers by name"; search box "Search customers by name"; search box "Search warehouses"; search box "Search a part number, e.g. 04465-0K290"  
**ACTIONS:**  
- Go to Applications -- Navigates.
- Search -- Shows matching results.
- Previous -- Loads the previous page.
- Next -- Loads the next page.
- Add -- Adds it.
- Cancel -- Nothing is saved.
- Adding… / Add -- Adds it.
**NORMAL NEXT STEP:** New sale  
**EVIDENCE:** `app/(app)/apps/[instanceId]/customers/page.tsx`, `components/business/Sections.tsx`, `components/business/BusinessApp.tsx`, `components/business/RecordSection.tsx`, `lib/business.ts`

## Built-in app: Sales

**ROUTE:** `/apps/[instanceId]/sales`  
**PURPOSE:** Sales documents of the built-in app.  
**WHO USES IT:** Sales staff  
**PERMISSION / CAPABILITY:** signed-in user; server areas `app_platform` check: `app_instance.manage`, `app_instance.read`, `app_instance.schema.manage`, `app_instance.workflow.approve`, `app_template.manage`, `app_template.publish`, `app_template.read`, `database.create`, `database.read`, `database.schema.manage`, `database.write`, `inventory.adjust`, `inventory.receive`, `inventory.sell`, `inventory.transfer`, `sharing.manage`, `storage.read`  
**HOW USER GETS THERE:** Built-in app > Sales  
**FIELDS:** Find a part number (search); Search (search); * (text)  
**BUTTONS:** New sale, Go to Applications, Search, Previous, Next, Add, Cancel, Adding… / Add  
**TABLE 1:** columns Date | Customer | Total | Status | Open  (`components/business/Sales.tsx:64`)  
**FILTERS / SEARCH:** search box "Search a part number, e.g. 04465-0K290"; status filter (success)  
**STATUSES:** success  
**ACTIONS:**  
- New sale -- Opens New sale (inventory.sell).
- Go to Applications -- Navigates.
- Search -- Shows matching results.
- Previous -- Loads the previous page.
- Next -- Loads the next page.
- Add -- Adds it.
- Cancel -- Nothing is saved.
- Adding… / Add -- Adds it.
**RELATED PAGES (links on the page):** `/apps/:id/sales/new`, `/apps/:id/sales/:id`  
**NORMAL NEXT STEP:** Open a sale  
**EVIDENCE:** `app/(app)/apps/[instanceId]/sales/page.tsx`, `components/business/Sales.tsx`, `lib/business.ts`, `lib/format.ts`, `components/business/BusinessApp.tsx`, `components/business/hooks.ts`, `components/business/RecordSection.tsx`

## Built-in app: New sale

**ROUTE:** `/apps/[instanceId]/sales/new`  
**PURPOSE:** Record a sale (order, lines, stock out, invoice) -- inventory.sell.  
**WHO USES IT:** Sales staff  
**PERMISSION / CAPABILITY:** signed-in user; server areas `app_platform` check: `app_instance.manage`, `app_instance.read`, `app_instance.schema.manage`, `app_instance.workflow.approve`, `app_template.manage`, `app_template.publish`, `app_template.read`, `database.create`, `database.read`, `database.schema.manage`, `database.write`, `inventory.adjust`, `inventory.receive`, `inventory.sell`, `inventory.transfer`, `sharing.manage`, `storage.read`  
**HOW USER GETS THERE:** Built-in app > New sale  
**FIELDS:** Customer (select); Warehouse (select); Quantity (text); Unit price (text); Find a part number (search)  
**BUTTONS:** Open sales document, New sale, Add another item, Recording sale… / Confirm sale, Remove item, Go to Applications, Search, Change  
**FILTERS / SEARCH:** search box "Search a part number, e.g. 04465-0K290"; search box "Type a product name or part number"  
**ACTIONS:**  
- Open sales document -- Navigates.
- New sale -- Opens New sale (inventory.sell).
- Add another item -- Adds a line.
- Recording sale… / Confirm sale -- Order, lines, stock out and invoice are recorded (inventory.sell).
- Remove item -- Removes it.
- Go to Applications -- Navigates.
- Search -- Shows matching results.
- Change -- Lets you pick again.
**RELATED PAGES (links on the page):** `/apps/:id/sales/:id`, `/apps/:id/customers`, `/apps/:id/warehouses`  
**NORMAL NEXT STEP:** Print invoice  
**EVIDENCE:** `app/(app)/apps/[instanceId]/sales/new/page.tsx`, `components/business/SellStock.tsx`, `lib/business.ts`, `components/business/BusinessApp.tsx`, `components/business/hooks.ts`, `components/business/ProductPicker.tsx`

## Built-in app: Sale

**ROUTE:** `/apps/[instanceId]/sales/[orderId]`  
**PURPOSE:** One recorded sale with its lines and invoice; print.  
**WHO USES IT:** Sales staff  
**PERMISSION / CAPABILITY:** signed-in user; server areas `app_platform` check: `app_instance.manage`, `app_instance.read`, `app_instance.schema.manage`, `app_instance.workflow.approve`, `app_template.manage`, `app_template.publish`, `app_template.read`, `database.create`, `database.read`, `database.schema.manage`, `database.write`, `inventory.adjust`, `inventory.receive`, `inventory.sell`, `inventory.transfer`, `sharing.manage`, `storage.read`  
**HOW USER GETS THERE:** Sales > a sale  
**FIELDS:** Find a part number (search)  
**BUTTONS:** Print invoice, Go to Applications, Search  
**TABLE 1:** columns Product | Quantity | Unit price | Line total | When | Warehouse | Change | Type  (`components/business/SalesDocument.tsx:131`)  
**FILTERS / SEARCH:** search box "Search a part number, e.g. 04465-0K290"; status filter (success, warning)  
**STATUSES:** success, warning  
**ACTIONS:**  
- Print invoice -- Opens the browser's print dialog.
- Go to Applications -- Navigates.
- Search -- Shows matching results.
**RELATED PAGES (links on the page):** `/apps/:id/sales`  
**NORMAL NEXT STEP:** Print invoice  
**EVIDENCE:** `app/(app)/apps/[instanceId]/sales/[orderId]/page.tsx`, `components/business/SalesDocument.tsx`, `lib/business.ts`, `lib/format.ts`, `components/business/BusinessApp.tsx`, `components/business/hooks.ts`

## Application (API client)

**ROUTE:** `/applications/[applicationId]`  
**PURPOSE:** A registered application (a program that connects to IntraForge): its credentials, resource grants and environments.  
**WHO USES IT:** Developers / administrators  
**PERMISSION / CAPABILITY:** signed-in user; server areas `applications, databases, environments, organizations, storage, workspaces` check: `application.create`, `application.credentials.manage`, `application.read`, `connection.manage`, `database.create`, `database.delete`, `database.read`, `database.schema.manage`, `database.write`, `dataset.export`, `environment.manage`, `environment.production.manage`, `environment.read`, `environment.secrets.manage`, `permissions.manage`, `storage.delete`, `storage.manage`, `storage.read`, `storage.write`, `users.manage`, `workspace.manage`  
**HOW USER GETS THERE:** Organization > Developer > Applications > one  
**FIELDS:** Permission code (text, required, in dialog: Grant permission); Resource type (text, required, in dialog: Grant permission); Resource ID (text, required, in dialog: Grant permission); Name (text, required, in dialog: New environment); Type (select, in dialog: New environment)  
**BUTTONS:** New environment, New credential, Rotate, Revoke, Grant permission, Cancel, Grant, Create  
**TABLE 1:** columns Credential | Status | Created | Last used | Actions  (`app/(app)/applications/[applicationId]/_client.tsx:310`)  
**TABLE 2:** columns Permission | Resource | Expires | Granted  (`app/(app)/applications/[applicationId]/_client.tsx:395`)  
**FILTERS / SEARCH:** search box "storage.files.read"; search box "bucket"; search box "the bucket's UUID"; search box "Production"; status filter (danger)  
**DIALOGS:** Grant permission, New environment  
**STATUSES:** danger  
**ACTIONS:**  
- New environment -- Opens the dialog (environment.manage; production also environment.production.manage).
- New credential -- Creates a token shown ONCE (application.credentials.manage).
- Rotate -- The old value stops working; the new one is shown once.
- Revoke -- Access ends immediately.
- Grant permission -- Opens the grant dialog: resource type / id, permission code (permissions.manage).
- Cancel -- Nothing is saved.
- Grant -- Creates a resource grant (permissions.manage).
- Create -- Creates it.
**RELATED PAGES (links on the page):** `/environments/:id`  
**NORMAL NEXT STEP:** Issue a credential or grant access  
**EVIDENCE:** `app/(app)/applications/[applicationId]/page.tsx`, `app/(app)/applications/[applicationId]/_client.tsx`, `lib/org-resources.ts`

## Environment

**ROUTE:** `/environments/[environmentId]`  
**PURPOSE:** One environment (Development / Staging / Production) of an application: variables, secrets, webhooks, bound database/bucket, credentials.  
**WHO USES IT:** Developers / administrators  
**PERMISSION / CAPABILITY:** signed-in user; server areas `applications, databases, environments, organizations, storage, workspaces` check: `application.create`, `application.credentials.manage`, `application.read`, `connection.manage`, `database.create`, `database.delete`, `database.read`, `database.schema.manage`, `database.write`, `dataset.export`, `environment.manage`, `environment.production.manage`, `environment.read`, `environment.secrets.manage`, `permissions.manage`, `storage.delete`, `storage.manage`, `storage.read`, `storage.write`, `users.manage`, `workspace.manage`  
**HOW USER GETS THERE:** Application > an environment  
**TABS:** Overview, Configuration, Secrets, API Keys, Database, Storage, Auth, Webhooks, Logs, Activity, Settings  
**FIELDS:** Key (text, required); Value (text); Base URL this environment's application should call (text); Tenant database (select); Bucket (select); Allowed origins (comma-separated) (text); URL (url, required); Event types (comma-separated) (text); Name (text); Type … to confirm (text, in dialog: Delete "…"?); I understand this is a production environment and I want to permanently delete it. (checkbox, in dialog: Delete "…"?)  
**BUTTONS:** Remove, Save, Saved / Save, New secret, Rotate, Delete, Cancel, Create, New credential, Revoke, Disconnect, Connect, New webhook, Disable / Enable, Previous, Next, Disable environment / Enable environment, Delete environment  
**TABLE 1:** columns Key | Value | Actions  (`app/(app)/environments/[environmentId]/_client.tsx:324`)  
**TABLE 2:** columns Key | Created | Rotated | Actions  (`app/(app)/environments/[environmentId]/_client.tsx:515`)  
**TABLE 3:** columns Credential | Status | Created | Last used | Actions  (`app/(app)/environments/[environmentId]/_client.tsx:722`)  
**TABLE 4:** columns URL | Events | Status | Actions  (`app/(app)/environments/[environmentId]/_client.tsx:1078`)  
**TABLE 5:** columns Time | Action | Result  (`app/(app)/environments/[environmentId]/_client.tsx:1240`)  
**FILTERS / SEARCH:** search box "LOG_LEVEL"; search box "debug"; search box "https://staging.example.com"; search box "STRIPE_API_KEY"; search box "https://staging.example.com, https://staging-preview.example.com"; search box "https://hooks.example.com/staging"; search box "file.uploaded, database.row.created"; status filter (danger)  
**DIALOGS:** Delete "…"?  
**STATUSES:** danger  
**ACTIONS:**  
- Remove -- The item is removed.
- Save -- The values are sent to the server and validated; on success the dialog closes and the list refreshes; on a validation error the message is shown and nothing is saved.
- Saved / Save -- The values are sent to the server and validated; on success the dialog closes and the list refreshes; on a validation error the message is shown and nothing is saved.
- New secret -- The value is encrypted and shown only once (environment.secrets.manage).
- Rotate -- The old value stops working; the new one is shown once.
- Delete -- The item is deleted on the server.
- Cancel -- Nothing is saved.
- Create -- Creates it.
- New credential -- Creates a token shown ONCE (application.credentials.manage).
- Revoke -- Access ends immediately.
- Disconnect -- Deletes the connection (not the external data).
- Connect -- Credentials scoped to this environment can then reach that resource and no other environment's (environment.manage).
- New webhook -- Opens the dialog: URL, event types; deliveries are signed, at-least-once.
- Disable / Enable -- Re-enables it.
- Previous -- Loads the previous page.
- Next -- Loads the next page.
- Disable environment / Enable environment -- Its credentials work again (environment.manage).
- Delete environment -- Asks for confirmation; a production environment needs a second explicit confirmation.
**NORMAL NEXT STEP:** Add variables or credentials  
**EVIDENCE:** `app/(app)/environments/[environmentId]/page.tsx`, `app/(app)/environments/[environmentId]/_client.tsx`, `lib/org-resources.ts`

## Developer portal

**ROUTE:** `/orgs/[orgId]/developer`  
**PURPOSE:** Entry to the developer area: applications, environments, webhooks, docs.  
**WHO USES IT:** Developers  
**PERMISSION / CAPABILITY:** signed-in user; server areas `applications, organizations` check: `application.create`, `application.credentials.manage`, `application.read`, `permissions.manage`, `users.manage`  
**HOW USER GETS THERE:** Organization > Developer  
**BUTTONS:** Manage applications, New application  
**ACTIONS:**  
- Manage applications -- Navigates.
- New application -- Opens the dialog (application.create).
**RELATED PAGES (links on the page):** `/orgs/:id/developer/applications`, `/applications/:id`  
**NORMAL NEXT STEP:** Applications  
**EVIDENCE:** `app/(app)/orgs/[orgId]/developer/page.tsx`, `app/(app)/orgs/[orgId]/developer/_client.tsx`, `components/DeveloperNav.tsx`

## Developer: Applications

**ROUTE:** `/orgs/[orgId]/developer/applications`  
**PURPOSE:** List and create registered applications (API clients).  
**WHO USES IT:** Developers  
**PERMISSION / CAPABILITY:** signed-in user; server areas `applications, organizations` check: `application.create`, `application.credentials.manage`, `application.read`, `permissions.manage`, `users.manage`  
**HOW USER GETS THERE:** Developer > Applications  
**FIELDS:** Name (text, required, in dialog: New application); Description (optional) (textarea, in dialog: New application)  
**BUTTONS:** New application, Connect application, Cancel, Create  
**FILTERS / SEARCH:** search box "Harmony Website"; search box "What this application does and who owns it."  
**DIALOGS:** New application  
**ACTIONS:**  
- New application -- Opens the dialog (application.create).
- Connect application -- Opens the wizard.
- Cancel -- Nothing is saved.
- Create -- Creates it.
**RELATED PAGES (links on the page):** `/orgs/:id/developer/applications/connect`, `/applications/:id`  
**NORMAL NEXT STEP:** Open an application  
**EVIDENCE:** `app/(app)/orgs/[orgId]/developer/applications/page.tsx`, `app/(app)/orgs/[orgId]/developer/applications/_client.tsx`, `components/DeveloperNav.tsx`

## Developer: Connect application

**ROUTE:** `/orgs/[orgId]/developer/applications/connect`  
**PURPOSE:** Step-by-step wizard to register an application, choose access and get its credential.  
**WHO USES IT:** Developers  
**PERMISSION / CAPABILITY:** signed-in user; server areas `applications, databases, organizations, storage, workspaces` check: `application.create`, `application.credentials.manage`, `application.read`, `connection.manage`, `database.create`, `database.delete`, `database.read`, `database.schema.manage`, `database.write`, `dataset.export`, `permissions.manage`, `storage.delete`, `storage.manage`, `storage.read`, `storage.write`, `users.manage`, `workspace.manage`  
**HOW USER GETS THERE:** Developer > Applications > Connect application  
**FIELDS:** Name (text, required); Description (optional) (textarea); Read only (radio); Read & write (radio)  
**BUTTONS:** Next, Back, Create application, Skip for now, Granting…, Generating… / Generate credential, Testing… / Test connection, Done — open application  
**FILTERS / SEARCH:** search box "What this application does and who owns it."; filter Read only  
**ACTIONS:**  
- Next -- Loads the next page.
- Back -- Returns to the previous step.
- Create application -- Creates it.
- Skip for now -- --
- Granting… -- Shown while the grant is being created.
- Generating… / Generate credential -- The token is shown once.
- Testing… / Test connection -- Connects with the saved settings and lists its tables; read-only.
- Done — open application -- Navigates.
**NORMAL NEXT STEP:** Open the application  
**EVIDENCE:** `app/(app)/orgs/[orgId]/developer/applications/connect/page.tsx`, `app/(app)/orgs/[orgId]/developer/applications/connect/_client.tsx`, `lib/org-resources.ts`, `components/DeveloperNav.tsx`

## Developer: Environments

**ROUTE:** `/orgs/[orgId]/developer/environments`  
**PURPOSE:** All environments of the organization's applications; create, clone, disable, delete.  
**WHO USES IT:** Developers  
**PERMISSION / CAPABILITY:** signed-in user; server areas `applications, environments, organizations` check: `application.create`, `application.credentials.manage`, `application.read`, `environment.manage`, `environment.production.manage`, `environment.read`, `environment.secrets.manage`, `permissions.manage`, `users.manage`  
**HOW USER GETS THERE:** Developer > Environments  
**FIELDS:** Application (select, required, in dialog: Create environment); Name (text, required, in dialog: Create environment); Type (select, in dialog: Create environment); Type … to confirm (text, in dialog: Delete "…"?); I understand this is a production environment and I want to permanently delete it. (checkbox, in dialog: Delete "…"?)  
**BUTTONS:** Create environment, Go to Applications, Clone, Disable / Enable, Delete, Cancel, Create, Delete environment  
**TABLE 1:** columns Name | Application | Type | Status | Database | Storage | API credentials | Created | Last activity | Actions  (`app/(app)/orgs/[orgId]/developer/environments/_client.tsx:174`)  
**FILTERS / SEARCH:** search box "Production"; status filter (default, success)  
**DIALOGS:** Create environment, Delete "…"?  
**STATUSES:** default, success  
**ACTIONS:**  
- Create environment -- Creates it.
- Go to Applications -- Navigates.
- Clone -- Creates a new environment with the same non-secret configuration (environment.manage).
- Disable / Enable -- Re-enables it.
- Delete -- The item is deleted on the server.
- Cancel -- Nothing is saved.
- Create -- Creates it.
- Delete environment -- Asks for confirmation; a production environment needs a second explicit confirmation.
**NORMAL NEXT STEP:** Open an environment  
**EVIDENCE:** `app/(app)/orgs/[orgId]/developer/environments/page.tsx`, `app/(app)/orgs/[orgId]/developer/environments/_client.tsx`, `components/DeveloperNav.tsx`

## Developer: Webhooks

**ROUTE:** `/orgs/[orgId]/developer/webhooks`  
**PURPOSE:** Webhook subscriptions across environments (signed event deliveries to other systems).  
**WHO USES IT:** Developers  
**PERMISSION / CAPABILITY:** signed-in user; server areas `applications, environments, organizations` check: `application.create`, `application.credentials.manage`, `application.read`, `environment.manage`, `environment.production.manage`, `environment.read`, `environment.secrets.manage`, `permissions.manage`, `users.manage`  
**HOW USER GETS THERE:** Developer > Webhooks  
**TABLE 1:** columns Environment | Application | Database bound | Webhooks | Manage | Event type | Fires when  (`app/(app)/orgs/[orgId]/developer/webhooks/_client.tsx:125`)  
**RELATED PAGES (links on the page):** `/environments/:id`  
**NORMAL NEXT STEP:** Open the environment to edit  
**EVIDENCE:** `app/(app)/orgs/[orgId]/developer/webhooks/page.tsx`, `app/(app)/orgs/[orgId]/developer/webhooks/_client.tsx`, `components/DeveloperNav.tsx`

## Developer: Docs

**ROUTE:** `/orgs/[orgId]/developer/docs`  
**PURPOSE:** Developer documentation links.  
**WHO USES IT:** Developers  
**PERMISSION / CAPABILITY:** signed-in user; server areas `organizations` check: `permissions.manage`, `users.manage`  
**HOW USER GETS THERE:** Developer > Docs  
**RELATED PAGES (links on the page):** `/api/v1/organizations/`  
**NORMAL NEXT STEP:** --  
**EVIDENCE:** `app/(app)/orgs/[orgId]/developer/docs/page.tsx`, `app/(app)/orgs/[orgId]/developer/docs/_client.tsx`, `components/DeveloperNav.tsx`

## Developer: SDKs

**ROUTE:** `/orgs/[orgId]/developer/sdks`  
**PURPOSE:** Information about client libraries.  
**WHO USES IT:** Developers  
**PERMISSION / CAPABILITY:** signed-in user; server areas `organizations` check: `permissions.manage`, `users.manage`  
**HOW USER GETS THERE:** Developer > SDKs  
**NORMAL NEXT STEP:** --  
**EVIDENCE:** `app/(app)/orgs/[orgId]/developer/sdks/page.tsx`, `app/(app)/orgs/[orgId]/developer/sdks/_client.tsx`, `components/DeveloperNav.tsx`

## Developer: API Keys (PLACEHOLDER)

**ROUTE:** `/orgs/[orgId]/developer/api-keys`  
**PURPOSE:** Placeholder page: "A cross-application key list isn't built yet". Credentials are managed per application.  
**WHO USES IT:** --  
**PERMISSION / CAPABILITY:** signed-in user; server areas `organizations` check: `permissions.manage`, `users.manage`  
**HOW USER GETS THERE:** Developer > API Keys  
**NORMAL NEXT STEP:** --  
**EVIDENCE:** `app/(app)/orgs/[orgId]/developer/api-keys/page.tsx`, `components/DeveloperStub.tsx`, `components/DeveloperNav.tsx`

## Developer: API Logs (PLACEHOLDER)

**ROUTE:** `/orgs/[orgId]/developer/api-logs`  
**PURPOSE:** Placeholder page: "A request-by-request API log isn't built yet".  
**WHO USES IT:** --  
**PERMISSION / CAPABILITY:** signed-in user; server areas `organizations` check: `permissions.manage`, `users.manage`  
**HOW USER GETS THERE:** Developer > API Logs  
**NORMAL NEXT STEP:** --  
**EVIDENCE:** `app/(app)/orgs/[orgId]/developer/api-logs/page.tsx`, `components/DeveloperStub.tsx`, `components/DeveloperNav.tsx`

## Developer: Auth (PLACEHOLDER)

**ROUTE:** `/orgs/[orgId]/developer/auth`  
**PURPOSE:** Placeholder page: "Letting applications authenticate end users isn't built yet".  
**WHO USES IT:** --  
**PERMISSION / CAPABILITY:** signed-in user; server areas `organizations` check: `permissions.manage`, `users.manage`  
**HOW USER GETS THERE:** Developer > Auth  
**NORMAL NEXT STEP:** --  
**EVIDENCE:** `app/(app)/orgs/[orgId]/developer/auth/page.tsx`, `components/DeveloperStub.tsx`, `components/DeveloperNav.tsx`

## Developer: Database (PLACEHOLDER)

**ROUTE:** `/orgs/[orgId]/developer/database`  
**PURPOSE:** Placeholder page: "An organization-wide database view isn't built yet".  
**WHO USES IT:** --  
**PERMISSION / CAPABILITY:** signed-in user; server areas `organizations` check: `permissions.manage`, `users.manage`  
**HOW USER GETS THERE:** Developer > Database  
**NORMAL NEXT STEP:** --  
**EVIDENCE:** `app/(app)/orgs/[orgId]/developer/database/page.tsx`, `components/DeveloperStub.tsx`, `components/DeveloperNav.tsx`

## Developer: Storage (PLACEHOLDER)

**ROUTE:** `/orgs/[orgId]/developer/storage`  
**PURPOSE:** Placeholder page: "An organization-wide storage view isn't built yet".  
**WHO USES IT:** --  
**PERMISSION / CAPABILITY:** signed-in user; server areas `organizations` check: `permissions.manage`, `users.manage`  
**HOW USER GETS THERE:** Developer > Storage  
**NORMAL NEXT STEP:** --  
**EVIDENCE:** `app/(app)/orgs/[orgId]/developer/storage/page.tsx`, `components/DeveloperStub.tsx`, `components/DeveloperNav.tsx`

## Developer: Usage (PLACEHOLDER)

**ROUTE:** `/orgs/[orgId]/developer/usage`  
**PURPOSE:** Placeholder page: "Per-application usage metering isn't built yet".  
**WHO USES IT:** --  
**PERMISSION / CAPABILITY:** signed-in user; server areas `organizations` check: `permissions.manage`, `users.manage`  
**HOW USER GETS THERE:** Developer > Usage  
**NORMAL NEXT STEP:** --  
**EVIDENCE:** `app/(app)/orgs/[orgId]/developer/usage/page.tsx`, `components/DeveloperStub.tsx`, `components/DeveloperNav.tsx`
