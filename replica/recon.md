# Recon map: AWS Management Console → IntraForge (web)

Scope: **AWS used as the reference model for IntraForge**, the self-hosted private cloud. The slice is the AWS console
services that IntraForge already covers or is heading toward: S3 (storage), IAM + Organizations + Cognito (identity),
RDS / query editor (databases), Lambda / App Runner / Amplify Hosting (hosted apps and sites), Secrets Manager /
Parameter Store (environments), EventBridge / S3 notifications (webhooks), CloudTrail / CloudWatch (audit, logs,
health), AWS Backup, and Billing / Service Quotas (usage). EC2, networking (VPC, Route 53) and the other ~190 services
are out of scope.
For: the user's own business: IntraForge Local Edition (shop kit 1.4.0) and the products built on it (Spare Parts,
Pharmacy, IntraForge Pay).
Date: 2026-11-03

**How to read this map.** The original is AWS, and the "clone" already exists: IntraForge. Every screen and feature
below says what AWS does, then what IntraForge has today, based on its code and docs. Gaps are the build list.
Places where IntraForge differs on purpose (no JSON policies, no raw SQL, LAN-first) are marked **by design** and are
not counted as gaps.

## Sources

| # | source | URL | notes |
| --- | --- | --- | --- |
| 1 | S3 User Guide | https://docs.aws.amazon.com/AmazonS3/latest/userguide/Welcome.html | buckets, objects, versioning, lifecycle, presigned URLs, static sites |
| 2 | S3 API Reference | https://docs.aws.amazon.com/AmazonS3/latest/API/Welcome.html | object data model, the de facto storage API |
| 3 | IAM User Guide | https://docs.aws.amazon.com/IAM/latest/UserGuide/introduction.html | users, groups, roles, policies, access keys, MFA |
| 4 | AWS Organizations | https://docs.aws.amazon.com/organizations/latest/userguide/orgs_introduction.html | accounts, OUs |
| 5 | Amazon Cognito | https://docs.aws.amazon.com/cognito/latest/developerguide/what-is-amazon-cognito.html | end-user auth / OAuth for apps |
| 6 | RDS User Guide | https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/Welcome.html | create DB, connectivity, snapshots, query editor |
| 7 | Lambda Developer Guide | https://docs.aws.amazon.com/lambda/latest/dg/welcome.html | create, code, test, env vars, triggers, logs |
| 8 | App Runner | https://docs.aws.amazon.com/apprunner/latest/dg/what-is-apprunner.html | deploy a web app from source/image |
| 9 | Amplify Hosting | https://docs.aws.amazon.com/amplify/latest/userguide/welcome.html | static/web site hosting flow |
| 10 | Secrets Manager | https://docs.aws.amazon.com/secretsmanager/latest/userguide/intro.html | secrets, rotation |
| 11 | SSM Parameter Store | https://docs.aws.amazon.com/systems-manager/latest/userguide/systems-manager-parameter-store.html | config variables |
| 12 | EventBridge | https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-what-is.html | events → targets (≈ webhooks) |
| 13 | CloudTrail | https://docs.aws.amazon.com/awscloudtrail/latest/userguide/cloudtrail-user-guide.html | event history, filters, event detail |
| 14 | CloudWatch | https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/WhatIsCloudWatch.html | metrics, logs, alarms, dashboards |
| 15 | AWS Backup | https://docs.aws.amazon.com/aws-backup/latest/devguide/whatisbackup.html | plans, vaults, jobs, restore testing |
| 16 | Billing & Cost Management | https://docs.aws.amazon.com/cost-management/latest/userguide/what-is-costmanagement.html | bills, budgets, cost explorer |
| 17 | Service Quotas | https://docs.aws.amazon.com/servicequotas/latest/userguide/intro.html | quota list, increase requests |
| 18 | Console getting started | https://docs.aws.amazon.com/awsconsolehelpdocs/latest/gsg/getting-started.html | console home, search, favorites, regions |
| 19 | Pricing (S3 example) | https://aws.amazon.com/s3/pricing/ | what AWS meters = what it thinks matters |
| 20 | What's New (changelog) | https://aws.amazon.com/new/ | recent direction |
| 21 | Cloudscape design system | https://cloudscape.design/ | the console's public component library (Apache-2.0); component names and states |
| 22 | AWS YouTube | https://www.youtube.com/@amazonwebservices | console walkthroughs, click by click |
| 23 | Terms / trademarks | https://aws.amazon.com/agreement/ , https://aws.amazon.com/trademark-guidelines/ | see "Terms" below |
| 24 | **IntraForge kit (installed)** | `C:\IntraForge` (README.txt, docker-compose.yml, infrastructure/proxy/Caddyfile, BUILD_INFO.txt, quickstart and pilot guides) | kit 1.4.0, source HEAD `dbf44f593`, built 2026-10-28 |
| 25 | **IntraForge data dir** | `C:\IntraForgeData` (backups, logs, shop-network) | backup naming and cadence; the keys file was **not** read |
| 26 | **intra-cloude repo** | https://github.com/lamek-star/intra-cloude (master `7bd8aa9`, 2026-08-27; `feature/app-platform` `6fc50c7`, 2026-10-04) | backend modules, DATA_MODEL.md, PERMISSIONS.md, USER_GUIDE.md, frontend routes |
| 27 | **intraforge-pay repo** | https://github.com/lamek-star/intraforge-pay (main `8817227`, 2026-10-13) | Pay service: ledger, QR checkout, wallet app |

Notes on the sources:
- The AWS rows (1–23) are public documentation. The screen and flow details come from knowing that documentation and
  the console. They were **not re-fetched this session**, so check a flow against the live docs before you depend on
  an exact click count.
- No AWS account was used. That makes the AWS Customer Agreement's account terms moot. **Terms:** "S3", "Lambda",
  "AWS" etc. are AWS trademarks. Describing an API as "S3-compatible" is common descriptive use, but never name an
  IntraForge feature with an AWS mark.
- **Version gap:** the installed kit (HEAD `dbf44f593`) is newer than every pushed branch. Hosted websites (ADR-0019),
  the app runner for Node apps (ADR-0020), the internet tunnel gate, and Pay slots 1–3 appear only in the kit's
  compose file and Caddyfile, not in the repo. Where this map relies on them, it says **kit-only (inferred)**.
- **Live walkthrough, 2026-11-03.** The user signed in to their own IntraForge (kit 1.4.0) in Chrome, and the screens
  were read at human speed. Nothing was created, changed or deleted. The only interactions were opening the account
  menu and typing into the Ctrl K search. The IntraForge column below reflects what the live UI shows. It overrides the
  code-only reading wherever the two disagree. Findings: see "Live walkthrough findings".

## Core loop

AWS: *put your data somewhere durable, give the right people and programs access to it, and run something on top of
it.* In IntraForge terms: **create a project → store files and tables in it → grant people / apps scoped access → run
an app on that data → it is audited and backed up.**

## Screens

Columns follow the template, plus **IntraForge today**: `yes` = screen exists, `partial` = some of it, `api` = backend
only, `kit` = kit-only (inferred), `no`.

| ID | screen | route / how to reach | purpose | key components | states seen | IntraForge today |
| --- | --- | --- | --- | --- | --- | --- |
| S00 | Public landing page | `/` signed out | pitch + Get Started / View Demo | hero, feature list | — | yes `/` (live) |
| S01 | Sign in | console sign-in → MFA step | authenticate, MFA challenge | form, MFA code input, error alert | filled, wrong password, MFA required, locked | yes `/login` (email, password, "Create one"; **no forgot-password link, no MFA step seen**) |
| S02 | Console home | after sign-in | recently visited, favorites, widgets (cost, health) | top nav, widget grid, empty widget | first-time empty, filled | yes `/dashboard`: welcome, org/workspace counts, **health 4/4** (API, control DB, tenant DB, Valkey), last 8 audit events. Showed "Loading…" ~7 s on first open |
| S03 | Unified search / services menu | top nav search, ⌥S | jump to any service, resource, doc | search combobox, grouped results | empty query, results, no results | partial: Ctrl K palette exists but finds **nav pages only** ("spare" → No matches; "dash" → Dashboard) |
| S04 | Account menu / settings | top-right account | org/account switch, security credentials, sign out | dropdown | — | partial: sidebar shows name, email, Log out; header "Account menu" opened nothing visible at desktop width; **no profile / MFA / password page** |
| S05 | Buckets list | S3 → Buckets | list buckets, create | resource table, filter, Create button, empty state | **empty "no buckets"**, filled, loading | yes, inside `/projects/[id]` (with Databases, Connected databases, Apps). `/developer/storage` is a **placeholder** ("Planned, not yet built") |
| S06 | Create bucket | S05 → Create bucket | name + settings | form sections: name, ownership, block public access, versioning, tags, encryption | validation error (name taken/invalid) | partial (name only; versioning is a model flag) |
| S07 | Bucket → Objects | S05 → bucket name | browse prefix tree, upload, actions | breadcrumbs, table, Actions dropdown, "Show versions" toggle, prefix search | empty bucket, filled, versions shown | yes `/buckets/[id]`: Upload files, filename search, empty state "No files yet", Sharing panel. **No folders, no versions toggle, no settings tab**; breadcrumb skips the workspace level |
| S08 | Upload | S07 → Upload | drag-drop files/folders, then status page | drop zone, file table, progress, summary flashbar | in progress, partial failure, done | partial (multi-file pick; no folder upload, no per-file status page) |
| S09 | Object detail | S07 → object | properties, versions, presigned link | tabs, key-value pairs, Copy URL | — | **no** dedicated page |
| S10 | Bucket Properties | S07 → Properties tab | versioning, tags, encryption, static website, event notifications | key-value containers, edit modals | disabled / enabled | partial (versioning api; websites kit; notifications ≈ webhooks) |
| S11 | Bucket Permissions | S07 → Permissions tab | block public access, bucket policy JSON, CORS | toggles, JSON editor | policy invalid | yes: Sharing panel + Share button on bucket and database pages; **by design** no JSON policy |
| S12 | Bucket Management | S07 → Management tab | lifecycle rules, replication, inventory | rule table, rule wizard | none, rules listed | **no** |
| S13 | IAM dashboard | IAM home | security recommendations, counts | stat tiles, checklist | — | no |
| S14 | IAM users + create user | IAM → Users → Create | add a person, set permissions | wizard (details → permissions → review), table | empty, filled | yes `/orgs/[id]` Members: Add member, roles per member (incl. app roles: Spare Parts, Pay, Pharmacy). The app's service account is listed as a member with a role picker |
| S15 | IAM user groups | IAM → User groups | group users, attach permissions | table, members tab | empty, filled | yes Teams `/orgs/[id]/teams` |
| S16 | IAM roles / policies | IAM → Roles / Policies | named permission sets, editor | table, visual + JSON editor | invalid policy | partial: fixed system roles + custom roles via api; **by design** capability catalog, not JSON |
| S17 | Security credentials | IAM → user → Security credentials | access keys, MFA devices | table, "Create access key" wizard, secret-shown-once modal | key shown once, key inactive | yes per application `/applications/[id]`: credentials table (Status, Created, **Last used**, Rotate, Revoke), **Access summary "CAN / CANNOT"**, resource permissions with expiry. `/developer/api-keys` org-wide list is a **placeholder**. MFA: no UI |
| S18 | Organizations: accounts & OUs | Organizations console | tree of accounts / OUs | tree view, move dialog | — | yes `/orgs` → workspaces → projects; `/orgs/[id]/units` (empty state "No units yet") |
| S19 | Cognito user pool / app client | Cognito → user pools | auth for your own apps' end users | wizard, app client table | — | **no**: `/developer/auth` is a placeholder ("isn't built yet … hasn't been designed yet"); `oauth_provider` models exist but no UI |
| S20 | Databases list | RDS → Databases | list DBs, status | table, status indicator | empty, creating, available, failed | yes inside the project; `/developer/database` is a **placeholder** |
| S21 | Create database | RDS → Create | engine, size, credentials, network | long form, presets | validation | yes, simpler: name only (schema per DB) |
| S22 | Database detail | RDS → DB name | connectivity, config, monitoring, snapshots | tabs, metrics charts | — | yes `/tenant-databases/[id]`: table cards, New table, Drop database, Dashboards, Sharing. An app's runtime DB shows **internal names** (`m_0000…`, `f_3d0e…`) instead of model/field names |
| S23 | Query editor / table data | RDS Query Editor | run SQL, see rows | code editor, results grid | error, empty result | yes **by design** a typed row grid, not raw SQL: `/tables/[id]` (add/edit/delete rows, search, CSV export) |
| S24 | Connected external DB | (≈ RDS Proxy / Athena federated) | browse a DB that lives elsewhere | connection form, schema tree | auth error, unreachable | yes `/connected-databases/[id]` (read-only Postgres) |
| S25 | Functions / apps list | Lambda → Functions; App Runner → Services | list deployed code | table, status | empty, deploying, running, failed | yes, shared with Websites `/orgs/[id]/sites`: a Node app is a zip with `intraforge.json` (`runtime`, `entry`), listens on `PORT`, gets `IF_API_URL` / `IF_API_TOKEN` / `IF_BASE_PATH` |
| S26 | Create function / service | Lambda → Create | runtime, name, role | wizard | — | yes "New website" (name, address, zip) |
| S27 | Function detail | Lambda → function | code editor, Test, config (env vars, triggers, URL), Monitor/logs | tabs, code editor, test-event modal, logs table | test pass/fail, throttled | partial: card actions only (Open, Copy address, Upload new version, Versions, Take offline, Delete). **No code editor, no test, no logs, no env vars on the card** |
| S28 | Static site hosting | Amplify Hosting / S3 website | deploy a site, get a URL | deploy wizard, domain panel | deploying, live | yes `/orgs/[id]/sites`: zip upload, `https://localhost:8445/<name>/`, status Online, version history + switch back, take offline. Sandboxed (no cookies/storage, never acts as a signed-in user) |
| S29 | Secrets & parameters | Secrets Manager / Parameter Store | store config and secrets per env | table, reveal-value, rotation | value hidden/revealed | yes `/developer/environments`: table (name, application, type, status, database, storage, credentials, activity, Disable). The env named "Production" has **type development** |
| S30 | Event rules / notifications | EventBridge rules; S3 event notifications | send events to a target | rule wizard, target picker, delivery metrics | failed deliveries | yes, per environment; `/developer/webhooks` is an overview + HMAC-SHA256 verification docs. Events: app record create/update/delete + workflow transition only, **no storage events** |
| S31 | Event history | CloudTrail → Event history | who did what, when | filter bar (user, event, resource, time), table, JSON detail | no results | yes `/orgs/[id]/audit`: filters resource type, action, result (Any/Success/Denied/Error); columns Time, Who, Action, Resource, Result, Request ID; 50 per page (121 events). **No date-range or user filter, no export, no row detail** |
| S32 | Logs / API logs | CloudWatch Logs | request and app logs | log group list, log stream, search | — | **no**: `/developer/api-logs` placeholder (points to the audit log); no app logs for Node apps |
| S33 | Health & metrics | CloudWatch dashboards / Health | is it up, how busy | charts, alarms | ok, alarm, insufficient data | partial: Control Center Status (desktop), `/healthz`, Prometheus; no web dashboard |
| S34 | Backup | AWS Backup → plans, vaults, jobs, restore | schedule, verify, restore | plan wizard, job table, restore wizard | job failed, completed, restore test | partial: Control Center (desktop) + nightly 19:00 + Sunday restore test; **no web screen** |
| S35 | Billing / usage / quotas | Billing home, Cost Explorer, Service Quotas | what am I using, limits | charts, quota table, request-increase form | over budget | **no**: `/developer/usage` placeholder ("needs new metering"); Quota model has no screen |
| S36 | Marketplace / app catalogue | AWS Marketplace | install a packaged product | catalogue cards, subscribe flow | — | yes `/apps` (installed: status Running, version, Open, Settings; available: Install) and `/orgs/[id]/app-templates` (templates with model counts). **Sign-in lands here**, not on the dashboard |
| S37 | Import data | (≈ S3 → RDS import, Glue) | load a CSV into a table | upload, column mapping, error rows | mapping error | yes `/tables/[id]/import` |
| S38 | Analytics dashboards | QuickSight | charts on your data | chart builder, dashboard | — | yes `/tables/[id]/analytics`, `/dashboards/[id]` |
| S39 | Public endpoint / edge | CloudFront / API Gateway | expose to the internet | distribution wizard | deploying | kit: Cloudflare Tunnel gate (Super Admin, off by default) |
| S40 | Developer hub | (no single AWS screen: SDKs, docs, CLI) | keys, docs, SDKs in one place | nav cards | — | partial `/orgs/[id]/developer`: 12 tabs. Overview, Applications, Environments, Webhooks, SDKs, Docs are real. API Keys, Auth, Storage, Database, API Logs, Usage are **"Planned, not yet built"** placeholders |

States recorded live: empty states (bucket, teams, units, connected DBs, dashboards, sharing), "Loading…" (3–7 s on
most first opens), placeholder/not-built pages. **Still not recorded:** error and permission-denied states. These need
a second account with a narrow role (e.g. Spare Parts Sales), which means creating a user. Only do that with the
user's go-ahead.

## Live walkthrough findings (2026-11-03)

These are things to fix or decide, found by reading the running kit 1.4.0. Severity uses the pilot log's scale:
P1 = a main workflow broken, P2 = significant, P3 = polish.

| # | finding | where | sev. |
| --- | --- | --- | --- |
| L1 | Six Developer tabs are placeholders, including API Keys, **Auth** and Usage. The earlier code-only map counted Auth (OAuth provider) as built | S40, S17, S19, S32, S35 | P2 |
| L2 | The app runtime database shows generated names (`m_…`, `f_…`) to the admin, so the tables can't be read by a person | S22 | P2 |
| L3 | The environment named "Production" has type **development**, so it probably lacks production-tier protection | S29 | P2 |
| L4 | The `pay intraforge` application has **two active credentials, both never used**. Revoke the spare one | S17 | P2 (hygiene) |
| L5 | Ctrl K search matches only nav pages, not orgs, projects, buckets or apps | S03 | P3 |
| L6 | Dashboard health checks omit object storage (MinIO) and the service apps; "4/4" can be green while files are down | S02, S33 | P2 |
| L7 | There's no account page: no MFA enrolment, no password change, and no forgot-password link | S01, S04 | P2 |
| L8 | The app's service account appears in Members with a role picker, so it's easy to over-grant by mistake | S14 | P3 |
| L9 | Webhook docs say delivery is "at-most-once and retried", which contradicts itself (retries mean at-least-once) | S30 | P3 |
| L10 | Bucket and database breadcrumbs skip the workspace level | S07, S22 | P3 |
| L11 | Sign-in landed on `/apps` although the URL asked for `next=/dashboard`. Possibly a bug; recheck | S01 | P3 |
| L12 | Most pages sit on "Loading…" for 3–7 s on first open. The pilot log asks for every wait over 2 s to be written down | all | P2 |

## Flows

Click counts for AWS are estimates from the documented console steps. Click counts for IntraForge come from the
user guide and need checking live.

```
F01 Create storage and upload a file
    AWS: S02 -> S05 -> S06 (name, defaults) -> S07 -> S08 -> done
    happy path clicks: AWS ~8 | IntraForge ~5 (project -> New bucket -> name -> open -> Upload)
    edge: name taken/invalid, upload > size limit, malware detected (IntraForge: ClamAV, quarantined),
          duplicate filename, network drop mid-upload

F02 Share one file with someone outside, for a limited time
    AWS: S07 -> S09 -> Actions: Share with presigned URL -> expiry -> Copy
    happy path clicks: AWS 4-5 | IntraForge: not possible (external sharing is a stubbed org toggle;
          presigned download is internal, 300 s)
    edge: expired link, revoked link, LAN-only install (who can even reach the URL?)

F03 Recover a deleted file / an older version
    AWS: S07 -> Show versions -> select version -> Download / delete the delete-marker
    happy path clicks: AWS 3-4 | IntraForge: API only (soft delete; FileVersion when versioning on)
    edge: versioning was off, retention expired

F04 Add a staff member with only what the job needs
    AWS: S13 -> S14 Create user -> add to group (S15) -> review -> create
    happy path clicks: AWS ~7 | IntraForge: invite to org -> assign role / team (pilot roles: cashier, receiver, owner)
    edge: user already exists, role too broad (pilot rule: "grant exactly these"), last admin removed

F05 Give a program an API key scoped to one resource
    AWS: S14 (service user) -> S17 Create access key -> use case -> secret shown once
    happy path clicks: AWS ~6 | IntraForge: /developer/applications -> new -> /developer/api-keys -> scope -> shown once
    edge: key leaked -> rotate/revoke, scope too wide, key used from an unexpected place

F06 Create a database, a table and a first row
    AWS: S20 -> S21 (engine, size, creds, network) -> wait for "available" -> S23 SQL
    happy path clicks: AWS 15+ plus minutes of provisioning | IntraForge ~8, instant
          (New database -> New table -> Add column x n -> Add row)  <- IntraForge already beats AWS here
    edge: duplicate column, unique violation, required empty, decimal precision

F07 Deploy a small app on your own data
    AWS: S25 -> S26 -> S27 code -> Deploy -> Test -> function URL / trigger
    happy path clicks: AWS ~10 | IntraForge ~4 once the zip exists (Websites -> New website -> name/address -> zip)
          but the zip needs intraforge.json + npm ci --omit=dev done by hand first
    edge: app crashes on start, over memory limit, needs internet (blocked by design), bad env var

F08 Publish a website
    AWS: S28 (Amplify: upload/connect -> deploy -> URL) or S10 static website + S11 policy
    happy path clicks: AWS ~6 | IntraForge ~5 (Org -> Websites -> New website -> name/address -> zip); rollback via Versions
    edge: missing index page, LAN vs internet visibility, certificate warning

F09 Find out who changed something
    AWS: S31 -> filter by user / event name -> event detail JSON
    happy path clicks: AWS 3-4 | IntraForge: /orgs/[id]/audit -> filter -> row
    edge: denied actions (IntraForge logs these too), time zone of timestamps, very long ranges

F10 Back up, check it is restorable, restore
    AWS: S34 create plan -> assign resources -> jobs -> restore testing -> restore job
    happy path clicks: AWS ~12 | IntraForge: Control Center Backup now / Restore (shows contents, safety backup first)
    edge: keys file missing (backups unreadable), disk full, restore onto a new PC, older-version backup

F11 Turn on MFA for my account
    AWS: S04 -> Security credentials -> Assign MFA -> scan QR -> two codes
    happy path clicks: AWS ~6 | IntraForge: API only (TOTP)
    edge: lost phone (recovery codes?), clock skew

F12 See what we use and where the limits are
    AWS: S35 Billing home / Cost Explorer / Service Quotas
    happy path clicks: AWS 2-3 | IntraForge: /developer/usage + Control Center Status (disk, memory)
    edge: disk nearly full, backup folder growing (34 .icb files after 4 days)

F13 Make the system reachable from the internet (and turn it off again)
    AWS: CloudFront / API Gateway setup
    IntraForge: Super Admin switches the tunnel gate on (kit-only); LAN via Control Center > Shop network
    edge: public Wi-Fi (blocked by firewall), certificate trust on staff PCs and phones
```

## Components

These come from the AWS console's public design system (Cloudscape, Apache-2.0) and the screens above. replica-design
should build IntraForge's own versions. Copy the behaviour and the states, not the AWS look.

| component | variants | states | used on |
| --- | --- | --- | --- |
| Top navigation | with search, with org switcher | default, search open | all |
| Side navigation | per service, collapsible | active item, collapsed | all |
| Breadcrumbs | path / prefix | truncated | S07, S22, S27 |
| Resource table | selectable (single/multi), sortable, paginated, column prefs | empty, loading, filtered-no-match, error | S05, S07, S14–S17, S20, S25, S31 |
| Filter / property filter bar | text, token (`user = x`) | empty, tokens applied | S05, S07, S31 |
| Actions dropdown | split button, menu | disabled per selection | S07, S20, S25 |
| Wizard | numbered steps, review step | step error, submitting | S06, S14, S17, S26, S34 |
| Tabs | | | S07, S09, S22, S27 |
| Key-value details | 1–4 columns, with Edit | — | S09, S10, S22 |
| Status indicator | success, pending, in-progress, error, stopped | — | S20, S25, S28, S33, S34 |
| Flashbar / toast | success, info, warning, error, with progress | dismissible | all mutations |
| Empty state | with primary CTA | — | every list |
| Confirm-delete modal | typed confirmation ("type the name") | — | delete bucket/DB/app |
| Secret-shown-once modal | copy + download | — | S17, S29 |
| Copy-to-clipboard | inline, button | copied | S09, S17, S28 |
| Code / JSON editor | code, JSON | invalid | S11 (no), S27 |
| Drop zone + upload progress | single, multiple, folder | dragging, uploading, failed | S08, S37 |
| Toggle / checkbox / radio group | | disabled | S06, S10 |
| Date-range picker | relative, absolute | — | S31, S32, S35 |
| Help panel ("Info" links) | | open/closed | forms |
| Charts | line, bar, stat tile | no data | S33, S35, S38 |

## Inferred data model

Each AWS entity is mapped to its IntraForge equivalent. "evidence" points at the source, "confidence" is how sure the
mapping is.

```
Account / OU         AWS: account id, name, OU parent
  -> Organization, OrganizationalUnit(+UnitMembership), Workspace, Project
                     evidence: S18; DATA_MODEL.md §3.1/3.3; org_units/models.py      confidence: high

User / Group         AWS: user, group, membership
  -> User (accounts), Membership, Team
                     evidence: S14, S15; PERMISSIONS.md                              confidence: high

Policy / Role        AWS: JSON policy docs (Effect, Action, Resource, Condition), roles attached to principals
  -> Permission (capability catalog), Role, RoleAssignment, ResourceGrant, UnitScopedGrant
     by design: fixed capability codes instead of free-form JSON
                     evidence: S16; PERMISSIONS.md §2–4                              confidence: high

Access key           AWS: key id, secret (shown once), status, last used
  -> Application, ServiceAccount, ApplicationCredential, Scope; /developer/api-keys
                     evidence: S17; applications/models                              confidence: high

App client (Cognito) AWS: client id, secret, callback URLs, scopes
  -> OAuthClient, OAuthAuthorizationCode, OAuthAccessToken, OAuthSigningKey (models only; UI not built, live S19)
                     evidence: S19; oauth_provider/models.py                         confidence: high

Bucket               AWS: name, region, versioning, encryption, policy, lifecycle rules, website config, tags
  -> Bucket(project, name, versioning_enabled, ...)   lifecycle / tags / website config: missing
                     evidence: S05–S12; storage/models.py                            confidence: high

Object / Version     AWS: key, size, etag, content-type, version id, delete marker, metadata
  -> FileObject(object_key server-generated, display name, mime (sniffed), size, sha256,
                status active|deleted|quarantined), FileVersion, Folder (adjacency list, not prefixes)
                     evidence: DATA_MODEL.md §3.4                                    confidence: high

Presigned URL        AWS: signed URL with expiry
  -> missing as a user feature; ShareGrant has expires_at but is internal-principal only
                     evidence: sharing/models.py docstring ("External sharing ... toggle")   confidence: high

DB instance / table  AWS: instance class, engine, endpoint; tables are inside the DB
  -> TenantDatabase (one Postgres schema db_<uuid>), DBTable, DBColumn, DBForeignKey, DBIndex (catalog)
     ConnectedDatabase (encrypted creds, read-only)
                     evidence: DATA_MODEL.md §3.5                                    confidence: high

Function / service   AWS: name, runtime, code, memory, timeout, env, triggers, URL
  -> RuntimeProvision (app_platform) + kit app runner (memory 256 MB, 0.5 CPU, isolated net); exact model unknown
                     evidence: compose `runner`; ADR-0015/0020                        confidence: medium (guess on fields)

Hosted site          AWS: app, branch, domain, deploy
  -> "Websites" (ADR-0019): name, address, status (Online/offline), versions (n, file count, size, uploader, time),
     kind = static | node (intraforge.json), linked application for API access — model not in the pushed repo
                     evidence: live S28 card; compose/Caddyfile `/_sites`, port 8445  confidence: medium (fields from UI)

Secret / parameter   AWS: name, value, version, rotation
  -> Environment(type, is_production_tier), EnvironmentVariable, EnvironmentSecret
                     evidence: environments/models.py                                confidence: high

Event rule / target  AWS: pattern, target, retries, DLQ
  -> EnvironmentWebhook, WebhookDelivery (with failure windows)
                     evidence: app_platform/webhooks.py, migration 0018               confidence: high

Trail event          AWS: eventTime, eventName, userIdentity, sourceIP, resources, errorCode
  -> AuditEvent (immutable, filterable, success|denied)
                     evidence: S31; audit/                                           confidence: high

Backup job / vault   AWS: plan, rule (schedule, retention), vault, recovery point, restore job
  -> BackupRecord; files `{control_db|tenant_db|object_storage|configuration}_<uuid>_<ts>.icb`,
     encrypted at rest, nightly + weekly restore test
                     evidence: C:\IntraForgeData\backups; README.txt                 confidence: high

Quota / usage        AWS: quota code, value, usage; cost line items
  -> Quota (system), /developer/usage            costs: none (single owner)
                     evidence: DATA_MODEL.md §1                                      confidence: medium

Marketplace product  AWS: listing, subscription
  -> AppTemplate, AppTemplateVersion, AppInstance, AppInstanceUpgrade; service apps (spare-parts, pharmacy, pay-N)
                     evidence: app_platform/models.py; compose                       confidence: high
```

Relationships: Organization 1-n Workspace 1-n Project 1-n {Bucket, TenantDatabase, AppInstance};
Bucket 1-n Folder 1-n FileObject 1-n FileVersion; TenantDatabase 1-n DBTable 1-n DBColumn;
Organization 1-n {Membership, Team, OrganizationalUnit, Role, Application, Environment, AuditEvent};
Role n-n Permission; RoleAssignment(principal, role, scope); ShareGrant(resource, principal, level, expires_at);
Environment 1-n {EnvironmentVariable, EnvironmentSecret, EnvironmentWebhook}.

## Feature matrix

See `features.csv`. The `clone` column holds **IntraForge's status today** (yes / partial / no), not "no" for every
row, because the clone already exists. Must: 22, should: 20, could: 12, skip: 9 (after the live walkthrough).
IntraForge today: must 18 yes / 3 partial / 1 no (folders); should 8 yes / 1 partial / 11 no; could 4 yes / 1 partial /
7 no.

## Out of scope (cannot or should not be cloned)

- **AWS's global infrastructure.** That means regions, availability zones, edge locations, and the durability and
  availability SLAs (S3's "eleven nines"). IntraForge is one PC plus USB backups, and its promise is the backup
  discipline, not those SLAs.
- **The rest of the catalogue.** EC2/VMs, VPC, Route 53, managed AI (Bedrock, SageMaker), Kinesis, and the other 190+
  services.
- **AWS Marketplace's partner network and AWS's compliance attestations** (SOC, PCI, HIPAA). IntraForge's pharmacy
  edition would need its own regulatory review.
- **Real-money pay-as-you-go billing.** IntraForge Pay is simulated credits. Real money is a regulated licence
  question, not a feature.
- **AWS names, logos, icons and console look.** Cloudscape's code is Apache-2.0, so its components *could* be used.
  But it would make IntraForge look like AWS, so replica-design should only borrow its behaviour.
- **IAM's JSON policy language with Conditions.** This is **by design**. The capability catalog plus resource grants is
  simpler and testable, so don't rebuild IAM policy evaluation.
- **Free-form SQL editor on tenant data.** Also **by design**: the "no unreviewed dynamic SQL" principle.

## Size

Screens 41, flows 13, entities 16. IntraForge covers nearly all must-haves (18 of 22 fully) but under half of the
should-haves (8 of 20). The work is closing gaps, not starting fresh. Six of those should-gaps already have an empty
placeholder tab waiting in Developer.

Hard parts:
1. **External sharing that is safe on a LAN-first box.** Presigned links, expiry, revocation, and who can actually
   reach the URL (tunnel gate on or off).
2. **Hosted-app experience (Lambda/App Runner parity).** Deploying a zip with versions already works (live). What's
   missing is logs, test invoke and env binding on the app card, on top of the locked runner, without opening the
   Docker socket wider.
3. **Storage lifecycle and versions UI.** Retention and expiry rules, version restore, and the delete-marker semantics
   for FileVersion, and making them work with encrypted backups and quotas.

Also notable: backups and health have no **web** screen. They live only in the desktop Control Center, so an org admin
on another PC cannot see them.

Size for the must-have gaps: **M** (a few weeks). Size for all should-rows: **L** (a quarter).
