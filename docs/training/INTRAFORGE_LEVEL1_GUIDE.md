# IntraForge -- Level 1 guide

*For someone who has never used IntraForge. Describes what is implemented (IntraForge `cb32c20`, shop kit 1.1.0). Page
detail: INTRAFORGE_LEVEL1_UI_INVENTORY.md; every field, button and table: the INTRAFORGE_*_REFERENCE.md files. Statements
the code does not confirm are marked NOT CONFIRMED; screens that do not exist are said not to exist.*

---

## 1. What IntraForge is

IntraForge is a private business system that runs on the shop's own PC. In a browser on that PC it offers organizations
(companies), people, file storage, databases you design yourself, imports, analytics, applications (Spare Parts) and an
audit log. It is reached at **`https://localhost:8443`** -- from this PC only. The browser warns about the certificate the
first time because the certificate is the PC's own: *Advanced > continue*.

Next to the web interface there is a Windows program, the **IntraForge Control Center** (section 13), for starting,
stopping, backing up, restoring and removing IntraForge.

---

## 2. Starting IntraForge

- **Normally automatic**: IntraForge starts when someone signs in to Windows (about 1-2 minutes).
- **By hand**: double-click the **IntraForge** shortcut (the Control Center) and press **Start**; **Open IntraForge** opens the
  browser. The Control Center shows **Healthy** when everything runs (section 13).

---

## 3. Signing in, creating an account, logging out

- **Sign in** (`/login`): **Email**, **Password**. If two-step sign-in is switched on for the account, an **Authenticator code**
  (6 digits from an authenticator app) is asked for as well. Too many attempts are slowed down on purpose (at most 10 a minute).
- **Create account** (`/register`): **First name**, **Email**, **Password**. Then the **Welcome** screen helps create the first
  organization.
- **Two-step sign-in** can be switched on, confirmed and switched off through the server (`auth/mfa/enroll`, `confirm`,
  `disable`), but **there is no screen to switch it on** -- IMPLEMENTED — DOCUMENTATION NEEDED (and a screen is missing).
- **Log out**: the account menu > **Log out**. Logging out of IntraForge also ends any application session (Spare Parts).
- **Quick search / command palette**: **Ctrl+K** (or Cmd+K) opens a palette to jump to pages.

---

## 4. The screen

A sidebar with three items: **Dashboard**, **Apps**, **Organizations**, and the account menu. Pages show a title, a short
description, action buttons at the top right, and breadcrumbs. IntraForge does not hide buttons by permission; if you are
not allowed, the server refuses and the page shows a "you don't have permission" message. A resource of an organization you
are not a member of is shown as "not found".

---

## 5. Dashboard

"An overview of your organizations and this deployment's health": your organizations with their workspace counts, the
system's **health** (`/healthz`) and **readiness** (`/readyz`), and -- when you belong to exactly one organization -- its 8
most recent audit events.

---

## 6. Organizations, members, teams and units

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

## 7. Workspaces, projects, files and databases

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

## 8. Apps -- installing and opening Spare Parts

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

## 9. The application platform (builders and administrators)

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

## 10. Developer area (connecting other programs)

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

## 11. Audit log

`Organization > Audit log` -- "A record of security-relevant actions taken in this organization." Columns Time, Action,
Resource, Result, Request ID; filters **Resource type**, **Action**, **Result** with **Apply** / **Clear**; paging. Needs
`audit.read` (otherwise a "you don't have permission" message). Entries cannot be edited. Spare Parts' actions appear here too
(`spareparts.…`).

---

## 12. Who may do what

IntraForge checks a **permission** (also called a capability, for example `storage.write`) on the server for every action;
**roles** are named sets of permissions (Organization Administrator, Editor, Viewer, Auditor, Spare Parts Sales...). Full
list: LEVEL1_ROLES.md.

---

## 13. The Control Center, backup, restore, diagnostics (Windows program)

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

## 14. Glossary and help

LEVEL1_GLOSSARY.md (words), LEVEL1_QUICK_START.md (first day), LEVEL1_TROUBLESHOOTING.md (problems).
