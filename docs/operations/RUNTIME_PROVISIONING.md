# Application runtime provisioning

Phase 2 backend step. See [ADR-0015](../architecture/adr/0015-runtime-provisioning.md).
This creates typed tables for installed definitions. Generic app record screens,
attachments and app record-level policy are not implemented by this step.

## Start and inspect

Use an authenticated human session with active organization membership and
`app_instance.schema.manage` for the instance, plus organization-wide
`database.create` and `database.schema.manage`.

1. GET `/api/v1/app-instances/{id}/runtime-plan/`.
2. POST `/api/v1/app-instances/{id}/runtime/` with only
   `{"fingerprint":"the returned 64-character fingerprint"}`.
3. Poll GET `/api/v1/app-instances/{id}/runtime/`.

POST returns 202 after reserving/enqueueing work, or 200 for an already-ready
runtime. GET requires instance schema-management authority and returns 404
before reservation. Foreign organizations get 404; missing capabilities get
403. Stale fingerprints return 409; unknown request properties return 400.
The response has `instance_id`, `status`, `fingerprint`, `database_id`,
`bindings`, `error`, and `completed_at`. Bindings map installed definition
UUIDs to existing database catalog UUIDs; relationship bindings include both
column and foreign-key UUIDs. They are not writable API inputs.

`pending` means reserved with no recorded error, not proof that a worker is
running. `failed` describes the most recent unsuccessful attempt; a bounded
automatic retry may still be scheduled. `ready` means catalog, mappings and
success audit are committed. No unverified percentage or running state is
reported. Full exception text, record contents and secrets are not returned.

## Recovery and retries

The receipt is committed before enqueue. A broker outage can leave a pending
receipt even if POST returns an error. Repeating POST with the same fingerprint
re-enqueues that same operation. There is no transactional broker outbox yet.
Duplicate deliveries serialize and a ready operation never rebuilds data.
Celery uses late acknowledgement, worker-loss rejection and one ordinary
retry after 30 seconds. Worker-loss recovery inherits the deployment's broker
configuration; it is not a fixed completion-time guarantee.

Before completion, retry may reconstruct only the exact operation-derived
tenant schema with a matching ownership comment and no catalog owner. A
schema without that marker or with an existing catalog owner is retained and
reported for review. Do not clear these conflicts by dropping an arbitrary
schema. No destructive repair endpoint is provided. Failed receipts and their
definition freeze remain until a safe retry or an operator-reviewed migration;
cancel/delete/schema-unlock workflows are deferred.

The worker rechecks the requesting actor's current active membership and
capabilities. Restore their authority or have another authorized human repeat
POST when appropriate; there is no permission bypass. Unarchive the instance
through the existing administration API before retrying an archived instance.

## Data and schema authority

Successful provisioning freezes structural definitions and generated catalog
schema until migration-aware editing exists. Display labels remain editable.
Ordinary database service calls cannot add fields/tables/FKs or drop generated
tables/databases. PostgreSQL control-catalog guards also reject direct ORM
structural mutations and changes to published receipts.

The generated database is an existing TenantDatabase. Its records currently
use existing `database.read`/`database.write`, ResourceGrant and Environment
credential checks through existing data explorer endpoints. This is not a
new app-specific or per-record permission engine. Metadata/provisioning APIs
remain human-only; no new integration endpoint or integration privilege is
granted. Existing authorized database access remains in effect. Do not use
this step as evidence that Phase 7 enterprise record permissions exist.

## Backup and deployment

Back up both control and tenant databases while writes/provisioning are
quiesced. Matching snapshots preserve runtime receipts, catalog mappings,
schema markers, constraints and records. A populated matched-pair restore was
tested against isolated databases; independently timed snapshots are not a
transactionally coordinated backup. Restore-test evidence is not permission
to replace a live database. Portable `.icp` still excludes app metadata: its
included runtime tables restore as ordinary data, not as installed apps.

Deployment requires migrations `app_platform.0003_runtime_provision` and
`0004_runtime_guards`, and the new backend and worker code together. Drain old
workers before migrations/restart, following the normal deployment procedure.
No new capabilities or dependencies require installation. This checkpoint was
verified in disposable test/smoke databases; production was not migrated.

Audit actions: `app_instance.runtime.reserve`, `.ready`, `.error`, plus the
existing validated database service events. This is provisioning audit, not
the still-pending generic app record history feature.
