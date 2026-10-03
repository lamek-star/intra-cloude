# NotebookLM source index -- IntraForge + Spare Parts, Level 1

What to upload to NotebookLM to build a beginner training manual, and what each document teaches. All generated documents
are in `docs/training/` (IntraForge repository) and copied to `C:\Users\Hp\Intraforge-main\NotebookLM-IntraForge-Level1\`.

## Upload these first (the core)

| File | Application | Purpose | What NotebookLM should learn |
|---|---|---|---|
| `INTRAFORGE_SPARE_PARTS_LEVEL1_MASTER_SOURCE.md` | Both | One consolidated source in 17 parts | The whole story in order: what it is, screens, pages, roles, the complete sale, glossary, problems |
| `INTRAFORGE_LEVEL1_GUIDE.md` | IntraForge | Beginner guide | Starting, signing in, organizations, members, files, databases, Apps, developer area, audit, Control Center, backup / restore |
| `SPARE_PARTS_LEVEL1_GUIDE.md` | Spare Parts | Beginner guide | Reference Catalogue vs My Products, import, products, stock and movements, purchasing, the sales chain stage by stage, reports, administration |
| `LEVEL1_QUICK_START.md` | Both | First-day answers | How to do the 16 most common tasks |
| `LEVEL1_ROLES.md` | Both | Roles from server authorization | What Owner/Admin, Manager, Sales, Inventory, Viewer may and may not do; the permission matrix |
| `LEVEL1_GLOSSARY.md` | Both | Words | Simple meanings of every term and status |
| `LEVEL1_TROUBLESHOOTING.md` | Both | Problems | Real messages, what they mean, what to do, when to ask an administrator |

## Detailed references (upload if the notebook can hold them)

| File | Application | Purpose | What NotebookLM should learn |
|---|---|---|---|
| `INTRAFORGE_LEVEL1_UI_INVENTORY.md` | IntraForge | Every page | Route, purpose, users, permissions, how to get there, fields, buttons, tables, filters, dialogs, statuses, next step |
| `SPARE_PARTS_LEVEL1_UI_INVENTORY.md` | Spare Parts | Every page | The same for Spare Parts, with menu and server permissions |
| `INTRAFORGE_FIELD_REFERENCE.md`, `SPARE_PARTS_FIELD_REFERENCE.md` | each | Every field | Type, purpose, what to enter, required, validation, permission, after save, related fields, source |
| `INTRAFORGE_BUTTON_REFERENCE.md`, `SPARE_PARTS_BUTTON_REFERENCE.md` | each | Every button | Purpose, what happens, data affected, confirmation, undo, next step, server call |
| `INTRAFORGE_TABLE_REFERENCE.md`, `SPARE_PARTS_TABLE_REFERENCE.md` | each | Every table | Columns and their meaning; implemented formulas only |
| `LEVEL1_WORKFLOW_SCREENSHOTS.md` | Both | The story in pictures | The 27-step sale from start to logout |
| `SCREENSHOT_CAPTURE_CHECKLIST.md` | Both | What to capture | Every page and dialog with navigation and file names |

## Existing documentation worth uploading

| File | Why |
|---|---|
| `docs/INTRAFORGE_EXPLAINED.md` | Plain-language overview of the whole product (but see discrepancy 1 below about roles) |
| `docs/OWN_SHOP_PILOT_QUICKSTART.md` | Install, Control Center, backups, restore, removal for the shop (see discrepancy 1) |
| `docs/INTRAFORGE_FINAL_QUALIFICATION_REPORT.md` | What was tested and proven, for trainers (technical) |

**Do not upload** `docs/HOW_INTRAFORGE_WORKS.md` -- it predates the integration and describes Spare Parts as a separate program
on port 3000 (discrepancy 7).

## Evidence and method

Every page (56 IntraForge routes in `apps/frontend/src/app`, 31 Spare Parts routes in `spareparts-platform/src/app`) and the
local components it imports were read by an extractor that records fields, buttons, table columns, dialogs, confirmations,
statuses, tabs, permission checks, API calls and links with their file and line. Permissions come from the servers:
IntraForge's `permissions/catalog.py` and the Django apps each page calls; Spare Parts' generated `API_ROUTES.md`,
`PERMISSIONS_MATRIX.md` and `platform/capabilities.ts`. Workflows and statuses come from the Spare Parts domain code
(`server/domain/*.ts`). Error messages are copied from the code.

## Discrepancies found (documentation vs implementation)

1. **RESOLVED in 1.2.0 (2026-10-04): the member list now has a Roles column** (give / take away, last-administrator guard,
   audited). The finding below is kept as it was recorded on 2026-09-29.
   **Assigning a role to a member has no screen.** DOCUMENTED BUT IMPLEMENTATION NOT CONFIRMED in the user interface:
   `docs/OWN_SHOP_PILOT_QUICKSTART.md` and `docs/INTRAFORGE_EXPLAINED.md` tell the owner to give staff a Spare Parts role in
   *Organization > Members*. The server supports it (`POST /api/v1/organizations/<org>/members/<membership>/role/`,
   `permissions.manage`), but no IntraForge page calls it; *Add member* adds a person **without a role** (so they can do nothing).
   Today a role can only be given through the API.
2. **Two-step sign-in can only be switched on through the API.** IMPLEMENTED — DOCUMENTATION NEEDED (and a screen): the server
   has enroll / confirm / disable endpoints; the web interface only asks for the code at sign-in.
3. **Six Developer pages are placeholders** (API Keys, API Logs, Auth, Database, Storage, Usage) -- each says it "isn't built
   yet". Not features.
4. **Two different "Spare Parts".** The application-platform template *Spare Parts / Inventory & Sales* (`/apps/<instance>/…`,
   Project > Applications) is a different application from the integrated Spare Parts opened from **Apps**
   (`/apps/spare-parts/`). Training must use the one from Apps.
5. **Return to supplier** (`RETURN_OUT`) is allowed by the Spare Parts database but nothing in the code creates it -- NOT
   IMPLEMENTED in the user interface.
6. **No password reset screen** in IntraForge -- NOT IMPLEMENTED; a forgotten password needs an administrator.
7. **`docs/HOW_INTRAFORGE_WORKS.md` is out of date** (Spare Parts on port 3000, separate logins).
8. **No backup / restore page in the web interface** -- backup, restore, diagnostics and removal are in the Windows Control
   Center (documented correctly in the shop quickstart; stated here so trainers do not look for it in the browser).
9. **Spare Parts' Users page** shows *Add user*, *Reset password*, *Disable* / *Enable*, but inside IntraForge every one of
   them is refused ("People, passwords and roles are managed in IntraForge …") -- the buttons exist for standalone mode.
10. **Dynamic forms** in the application platform (record forms, built-in business app forms) take their field labels from each
    app's model definition at run time; they are IMPLEMENTED but cannot be listed field by field (22 such controls).

## Not confirmed

- Whether the quotation PDF link is offered before a quotation is issued.
- Field-by-field server validation limits for IntraForge forms (the server validates every request; per-field limits were not
  extracted).
- Exact layout of controls that render conditionally (busy states, empty states) beyond what the code shows.
