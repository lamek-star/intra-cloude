-- IntraForge gap-closing schema (control database, Postgres 18).
--
-- This is the TARGET DDL, not a migration to run by hand. IntraForge's schema is owned by Django:
-- write each table as a model in the named app, run makemigrations, and check that `sqlmigrate`
-- produces the equivalent of what is below. Table names follow Django's <app>_<model> convention.
--
-- Conventions kept from the existing codebase (apps/backend, branch feature/app-platform 6fc50c7):
--   * uuid primary keys (Django generates uuid4 in Python; gen_random_uuid() here is the SQL equivalent)
--   * every tenant-owned row reaches an organization (directly or via its parent) for IDOR checks
--   * access control is a data-layer check (permissions.services.has_permission) in every service
--     function, NOT Postgres row level security — the control DB is one Django role
--   * timestamps are timestamptz, stored UTC (USE_TZ=True)
--   * secrets/tokens are stored hashed or encrypted, never in plain text
--
-- Existing tables referenced (already built): accounts_user, organizations_organization,
-- storage_bucket, storage_fileobject, storage_folder, applications_application,
-- applications_applicationcredential, environments_environment, databases_tenantdatabase.

------------------------------------------------------------------------------------------------
-- 1. storage: expiring share links (F02, S09; features "Expiring share link for one file")
--    Only usable when organizations_organization.external_sharing_enabled is true (checked in the
--    service layer). Served from the sites origin (:8445), never from IntraForge's own origin.
------------------------------------------------------------------------------------------------
create table storage_sharelink (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references organizations_organization(id) on delete cascade,
  file_id uuid not null references storage_fileobject(id) on delete cascade,
  -- sha256 of the 32-byte random token; the token itself is shown once, at creation
  token_hash char(64) not null unique,
  expires_at timestamptz not null,
  max_downloads integer check (max_downloads is null or max_downloads > 0),
  download_count integer not null default 0 check (download_count >= 0),
  -- optional extra secret, argon2/pbkdf2 via Django's password hashers
  password_hash text,
  revoked_at timestamptz,
  last_downloaded_at timestamptz,
  created_by_id uuid references accounts_user(id) on delete set null,
  created_at timestamptz not null default now(),
  constraint sharelink_expiry_after_creation check (expires_at > created_at),
  constraint sharelink_expiry_at_most_30_days check (expires_at <= created_at + interval '30 days'),
  constraint sharelink_downloads_within_limit check (max_downloads is null or download_count <= max_downloads)
);
create index on storage_sharelink (file_id);
create index on storage_sharelink (organization_id, created_at desc);
create index on storage_sharelink (created_by_id);
-- the "active links" list on the file page and the org-wide list
create index storage_sharelink_active on storage_sharelink (organization_id, expires_at)
  where revoked_at is null;

------------------------------------------------------------------------------------------------
-- 2. storage: lifecycle rules (S12; could-have, hard part 3)
------------------------------------------------------------------------------------------------
create table storage_lifecyclerule (
  id uuid primary key default gen_random_uuid(),
  bucket_id uuid not null references storage_bucket(id) on delete cascade,
  -- null = whole bucket; otherwise the rule applies to this folder and everything below it
  folder_id uuid references storage_folder(id) on delete cascade,
  name varchar(200) not null,
  action varchar(40) not null check (action in (
    'purge_deleted_files',        -- hard-delete files soft-deleted more than after_days ago
    'expire_old_versions',        -- remove FileVersion rows (and their objects) older than after_days
    'delete_files_older_than'     -- soft-delete active files created more than after_days ago
  )),
  after_days integer not null check (after_days between 1 and 3650),
  enabled boolean not null default true,
  last_run_at timestamptz,
  last_run_affected integer not null default 0,
  created_by_id uuid references accounts_user(id) on delete set null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint lifecycle_rule_name_unique_per_bucket unique (bucket_id, name)
);
create index on storage_lifecyclerule (bucket_id);
create index on storage_lifecyclerule (folder_id);
create index storage_lifecyclerule_enabled on storage_lifecyclerule (enabled) where enabled;

------------------------------------------------------------------------------------------------
-- 3. tags on buckets and tenant databases (S10; could-have). A column, not a tag table:
--    there is no cross-resource tag search in scope.
------------------------------------------------------------------------------------------------
alter table storage_bucket
  add column tags jsonb not null default '{}'::jsonb
  check (jsonb_typeof(tags) = 'object');
alter table databases_tenantdatabase
  add column tags jsonb not null default '{}'::jsonb
  check (jsonb_typeof(tags) = 'object');

------------------------------------------------------------------------------------------------
-- 4. accounts: MFA recovery codes and admin-issued password resets (S04, F11; finding L7)
--    The MFA enrol/confirm/verify/disable API already exists (accounts/urls.py). Missing are the
--    recovery path for a lost phone and any password recovery at all. IntraForge has no email on
--    an offline shop PC, so a reset is a one-time code an organization administrator hands over.
------------------------------------------------------------------------------------------------
create table accounts_mfarecoverycode (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references accounts_user(id) on delete cascade,
  code_hash text not null,           -- Django password hasher; 10 codes per (re)generation
  used_at timestamptz,
  created_at timestamptz not null default now()
);
create index on accounts_mfarecoverycode (user_id) where used_at is null;

create table accounts_passwordresetcode (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references accounts_user(id) on delete cascade,
  organization_id uuid not null references organizations_organization(id) on delete cascade,
  code_hash text not null,
  expires_at timestamptz not null,
  used_at timestamptz,
  issued_by_id uuid references accounts_user(id) on delete set null,
  created_at timestamptz not null default now(),
  constraint reset_code_short_lived check (expires_at <= created_at + interval '24 hours')
);
create index on accounts_passwordresetcode (user_id) where used_at is null;
create index on accounts_passwordresetcode (organization_id, created_at desc);
create index on accounts_passwordresetcode (issued_by_id);

------------------------------------------------------------------------------------------------
-- 5. observability (new Django app `observability`): API request log and daily usage
--    (S32, S35; findings L1). The audit log stays the record of WHO did WHAT; this is HOW the API
--    was called. Kept 30 days (prune job), so it never competes with the shop's data for disk.
------------------------------------------------------------------------------------------------
create table observability_apirequest (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid references organizations_organization(id) on delete cascade,
  application_id uuid references applications_application(id) on delete set null,
  credential_id uuid references applications_applicationcredential(id) on delete set null,
  actor_id uuid references accounts_user(id) on delete set null,   -- null for credential calls
  method varchar(8) not null check (method in ('GET','POST','PUT','PATCH','DELETE','HEAD','OPTIONS')),
  route varchar(200) not null,      -- the URL pattern (/api/v1/files/<uuid>/), never the raw path
  status_code smallint not null check (status_code between 100 and 599),
  duration_ms integer not null check (duration_ms >= 0),
  request_id varchar(64) not null,  -- same id as audit_auditevent.request_id, to jump between them
  created_at timestamptz not null default now()
);
create index on observability_apirequest (organization_id, created_at desc);
create index on observability_apirequest (application_id, created_at desc);
create index on observability_apirequest (credential_id);
create index on observability_apirequest (actor_id);
create index on observability_apirequest (request_id);
create index observability_apirequest_errors on observability_apirequest (organization_id, created_at desc)
  where status_code >= 400;

create table observability_usagedaily (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references organizations_organization(id) on delete cascade,
  application_id uuid references applications_application(id) on delete cascade,  -- null = whole org
  day date not null,                -- the shop's local calendar day (see "time zones")
  metric varchar(30) not null check (metric in (
    'api_requests', 'api_errors', 'storage_bytes', 'files', 'db_rows', 'site_requests'
  )),
  value bigint not null check (value >= 0),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
-- one row per (org, app-or-org, day, metric); NULLS NOT DISTINCT makes the org-wide row unique too
create unique index observability_usagedaily_one_per_day
  on observability_usagedaily (organization_id, application_id, day, metric) nulls not distinct;
create index on observability_usagedaily (application_id, day);

------------------------------------------------------------------------------------------------
-- 6. system: quotas (S35). DATA_MODEL.md lists Quota but system/models.py has only BackupRecord.
------------------------------------------------------------------------------------------------
create table system_quota (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references organizations_organization(id) on delete cascade,
  resource varchar(30) not null check (resource in (
    'storage_bytes', 'max_file_bytes', 'tenant_databases', 'sites', 'applications', 'api_requests_per_day'
  )),
  limit_value bigint not null check (limit_value > 0),
  warn_at_percent smallint not null default 80 check (warn_at_percent between 1 and 100),
  updated_by_id uuid references accounts_user(id) on delete set null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint quota_one_per_resource unique (organization_id, resource)
);
create index on system_quota (updated_by_id);

------------------------------------------------------------------------------------------------
-- 7. fixes to existing tables (findings L3, L8)
------------------------------------------------------------------------------------------------
-- L3: an environment typed 'production' must carry production-tier protection. (The live
-- "Production" environment is typed 'development'; fix the row first, then add the constraint.)
alter table environments_environment
  add constraint production_type_is_production_tier
  check (environment_type <> 'production' or is_production_tier);

-- L8 needs no schema change: hide memberships whose user is a service account
-- (email ends in '@service.internal') from the Members table and its role picker in the
-- serializer/service layer, and refuse role grants to them in permissions.services.assign_role.

------------------------------------------------------------------------------------------------
-- Not new tables, on purpose:
--   * folders, file versions, restore-deleted, MFA enrol, OAuth clients: tables AND API exist;
--     only screens are missing.
--   * hosted-app logs: read live from the runner (a new fixed, token-checked "tail logs"
--     operation), not copied into Postgres.
--   * storage webhooks: new event types on the existing EnvironmentWebhook/WebhookDelivery.
--   * health: computed live per request; no history table.
--   * readable app-runtime names (L2): join DBTable/DBColumn to app_platform ModelDefinition /
--     FieldDefinition in the serializer.
------------------------------------------------------------------------------------------------
