# User Guide — Private Data Cloud

Status: VERIFIED (the frontend described below was built and the flows in
this guide were driven end-to-end against the real backend through the
live Caddy proxy — session-cookie login, CSRF-protected mutations, file
upload/download, and the database builder's row API all confirmed
working, not just assumed from the code)
Last updated: 2026-08-10

This is the end-user companion to
[docs/deployment/LOCAL_DEPLOYMENT.md](../deployment/LOCAL_DEPLOYMENT.md)
(which covers getting the stack running) — this document covers what to
do once it's up: how to sign in and use the web interface, and where to
find the platform's other real, tested features that don't have a
screen yet.

## 1. Quick Start

| | |
|---|---|
| Open | `https://localhost:8443/login` |
| Demo email | `demo@example.com` |
| Demo password | `Demo-Password-123!` |

The first time you open the URL, your browser will warn about the
certificate — this deployment signs its own HTTPS certificate (Caddy's
local CA, `infrastructure/proxy/Caddyfile`) rather than using a public
one, appropriate for a local/LAN-first deployment
(`docs/deployment/LOCAL_DEPLOYMENT.md` Section 6). Click through
**Advanced → Proceed**. It only appears once per browser.

## 2. How It's Organized

Everything you create lives inside exactly one thing above it, in this
order:

```
Organization            e.g. "Acme Corp" — owns members and permissions
  └─ Workspace           e.g. "Engineering" — groups projects
      └─ Project          e.g. "Demo Project" — where work happens
          ├─ Storage bucket    holds files
          └─ Database          holds tables
```

A bucket or a database always belongs to exactly one project; a project
always belongs to exactly one workspace; a workspace always belongs to
exactly one organization.

## 3. Sign In

Use the demo account above, or register your own from the sign-in
page's "Create one" link. A freshly registered account starts with no
organizations — you'll create your first one from an empty state.

If a login asks for a 6-digit code, that account has two-factor
authentication enabled (Section 6) — the demo account doesn't.

## 4. Organizations

The Organizations page is what you land on after signing in — every
organization you're a member of, as a card.

1. **New organization** (top right) → name it → you become its
   administrator immediately, no approval step.
2. Open an organization to see its **workspaces** and its **members**
   list.
3. **Add member** attaches an existing account to the organization by
   email — it doesn't send an invite; the person needs an account
   already.

No member list visible, or an action fails? You're a member without
administrative rights in that organization — expected, not a bug. Only
administrators manage membership and roles.

## 5. Workspaces & Projects

Open a workspace from inside an organization to see its **projects**.
Open a project to reach its buckets and databases. For a small demo,
one workspace and one project is completely normal — the extra level
exists to keep large organizations tidy, not because you need it.

## 6. Storage

A bucket is a flat space for files — think a shared drive folder.

1. Inside a project: **New bucket**, give it a name (e.g.
   `shared-docs`).
2. Open it, then **Upload files** — pick one or several at once.
3. Use the search box to filter by filename. **Download** streams the
   file back through the backend. **Delete** is a soft delete —
   recoverable via the API even though it disappears from this list.

File type is detected from the actual file content on upload, not the
filename — renaming a file to `.txt` won't fool it.

## 7. Databases

A database here is a real, isolated PostgreSQL schema — not a
simulation.

1. Inside a project: **New database**, give it a name.
2. Open it → **New table**, give it a name. It's created with an
   automatic `id` column.
3. Open the table → **Add column** for each field, choosing a type from
   the table below.
4. **Add row** inserts data through a form built from your columns;
   **Edit** changes a row; **Delete** removes it.
5. The search box filters across text columns. **Export CSV** streams
   every row down as a file.

| Type | Stores | Notes |
|---|---|---|
| `text` / `varchar` | A string | `varchar` has a max length; `text` doesn't. |
| `integer` / `bigint` | A whole number | No decimals. |
| `decimal` | A precise number | Set precision (total digits) and scale (digits after the point) — good for money. |
| `boolean` | True / false | |
| `date` / `datetime` | A calendar date, with or without a time | Uses your browser's native date picker. |
| `uuid` | A unique identifier | Useful for referencing something external. |
| `json` | Any nested structure | Typed as raw JSON, e.g. `{"a": 1}`. |

Mark a column **Required** to forbid empty values, or **Unique** to
forbid duplicates — both enforced by PostgreSQL itself, not just the
form.

## 8. Real Features With No Screen Yet

The interface above covers the core workflow. Everything below is fully
built and tested on the server (see `docs/architecture/ROADMAP.md` for
which phase implemented each) — just not wired to a page yet. Reach all
of it at `https://localhost:8443/api/v1/`, which is itself a clickable,
interactive interface (Django REST Framework's browsable API) once
you're signed in — not raw JSON.

| Feature | What it does |
|---|---|
| Sharing | Grant one person or team read/write access to a single bucket or database, without making them a full organization member. |
| Applications | Register a service account and issue it a bearer token, scoped to exactly the resources it needs — for scripts and integrations. |
| Two-factor auth (MFA) | Enroll an authenticator app against your own account; sign-in then asks for a 6-digit code after your password. |
| Connected databases | Point at an external PostgreSQL database and browse it live, read-only — nothing copied in. |
| Audit log | Every sensitive action in an organization, who did it, and when — success or denied. |
| Teams | Group members inside an organization below the organization level, for coarser sharing. |

## 9. Troubleshooting

| What you see | What it means |
|---|---|
| Browser refuses to load the page at all | The self-signed certificate warning wasn't accepted yet — reopen the URL and click through it. |
| "You don't have permission to do that" | Correct behavior, not a bug — your account lacks the required role in that organization. |
| A page stays on its loading spinner | The backend stack isn't running — start it per `docs/deployment/LOCAL_DEPLOYMENT.md` Section 4. |
| Data from an earlier session is missing | The stack's volumes were reset (`docker compose down -v`). Nothing survives a full data wipe; day-to-day restarts (`docker compose down` / `up -d`) keep everything. |
