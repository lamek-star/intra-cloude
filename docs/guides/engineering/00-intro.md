# About this handbook

This handbook is for the software engineer who takes over, extends or scales IntraForge. It explains how the whole
system is built, why it is built that way, and where every piece of code lives. Read Chapters 1–4 first: they are the
rules every change must keep. The last three parts are **generated from the code itself** and list every API endpoint
(Reference A), every database model (Reference B) and every source file (Reference C).

| If you want to… | Read |
|---|---|
| Understand the system in an hour | Chapter 1 (architecture), Chapter 4 (security) |
| Change the backend | Chapter 2, then the app's section in Reference C |
| Change a screen | Chapter 3 |
| Add or change a business application | Chapter 5 |
| Build a kit, install or upgrade a shop | Chapter 6 |
| Work on Pay, the wallet app or the standalone Spare Parts | Chapter 7 |
| Set up your machine, test and release | Chapter 8 |
| Know what is not finished or not proven | Chapter 9 |

**Where the truth is.** When this handbook and a document under `docs/` disagree, the document wins for its topic:
architecture decisions in `docs/architecture/adr/`, permissions in `docs/security/PERMISSIONS.md`, threats in
`docs/security/THREAT_MODEL.md`, operations in `docs/operations/`. `CLAUDE.md` at the repository root holds the
standing engineering rules. Regenerate the three reference parts after any change (Chapter 8).

## What IntraForge is

**IntraForge** ("Build. Store. Connect. Privately.") is a private business platform that runs on the customer's own PC
or server, with no internet needed for normal work. It combines:

- **File storage** — buckets, folders, versions, share links, a trash, malware scanning.
- **A no-code database builder** — real PostgreSQL tables, rows, CSV import, analytics, read-only connections to
  outside PostgreSQL, MySQL and SQL Server databases.
- **An application platform** — business applications (Spare Parts / Inventory & Sales, Pharmacy, Repair Shop,
  Rentals, CRM, HR…) defined as data, installed per organization, run by one generic engine.
- **Service applications** — separately built programs (IntraForge Pay, the Spare Parts shop app, the Pharmacy app)
  that use IntraForge's sign-in, storage and audit.
- **Shop features** — the Movie Shop with its customer portal and media agent, hosted websites, shop names on the LAN,
  licensing.
- **People and safety** — organizations, teams, roles and capabilities, two-step sign-in and passkeys, an audit log
  nobody can edit, encrypted backups that are test-restored automatically.

## The repositories

| Repository (folder) | What it holds | Language |
|---|---|---|
| `intra-cloude` (this one; branch `integration/1.5.0`) | IntraForge itself: backend, frontend, shop kit, Control Center, setup, media agent, docs | Python, TypeScript, PowerShell, C# |
| `intraforge-pay` (and its `-portal`, `-wallet` working copies) | IntraForge Pay: the shop server, cashier and office pages, the double-entry ledger, the Android wallet | Python (FastAPI), SQL, Kotlin |
| `spare-part-shop` | The standalone Spare Parts shop application (catalogue, quotations, invoices, labels) | TypeScript (Next.js), SQLite |
| `licensing` (private: never in a repo, kit or shop PC) | The vendor's licence-signing key and serial-number registry | — |

## Versions at the time of writing

IntraForge Local Edition **1.5.7** (kit `1.5.7-586a4bbe8`) runs at the pilot shop.

- Backend: Python 3.13, Django 5.2, Django REST Framework 3.18, Celery 5.6, psycopg 3, boto3.
- Data: PostgreSQL 18 (two servers), Valkey 9, MinIO.
- Frontend: Node 24, Next.js 16.4, React 19.2, TanStack Query 5, Tailwind CSS 4.
- Proxy: Caddy 2. Shop names: CoreDNS 1.15.
- Windows side: Docker Desktop with WSL 2; C# 5 on .NET Framework 4.x for the Control Center, Setup and the media
  agent, compiled with the compiler that ships with Windows.
