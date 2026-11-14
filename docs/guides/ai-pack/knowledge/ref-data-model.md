# Reference B — the data model

Every model of IntraForge's own apps, generated from the models: table, fields (type; null; relation) and the model's description. Tenant business data (tables people create, installed apps' records) lives in per-organization PostgreSQL schemas, not here (ADR-0005).

## accounts

### User (`accounts_user`)

| Field | Type | Notes |
|---|---|---|
| `password` | CharField |  |
| `last_login` | DateTimeField | null |
| `id` | UUIDField | primary key |
| `email` | EmailField | unique |
| `first_name` | CharField |  |
| `last_name` | CharField |  |
| `is_active` | BooleanField |  |
| `date_joined` | DateTimeField |  |
| `mfa_enabled` | BooleanField |  |
| `must_change_password` | BooleanField |  |
| `mfa_secret_encrypted` | BinaryField | null |
| `mfa_confirmed_at` | DateTimeField | null |
| `passkey_only` | BooleanField |  |

### Passkey (`accounts_passkey`)

A WebAuthn credential (ADR-0019). Belongs to one user and to one relying-party ID -- the host name the browser used when it was made (`localhost`, the shop-network name): it signs in only at that name.

| Field | Type | Notes |
|---|---|---|
| `id` | UUIDField | primary key |
| `user` | ForeignKey | → User |
| `name` | CharField |  |
| `rp_id` | CharField |  |
| `credential_id` | BinaryField | unique |
| `public_key` | BinaryField |  |
| `sign_count` | PositiveBigIntegerField |  |
| `transports` | JSONField |  |
| `backed_up` | BooleanField |  |
| `created_at` | DateTimeField |  |
| `last_used_at` | DateTimeField | null |

### MFARecoveryCode (`accounts_mfarecoverycode`)

One of a person's one-time recovery codes for two-step sign-in, for when their authenticator is lost. Only a hash is kept; the codes are shown once, when made.

| Field | Type | Notes |
|---|---|---|
| `id` | UUIDField | primary key |
| `user` | ForeignKey | → User |
| `code_hash` | CharField |  |
| `used_at` | DateTimeField | null |
| `created_at` | DateTimeField |  |

## analytics

### Dashboard (`analytics_dashboard`)

A saved arrangement of analytics widgets (Section 25 of the master prompt). Widgets are stored as declarative JSON — {table_id, operation, params, chart_type, title, position} — never a saved raw query, so `views.py`'s render endpoint can re-validate every widget's permissions and re-run its operation against live data every time it's viewed, rather than trusting a cached result a later-revoked grant should have invalidated.

| Field | Type | Notes |
|---|---|---|
| `id` | UUIDField | primary key |
| `tenant_database` | ForeignKey | → TenantDatabase |
| `name` | CharField |  |
| `widgets` | JSONField |  |
| `created_by` | ForeignKey | → User |
| `created_at` | DateTimeField |  |
| `updated_at` | DateTimeField |  |

## app_platform

### AppTemplate (`app_platform_apptemplate`)

| Field | Type | Notes |
|---|---|---|
| `id` | UUIDField | primary key |
| `label` | CharField |  |
| `created_at` | DateTimeField |  |
| `organization` | ForeignKey | → Organization |
| `description` | TextField |  |
| `draft` | JSONField |  |
| `archived` | BooleanField |  |
| `created_by` | ForeignKey | → User |

### AppTemplateVersion (`app_platform_apptemplateversion`)

| Field | Type | Notes |
|---|---|---|
| `id` | UUIDField | primary key |
| `template` | ForeignKey | → AppTemplate |
| `number` | PositiveIntegerField |  |
| `definition` | JSONField |  |
| `checksum_sha256` | CharField |  |
| `created_at` | DateTimeField |  |
| `created_by` | ForeignKey | → User |

### AppInstance (`app_platform_appinstance`)

| Field | Type | Notes |
|---|---|---|
| `id` | UUIDField | primary key |
| `label` | CharField |  |
| `created_at` | DateTimeField |  |
| `organization` | ForeignKey | → Organization |
| `project` | ForeignKey | → Project |
| `source_version` | ForeignKey | → AppTemplateVersion |
| `archived` | BooleanField |  |
| `created_by` | ForeignKey | → User |

### ModelDefinition (`app_platform_modeldefinition`)

| Field | Type | Notes |
|---|---|---|
| `id` | UUIDField | primary key |
| `label` | CharField |  |
| `created_at` | DateTimeField |  |
| `key` | CharField |  |
| `source_definition_id` | UUIDField | null |
| `position` | PositiveIntegerField |  |
| `instance` | ForeignKey | → AppInstance |

### FieldDefinition (`app_platform_fielddefinition`)

| Field | Type | Notes |
|---|---|---|
| `id` | UUIDField | primary key |
| `label` | CharField |  |
| `created_at` | DateTimeField |  |
| `key` | CharField |  |
| `source_definition_id` | UUIDField | null |
| `position` | PositiveIntegerField |  |
| `model` | ForeignKey | → ModelDefinition |
| `data_type` | CharField | choices: text, integer, decimal, boolean, date, datetime, org_unit_reference |
| `required` | BooleanField |  |
| `default_value` | JSONField | null |
| `unique` | BooleanField |  |
| `indexed` | BooleanField |  |

### ConstraintDefinition (`app_platform_constraintdefinition`)

A model-level composite UNIQUE constraint -- Post-Phase-3 Integration Enablement's general composite-uniqueness capability (docs/SPARE_PARTS_INTEGRATION_READINESS.md's "Inventory (Part x Warehouse)" row). Membership is `fields` union `relationships`, >=2 combined, all belonging to this same `model` (enforced by definitions.py/instances.py, never by a DB constraint spanning two tables). A relationship is only eligible when its own FK column lives on this model's table -- i.e. `relationship.source_model == model` and `relationship.kind == "many_to_one"`; a `many_to_many` relationship has no column on either side (it's a join table) and can never participate. Physical enforcement is a real Postgres UNIQUE constraint added via databases.services.add_field_set_unique_constraint, keyed by this row's own stable `id` -- never by the member set or by `label` -- so a display-label rename or a member's position/order changing never touches DDL or requires reprovisioning.

| Field | Type | Notes |
|---|---|---|
| `id` | UUIDField | primary key |
| `label` | CharField |  |
| `created_at` | DateTimeField |  |
| `key` | CharField |  |
| `source_definition_id` | UUIDField | null |
| `position` | PositiveIntegerField |  |
| `model` | ForeignKey | → ModelDefinition |
| `fields` | ManyToManyField | → FieldDefinition |
| `relationships` | ManyToManyField | → RelationshipDefinition |

### RelationshipDefinition (`app_platform_relationshipdefinition`)

| Field | Type | Notes |
|---|---|---|
| `id` | UUIDField | primary key |
| `label` | CharField |  |
| `created_at` | DateTimeField |  |
| `key` | CharField |  |
| `source_definition_id` | UUIDField | null |
| `position` | PositiveIntegerField |  |
| `instance` | ForeignKey | → AppInstance |
| `source_model` | ForeignKey | → ModelDefinition |
| `target_model` | ForeignKey | → ModelDefinition |
| `kind` | CharField |  |
| `deletion_policy` | CharField |  |

### WorkflowDefinition (`app_platform_workflowdefinition`)

Phase 5: a declarative state machine over one of `model`'s own existing text fields -- there is no enum type in this platform, so `state_field` (validated text-typed, enforced in definitions.py/ instances.py, never by a DB constraint spanning two tables the way FieldDefinition.data_type is) holds whatever value the workflow's current state says it should. Like every Definition, `position` is excluded from runtime_plan.py's fingerprint -- but unlike every other concrete Definition subclass, the *whole* workflow subsystem is excluded from it: no migration or provisioning code ever reads these tables. It's pure control-plane declaration, governing legal writes to an already-physical field, never new schema of its own.

| Field | Type | Notes |
|---|---|---|
| `id` | UUIDField | primary key |
| `label` | CharField |  |
| `created_at` | DateTimeField |  |
| `key` | CharField |  |
| `source_definition_id` | UUIDField | null |
| `position` | PositiveIntegerField |  |
| `model` | ForeignKey | → ModelDefinition |
| `state_field` | ForeignKey | → FieldDefinition |

### WorkflowState (`app_platform_workflowstate`)

A legal value of its workflow's `state_field`. Deliberately no separate `value` column -- `key` is already a validated, storage-safe identifier (KeyField), and reusing it as the literal text written to the record avoids a redundant, driftable second name for the same thing.

| Field | Type | Notes |
|---|---|---|
| `id` | UUIDField | primary key |
| `label` | CharField |  |
| `created_at` | DateTimeField |  |
| `key` | CharField |  |
| `source_definition_id` | UUIDField | null |
| `position` | PositiveIntegerField |  |
| `workflow` | ForeignKey | → WorkflowDefinition |

### WorkflowTransition (`app_platform_workflowtransition`)

One legal move from `from_state` (null = valid from any current state) to `to_state`. `conditions` is a JSON list of `{field_id, operator, value}` (operator in eq/ne/is_null/is_not_null), ANDed -- deliberately as narrow as databases/rows.py's own exact-match-only filtering, not a general expression language. `field_actions` is a JSON list of `{field_id, value}` literal writes applied in the exact same UPDATE as the state change (databases.rows.update_row_if) -- literal-only (no calculated values) is what makes a replayed apply naturally idempotent: setting a column to a fixed value twice is a no-op the second time, unlike e.g. incrementing a counter. `requires_approval` gates this specific transition behind the `app_instance.workflow.approve` capability, in addition to the `database.write` every record write already needs -- see docs/implementation/APP_PLATFORM_PHASE5.md for why this is a capability gate and not a stateful pending/approve workflow. `notify_url`, if set, is validated against databases.connectors.assert_host_is_safe at definition time (and re-checked immediately before every delivery attempt, since DNS can rebind between the two).

| Field | Type | Notes |
|---|---|---|
| `id` | UUIDField | primary key |
| `label` | CharField |  |
| `created_at` | DateTimeField |  |
| `key` | CharField |  |
| `source_definition_id` | UUIDField | null |
| `position` | PositiveIntegerField |  |
| `workflow` | ForeignKey | → WorkflowDefinition |
| `from_state` | ForeignKey | null; → WorkflowState |
| `to_state` | ForeignKey | → WorkflowState |
| `conditions` | JSONField |  |
| `field_actions` | JSONField |  |
| `requires_approval` | BooleanField |  |
| `notify_url` | TextField |  |

### RuntimeProvision (`app_platform_runtimeprovision`)

Durable reservation and immutable publication of one runtime per instance.

| Field | Type | Notes |
|---|---|---|
| `instance` | OneToOneField | primary key; → AppInstance |
| `plan` | JSONField |  |
| `fingerprint` | CharField |  |
| `database` | OneToOneField | null; unique; → TenantDatabase |
| `bindings` | JSONField |  |
| `last_error` | CharField |  |
| `created_by` | ForeignKey | → User |
| `created_at` | DateTimeField |  |
| `completed_at` | DateTimeField | null |

### RecordAttachment (`app_platform_recordattachment`)

Links an existing `storage.FileObject` to one record. The record itself lives in a raw tenant table this app never models in Django, so `record_id` is a plain UUID, not a foreign key -- its only integrity guarantee is `records.delete_record` also removing rows here, not a database constraint (see that function's own docstring for why this can't be a single atomic operation across the control/tenant databases).

| Field | Type | Notes |
|---|---|---|
| `id` | UUIDField | primary key |
| `model` | ForeignKey | → ModelDefinition |
| `record_id` | UUIDField |  |
| `file` | ForeignKey | → FileObject |
| `created_by` | ForeignKey | → User |
| `created_at` | DateTimeField |  |

### WorkflowTransitionAttempt (`app_platform_workflowtransitionattempt`)

A durable receipt for one "apply this transition to this record" request -- operational state, not declarative metadata (deliberately not a Definition subclass). Mirrors RuntimeProvision/exports.RestoreJob's own reserve-then-execute shape: `completed_at` is the single durable "already fully applied" marker a replayed request short-circuits on (workflows.py's apply_transition checks it before redoing any work), and `idempotency_key` + `request_fingerprint` give the exact same actor-opts-in idempotency RestoreJob's own docstring describes -- a repeat with the same key AND the same fingerprint returns the original outcome; the same key with a different fingerprint is a genuine conflicting request, rejected rather than silently reinterpreted. `record_id` is a bare UUID, not a FK, the same cross-database precedent RecordAttachment.record_id already establishes -- the record itself lives in a raw tenant table this app never models in Django.

| Field | Type | Notes |
|---|---|---|
| `id` | UUIDField | primary key |
| `transition` | ForeignKey | → WorkflowTransition |
| `record_id` | UUIDField |  |
| `idempotency_key` | UUIDField | null |
| `request_fingerprint` | CharField |  |
| `state_before` | CharField |  |
| `state_after` | CharField |  |
| `completed_at` | DateTimeField | null |
| `last_error` | CharField |  |
| `created_by` | ForeignKey | → User |
| `created_at` | DateTimeField |  |

### WorkflowNotificationDelivery (`app_platform_workflownotificationdelivery`)

An at-least-once outbox row for one transition attempt's notification -- one row per attempt that had a `notify_url` at the moment it completed. `url` is a denormalized copy taken at that moment, not a live read of the transition's current `notify_url`, so editing a transition's notification target later never rewrites history. `delivered_at` is the exact same kind of durable completion marker WorkflowTransitionAttempt.completed_at is -- the Celery delivery task (app_platform/tasks.py) checks it before ever dialing out. Remote acceptance before that marker commits can cause a repeat; receivers must deduplicate the stable event_id.

| Field | Type | Notes |
|---|---|---|
| `id` | UUIDField | primary key |
| `attempt` | ForeignKey | → WorkflowTransitionAttempt |
| `url` | TextField |  |
| `delivered_at` | DateTimeField | null |
| `attempt_count` | PositiveIntegerField |  |
| `last_error` | CharField |  |
| `created_at` | DateTimeField |  |
| `next_attempt_at` | DateTimeField |  |
| `exhausted_at` | DateTimeField | null |

### WebhookDelivery (`app_platform_webhookdelivery`)

Phase 10: a durable at-least-once outbox row for one `environments.EnvironmentWebhook` delivery of an App Platform event (`app_platform/webhooks.py`) -- the "reliable webhooks" this phase's own exit bar names, and the concrete mechanism `docs/ EXTERNAL_APP_API_CONTRACT.md` previously flagged outright as **NOT YET IMPLEMENTED** ("Webhooks or any push/event-notification mechanism out of App Platform toward an external application").

| Field | Type | Notes |
|---|---|---|
| `id` | UUIDField | primary key |
| `webhook` | ForeignKey | → EnvironmentWebhook |
| `instance` | ForeignKey | → AppInstance |
| `event_type` | CharField |  |
| `payload` | JSONField |  |
| `delivered_at` | DateTimeField | null |
| `attempt_count` | PositiveIntegerField |  |
| `last_error` | CharField |  |
| `created_at` | DateTimeField |  |
| `next_attempt_at` | DateTimeField |  |
| `exhausted_at` | DateTimeField | null |

### UnitScopedGrant (`app_platform_unitscopedgrant`)

Phase 7 Step 3 ("unit scope"): grants one user read/write access to a model's records, restricted to records whose org_unit_reference field equals `unit`. Real FKs to both `model` and `unit` -- unlike org_unit_reference itself, both rows here live in the control-plane database (this app and org_units), so there's no cross-database problem to work around.

| Field | Type | Notes |
|---|---|---|
| `id` | UUIDField | primary key |
| `model` | ForeignKey | → ModelDefinition |
| `unit` | ForeignKey | → OrganizationalUnit |
| `user` | ForeignKey | → User |
| `level` | CharField | choices: read, write |
| `granted_by` | ForeignKey | null; → User |
| `expires_at` | DateTimeField | null |
| `created_at` | DateTimeField |  |

### AppInstanceUpgrade (`app_platform_appinstanceupgrade`)

Phase 9: a durable receipt for one `upgrades.apply_upgrade` call -- operational history, not declarative metadata (deliberately not a `Definition` subclass, the same distinction `WorkflowTransitionAttempt` already draws above). `summary` is the full three-way diff this call computed (see `upgrades.py`): every item added or label-synced, and every item that needed a human because it conflicted with a local customization, changed something a live migration can't safely apply, or was removed upstream -- recorded even when it wasn't applied, never silently dropped. There is nothing here to *resume*: `apply_upgrade` runs entirely inside one control-plane transaction (plus one nested tenant transaction for any real DDL), so a crash mid-call leaves nothing partially applied -- Postgres's own transactional DDL is the recovery mechanism, matching every other schema_evolution.py caller (RuntimeProvision/WorkflowTransitionAttempt need their own resumable- job machinery only because they span an async Celery task; this doesn't).

| Field | Type | Notes |
|---|---|---|
| `id` | UUIDField | primary key |
| `instance` | ForeignKey | → AppInstance |
| `from_version` | ForeignKey | → AppTemplateVersion |
| `to_version` | ForeignKey | → AppTemplateVersion |
| `summary` | JSONField |  |
| `created_by` | ForeignKey | → User |
| `created_at` | DateTimeField |  |

### QuantityLedgerBinding (`app_platform_quantityledgerbinding`)

ADR-0016's closing half: an opt-in, administrator-validated binding between an append-only movement model's field and the balance model's field its inserts must atomically maintain, over a shared set of relationship "dimensions" (e.g. Part, Warehouse) -- `operation_journal.py` covers durable audit/webhook evidence for a mutation that already committed; this covers making the mutation itself atomic (and concurrency-safe, and rejecting an insufficient balance) in the first place, enforced by a real Postgres trigger installed by `quantity_ledger.bind()`, not application code -- so it holds even for a direct SQL insert that never goes through `records.py`.

| Field | Type | Notes |
|---|---|---|
| `id` | UUIDField | primary key |
| `instance` | ForeignKey | → AppInstance |
| `balance_model` | ForeignKey | → ModelDefinition |
| `balance_field` | ForeignKey | → FieldDefinition |
| `unique_constraint` | ForeignKey | → ConstraintDefinition |
| `movement_model` | ForeignKey | → ModelDefinition |
| `movement_field` | ForeignKey | → FieldDefinition |
| `allow_negative` | BooleanField |  |
| `created_by` | ForeignKey | → User |
| `created_at` | DateTimeField |  |

### QuantityLedgerDimension (`app_platform_quantityledgerdimension`)

One (balance relationship, movement relationship) pair identifying the same real-world dimension on both sides of a QuantityLedgerBinding. Both must be many_to_one relationships whose own `target_model` matches, and whose `source_model` is the binding's `balance_model`/ `movement_model` respectively -- validated in `quantity_ledger.bind()`, not by a DB constraint spanning definitions this way, the same discipline `ConstraintDefinition`'s own docstring already documents for its cross-table membership rules.

| Field | Type | Notes |
|---|---|---|
| `id` | UUIDField | primary key |
| `binding` | ForeignKey | → QuantityLedgerBinding |
| `balance_relationship` | ForeignKey | → RelationshipDefinition |
| `movement_relationship` | ForeignKey | → RelationshipDefinition |

## applications

### Application (`applications_application`)

A registered piece of software, owned by an Organization, with an owning User (docs/architecture/DATA_MODEL.md Section 3.7).

| Field | Type | Notes |
|---|---|---|
| `id` | UUIDField | primary key |
| `organization` | ForeignKey | → Organization |
| `name` | CharField |  |
| `description` | TextField |  |
| `owner` | ForeignKey | → User |
| `created_at` | DateTimeField |  |

### ServiceAccount (`applications_serviceaccount`)

The identity an Application authenticates as. Deliberately backed by a real `accounts.User` row (`identity_user`, unusable password — it can never log into the web UI) rather than a parallel principal type: every existing permission check, RoleAssignment, ResourceGrant, and tenant-membership lookup already works in terms of `User`, and duplicating that machinery for a second principal type would be a second, easy-to-miss place for the isolation invariants in docs/security/THREAT_MODEL.md Section 4 to be re-implemented (and potentially get wrong). A Membership row (created alongside this one, see applications/services.py) makes the identity_user resolvable by every existing get_member_* helper; Membership alone grants no permissions, so this doesn't widen access — only RoleAssignment/ ResourceGrant do that, exactly as for a human user.

| Field | Type | Notes |
|---|---|---|
| `id` | UUIDField | primary key |
| `application` | OneToOneField | unique; → Application |
| `identity_user` | OneToOneField | unique; → User |
| `created_at` | DateTimeField |  |

### ApplicationCredential (`applications_applicationcredential`)

Never stores the plaintext secret — only its SHA-256 hash (fast hash, not a slow password hasher: the secret is a high-entropy random token generated by the server, not a user-chosen password, so brute- force/rainbow-table resistance from a slow hash isn't the relevant property here — Section 13 of the master prompt: never store plaintext long-term secrets when a secure hash is sufficient). The plaintext is returned exactly once, at creation/rotation time, by applications/services.py — never persisted, never logged.

| Field | Type | Notes |
|---|---|---|
| `id` | UUIDField | primary key |
| `service_account` | ForeignKey | → ServiceAccount |
| `environment` | ForeignKey | null; → Environment |
| `secret_hash` | CharField | unique |
| `created_by` | ForeignKey | null; → User |
| `created_at` | DateTimeField |  |
| `last_used_at` | DateTimeField | null |
| `expires_at` | DateTimeField | null |
| `revoked_at` | DateTimeField | null |

### ApiRequestLog (`applications_apirequestlog`)

One request an application made with its bearer credential, for the application's Requests page: what it called and how it went. Never the query string, a body or a header (they can carry data or the secret itself). Kept API_REQUEST_LOG_DAYS days (applications.tasks.prune_api_request_log).

| Field | Type | Notes |
|---|---|---|
| `id` | BigAutoField | primary key |
| `application` | ForeignKey | → Application |
| `credential` | ForeignKey | null; → ApplicationCredential |
| `method` | CharField |  |
| `path` | CharField |  |
| `status` | PositiveSmallIntegerField |  |
| `duration_ms` | PositiveIntegerField |  |
| `at` | DateTimeField |  |

## audit

### AuditEvent (`audit_auditevent`)

| Field | Type | Notes |
|---|---|---|
| `id` | UUIDField | primary key |
| `timestamp` | DateTimeField |  |
| `actor` | ForeignKey | null; → User |
| `organization` | ForeignKey | null; → Organization |
| `action` | CharField |  |
| `resource_type` | CharField |  |
| `resource_id` | CharField |  |
| `request_id` | CharField |  |
| `result` | CharField | choices: success, denied, error |
| `context` | JSONField |  |

## catalogue_storage

### OEMPart (`catalogue_storage_oempart`)

Answers "what part is this" — never a selling price, stock level, or anything else that answers "what will we sell it for" (that's the spare-parts application's own CustomerCatalogueItem, deliberately not duplicated here — see the module docstring).

| Field | Type | Notes |
|---|---|---|
| `id` | UUIDField | primary key |
| `manufacturer` | CharField |  |
| `part_number` | CharField |  |
| `normalized_part_number` | CharField | unique |
| `description` | CharField |  |
| `applicability` | CharField |  |
| `fitment_notes` | CharField |  |
| `created_at` | DateTimeField |  |
| `updated_at` | DateTimeField |  |

### Diagram (`catalogue_storage_diagram`)

| Field | Type | Notes |
|---|---|---|
| `id` | UUIDField | primary key |
| `provider` | CharField |  |
| `provider_diagram_id` | CharField |  |
| `diagram_code` | CharField |  |
| `file` | ForeignKey | null; → FileObject |
| `source_image_url` | URLField |  |
| `figure_data` | JSONField |  |
| `license_status` | CharField | choices: EXTERNAL_REFERENCE_ONLY, LOCALLY_STORED |
| `created_at` | DateTimeField |  |
| `updated_at` | DateTimeField |  |

### DiagramPart (`catalogue_storage_diagrampart`)

One diagram can show many parts; one part can appear on more than one diagram (a different production run's exploded view, for instance) -- this is a genuine many-to-many, not a FK on either side. `x`/`y`/`width`/`height` are the provider's own real hotspot rectangle when it supplies one; left null otherwise -- never fabricated (see docs/CATALOGUE_STORAGE.md "Image highlighting").

| Field | Type | Notes |
|---|---|---|
| `id` | UUIDField | primary key |
| `diagram` | ForeignKey | → Diagram |
| `part` | ForeignKey | → OEMPart |
| `callout` | CharField |  |
| `x` | FloatField | null |
| `y` | FloatField | null |
| `width` | FloatField | null |
| `height` | FloatField | null |
| `created_at` | DateTimeField |  |

## databases

### TenantDatabase (`databases_tenantdatabase`)

A logical database the platform manages for a Project. Maps 1:1 to one physical PostgreSQL schema in the tenant cluster (docs/architecture/adr/0005-tenant-database-isolation-strategy.md). `schema_name` is server-generated from this row's own UUID — never derived from user input (Section 5/8 of the master prompt).

| Field | Type | Notes |
|---|---|---|
| `id` | UUIDField | primary key |
| `project` | ForeignKey | → Project |
| `environment` | OneToOneField | null; unique; → Environment |
| `name` | CharField |  |
| `schema_name` | CharField | unique |
| `created_at` | DateTimeField |  |
| `created_by` | ForeignKey | → User |

### DBTable (`databases_dbtable`)

| Field | Type | Notes |
|---|---|---|
| `id` | UUIDField | primary key |
| `tenant_database` | ForeignKey | → TenantDatabase |
| `name` | CharField |  |
| `created_at` | DateTimeField |  |
| `created_by` | ForeignKey | → User |

### DBColumn (`databases_dbcolumn`)

| Field | Type | Notes |
|---|---|---|
| `id` | UUIDField | primary key |
| `table` | ForeignKey | → DBTable |
| `name` | CharField |  |
| `data_type` | CharField | choices: text, varchar, integer, bigint, decimal, boolean, date, datetime, uuid, json |
| `max_length` | PositiveIntegerField | null |
| `precision` | PositiveIntegerField | null |
| `scale` | PositiveIntegerField | null |
| `is_primary_key` | BooleanField |  |
| `is_nullable` | BooleanField |  |
| `is_unique` | BooleanField |  |
| `default_value` | JSONField | null |
| `created_at` | DateTimeField |  |

### DBForeignKey (`databases_dbforeignkey`)

| Field | Type | Notes |
|---|---|---|
| `id` | UUIDField | primary key |
| `column` | OneToOneField | unique; → DBColumn |
| `references_table` | ForeignKey | → DBTable |
| `references_column` | ForeignKey | → DBColumn |
| `on_delete` | CharField | choices: cascade, restrict, set_null |
| `created_at` | DateTimeField |  |

### ConnectedDatabase (`databases_connecteddatabase`)

An externally-hosted database reached in **connected mode**: the platform proxies authenticated read queries to it; nothing is copied in. Deliberately a distinct model from `TenantDatabase` — a single connection is never simultaneously "connected" and "imported" (docs/architecture/adr/0009-external-database-connector-modes.md). `encrypted_password` is a Fernet token (`databases/crypto.py`); the plaintext password is never stored and never returned by any API response.

| Field | Type | Notes |
|---|---|---|
| `id` | UUIDField | primary key |
| `project` | ForeignKey | → Project |
| `name` | CharField |  |
| `engine` | CharField | choices: postgresql |
| `host` | CharField |  |
| `port` | PositiveIntegerField |  |
| `database_name` | CharField |  |
| `username` | CharField |  |
| `encrypted_password` | BinaryField |  |
| `sslmode` | CharField | choices: disable, prefer, require, verify-full |
| `status` | CharField | choices: untested, connected, unreachable |
| `last_tested_at` | DateTimeField | null |
| `last_test_error` | CharField |  |
| `created_at` | DateTimeField |  |
| `created_by` | ForeignKey | → User |

### DBIndex (`databases_dbindex`)

Created automatically alongside unique columns and primary keys — not (yet) a user-facing "create an arbitrary index" feature; still a real catalog entry mirroring what actually exists in the tenant schema, per docs/architecture/DATA_MODEL.md Section 3.5.

| Field | Type | Notes |
|---|---|---|
| `id` | UUIDField | primary key |
| `table` | ForeignKey | → DBTable |
| `name` | CharField | unique |
| `is_unique` | BooleanField |  |
| `created_at` | DateTimeField |  |
| `columns` | ManyToManyField | → DBColumn |

## environments

### Environment (`environments_environment`)

| Field | Type | Notes |
|---|---|---|
| `id` | UUIDField | primary key |
| `application` | ForeignKey | → Application |
| `name` | CharField |  |
| `slug` | SlugField |  |
| `environment_type` | CharField | choices: development, staging, production, custom |
| `is_production_tier` | BooleanField |  |
| `status` | CharField | choices: active, disabled |
| `config` | JSONField |  |
| `created_by` | ForeignKey | → User |
| `created_at` | DateTimeField |  |
| `updated_at` | DateTimeField |  |
| `last_activity_at` | DateTimeField | null |

### EnvironmentVariable (`environments_environmentvariable`)

Plain, non-secret configuration (e.g. LOG_LEVEL=debug). Secret values never belong here — see EnvironmentSecret.

| Field | Type | Notes |
|---|---|---|
| `id` | UUIDField | primary key |
| `environment` | ForeignKey | → Environment |
| `key` | CharField |  |
| `value` | TextField |  |
| `created_at` | DateTimeField |  |
| `updated_at` | DateTimeField |  |

### EnvironmentSecret (`environments_environmentsecret`)

Never stores a plaintext value -- only a Fernet ciphertext (environments/crypto.py, same CREDENTIAL_ENCRYPTION_KEY-derived key as accounts/databases' equivalent modules). The plaintext is known only at creation/rotation time, in the API response body for that one request, and is never logged, never included in an audit event context, and never re-displayed by any read endpoint afterward.

| Field | Type | Notes |
|---|---|---|
| `id` | UUIDField | primary key |
| `environment` | ForeignKey | → Environment |
| `key` | CharField |  |
| `value_ciphertext` | BinaryField |  |
| `created_by` | ForeignKey | null; → User |
| `created_at` | DateTimeField |  |
| `rotated_at` | DateTimeField | null |

### EnvironmentWebhook (`environments_environmentwebhook`)

The signing secret is encrypted the same way EnvironmentSecret's values are -- never returned by a read endpoint after creation.

| Field | Type | Notes |
|---|---|---|
| `id` | UUIDField | primary key |
| `environment` | ForeignKey | → Environment |
| `url` | URLField |  |
| `event_types` | JSONField |  |
| `enabled` | BooleanField |  |
| `signing_secret_ciphertext` | BinaryField |  |
| `created_by` | ForeignKey | null; → User |
| `created_at` | DateTimeField |  |

## exports

### ExportJob (`exports_exportjob`)

One .icp portable-export package build for one Organization (the only export_type implemented so far — Section 14 of the master prompt lists several narrower scopes as future work). The finished package is written to object storage, not the control-plane database — this row is metadata/status only (ADR-0001).

| Field | Type | Notes |
|---|---|---|
| `id` | UUIDField | primary key |
| `organization` | ForeignKey | → Organization |
| `created_by` | ForeignKey | → User |
| `status` | CharField | choices: pending, running, completed, failed |
| `encrypted` | BooleanField |  |
| `object_key` | CharField |  |
| `size_bytes` | BigIntegerField | null |
| `checksum_sha256` | CharField |  |
| `error_message` | CharField |  |
| `created_at` | DateTimeField |  |
| `completed_at` | DateTimeField | null |

### RestoreJob (`exports_restorejob`)

One .icp import/restore attempt. `organization` is null until the restore actually creates the new Organization (Section 17 of the master prompt: nothing should be visible/reachable until the whole restore either fully commits or fully rolls back) — see exports/restorer.py.

| Field | Type | Notes |
|---|---|---|
| `id` | UUIDField | primary key |
| `organization` | ForeignKey | null; → Organization |
| `created_by` | ForeignKey | → User |
| `status` | CharField | choices: pending, validating, restoring, completed, failed |
| `source_object_key` | CharField |  |
| `recovery_version` | PositiveSmallIntegerField |  |
| `source_sha256` | CharField |  |
| `idempotency_key` | UUIDField | null |
| `request_fingerprint` | CharField |  |
| `report` | JSONField |  |
| `error_message` | CharField |  |
| `created_at` | DateTimeField |  |
| `completed_at` | DateTimeField | null |

## hosted_sites

### Site (`hosted_sites_site`)

| Field | Type | Notes |
|---|---|---|
| `id` | UUIDField | primary key |
| `organization` | ForeignKey | → Organization |
| `name` | CharField |  |
| `slug` | SlugField | unique |
| `hostname` | CharField | null; unique |
| `status` | CharField | choices: active, disabled |
| `single_page_app` | BooleanField |  |
| `kind` | CharField | choices: static, node |
| `application` | ForeignKey | null; → Application |
| `internet_hostname` | CharField | null; unique |
| `internet_published_by` | ForeignKey | null; → User |
| `internet_published_at` | DateTimeField | null |
| `internet_auto` | BooleanField |  |
| `runtime_state` | CharField |  |
| `runtime_log` | TextField |  |
| `active_version` | ForeignKey | null; → SiteVersion |
| `created_by` | ForeignKey | null; → User |
| `created_at` | DateTimeField |  |
| `updated_at` | DateTimeField |  |

### SiteVersion (`hosted_sites_siteversion`)

| Field | Type | Notes |
|---|---|---|
| `id` | UUIDField | primary key |
| `site` | ForeignKey | → Site |
| `number` | PositiveIntegerField |  |
| `original_filename` | CharField |  |
| `files` | JSONField |  |
| `file_count` | PositiveIntegerField |  |
| `total_bytes` | BigIntegerField |  |
| `notes` | JSONField |  |
| `manifest` | JSONField |  |
| `uploaded_by` | ForeignKey | null; → User |
| `created_at` | DateTimeField |  |

### InternetGateway (`hosted_sites_internetgateway`)

The one internet gate of this installation (ADR-0020 decision 4): off unless the Super Administrator switches it on. The Cloudflare Tunnel token is kept encrypted and never shown again.

| Field | Type | Notes |
|---|---|---|
| `id` | PositiveSmallIntegerField | primary key |
| `enabled` | BooleanField |  |
| `token_encrypted` | BinaryField | null |
| `auto_domain` | CharField |  |
| `changed_by` | ForeignKey | null; → User |
| `changed_at` | DateTimeField | null |

## imports

### ImportJob (`imports_importjob`)

| Field | Type | Notes |
|---|---|---|
| `id` | UUIDField | primary key |
| `file` | ForeignKey | → FileObject |
| `table` | ForeignKey | → DBTable |
| `encoding` | CharField |  |
| `delimiter` | CharField |  |
| `column_mapping` | JSONField |  |
| `status` | CharField | choices: pending, running, completed, failed |
| `total_rows` | PositiveIntegerField | null |
| `imported_rows` | PositiveIntegerField |  |
| `rejected_rows` | PositiveIntegerField |  |
| `last_processed_row` | PositiveIntegerField |  |
| `error_message` | TextField |  |
| `created_by` | ForeignKey | → User |
| `created_at` | DateTimeField |  |
| `started_at` | DateTimeField | null |
| `completed_at` | DateTimeField | null |

### ImportJobError (`imports_importjoberror`)

| Field | Type | Notes |
|---|---|---|
| `id` | UUIDField | primary key |
| `job` | ForeignKey | → ImportJob |
| `row_number` | PositiveIntegerField |  |
| `message` | CharField |  |
| `raw_row` | JSONField |  |
| `created_at` | DateTimeField |  |

## licensing

### LicenseState (`licensing_licensestate`)

| Field | Type | Notes |
|---|---|---|
| `id` | BigAutoField | primary key |
| `trial_started_at` | DateTimeField |  |
| `last_seen_at` | DateTimeField |  |
| `serial` | CharField |  |
| `activation_code` | TextField |  |
| `activated_at` | DateTimeField | null |
| `activated_by` | ForeignKey | null; → User |

## movie_shop

### MovieShop (`movie_shop_movieshop`)

| Field | Type | Notes |
|---|---|---|
| `id` | UUIDField | primary key |
| `organization` | ForeignKey | → Organization |
| `project` | ForeignKey | → Project |
| `name` | CharField |  |
| `default_price` | PositiveIntegerField |  |
| `agent_application` | OneToOneField | null; unique; → Application |
| `covers_bucket` | OneToOneField | null; unique; → Bucket |
| `agent_report` | JSONField |  |
| `agent_seen_at` | DateTimeField | null |
| `portal_open` | BooleanField |  |
| `welcome_points` | PositiveIntegerField |  |
| `referral_points` | PositiveIntegerField |  |
| `birthday_points` | PositiveIntegerField |  |
| `every_nth_free` | PositiveSmallIntegerField |  |
| `created_by` | ForeignKey | → User |
| `created_at` | DateTimeField |  |

### CategoryPrice (`movie_shop_categoryprice`)

The price of every title in one category (folder), unless a title sets its own.

| Field | Type | Notes |
|---|---|---|
| `id` | BigAutoField | primary key |
| `shop` | ForeignKey | → MovieShop |
| `category` | CharField |  |
| `price` | PositiveIntegerField |  |

### Library (`movie_shop_library`)

One folder on one of the shop PC's drives, as the media agent sees it (``D:\Movies``).

| Field | Type | Notes |
|---|---|---|
| `id` | UUIDField | primary key |
| `shop` | ForeignKey | → MovieShop |
| `name` | CharField |  |
| `path` | CharField |  |
| `kind` | CharField | choices: fixed, removable, network |
| `total_bytes` | BigIntegerField | null |
| `free_bytes` | BigIntegerField | null |
| `scan_requested_at` | DateTimeField | null |
| `scan_generation` | PositiveIntegerField |  |
| `scanned_generation` | PositiveIntegerField |  |
| `last_scan_at` | DateTimeField | null |
| `last_scan_message` | CharField |  |
| `created_at` | DateTimeField |  |

### Title (`movie_shop_title`)

| Field | Type | Notes |
|---|---|---|
| `id` | UUIDField | primary key |
| `shop` | ForeignKey | → MovieShop |
| `library` | ForeignKey | → Library |
| `relative_path` | CharField |  |
| `category` | CharField |  |
| `title` | CharField |  |
| `year` | PositiveSmallIntegerField | null |
| `kind` | CharField | choices: movie, series, music, album |
| `size_bytes` | BigIntegerField |  |
| `episodes` | PositiveIntegerField |  |
| `seen_generation` | PositiveIntegerField |  |
| `cover` | ForeignKey | null; → FileObject |
| `cover_fingerprint` | CharField |  |
| `cover_locked` | BooleanField |  |
| `price` | PositiveIntegerField | null |
| `hidden` | BooleanField |  |
| `description` | TextField |  |
| `edited` | BooleanField |  |
| `created_at` | DateTimeField |  |
| `updated_at` | DateTimeField |  |

### PortalCustomer (`movie_shop_portalcustomer`)

A customer of one shop's portal (ADR-0022 decision 7). Not an IntraForge user: signs in only to this shop's portal, with a phone number and a password, and can do nothing else in IntraForge.

| Field | Type | Notes |
|---|---|---|
| `id` | UUIDField | primary key |
| `shop` | ForeignKey | → MovieShop |
| `name` | CharField |  |
| `phone` | CharField |  |
| `password` | CharField |  |
| `birthday` | DateField | null |
| `referral_code` | CharField |  |
| `referred_by` | ForeignKey | null; → PortalCustomer |
| `status` | CharField | choices: pending, approved, rejected, blocked |
| `pay_wallet_id` | UUIDField | null |
| `pay_username` | CharField |  |
| `approved_at` | DateTimeField | null |
| `approved_by` | ForeignKey | null; → User |
| `birthday_points_year` | PositiveSmallIntegerField | null |
| `reset_requested_at` | DateTimeField | null |
| `created_at` | DateTimeField |  |

### PortalSession (`movie_shop_portalsession`)

A portal sign-in: the cookie holds a random token, this table only its SHA-256.

| Field | Type | Notes |
|---|---|---|
| `token_hash` | CharField | primary key |
| `customer` | ForeignKey | → PortalCustomer |
| `created_at` | DateTimeField |  |
| `expires_at` | DateTimeField |  |
| `revoked_at` | DateTimeField | null |

### PointsEntry (`movie_shop_pointsentry`)

The points ledger: a customer's points are the sum of their entries. Never edited; a reversal is an entry.

| Field | Type | Notes |
|---|---|---|
| `id` | BigAutoField | primary key |
| `customer` | ForeignKey | → PortalCustomer |
| `delta` | IntegerField |  |
| `reason` | CharField | choices: welcome, referral, birthday, redeem, returned, adjust |
| `sale` | ForeignKey | null; → Sale |
| `note` | CharField |  |
| `created_at` | DateTimeField |  |

### Sale (`movie_shop_sale`)

A counter sale: titles for one customer, paid with IntraForge Pay (or cash), then copied by the media agent onto the customer's drive. Nothing here holds money: Pay keeps the payment and its receipt (ADR-0022 decision 6).

| Field | Type | Notes |
|---|---|---|
| `id` | UUIDField | primary key |
| `shop` | ForeignKey | → MovieShop |
| `number` | CharField | unique |
| `status` | CharField | choices: ordered, awaiting_payment, paid, done, cancelled |
| `method` | CharField | choices: ifpay, cash |
| `customer_name` | CharField |  |
| `total` | PositiveIntegerField |  |
| `destination` | CharField |  |
| `folder` | CharField |  |
| `pay_request_id` | UUIDField | null |
| `pay_code` | TextField |  |
| `pay_qr_svg` | TextField |  |
| `pay_expires_at` | DateTimeField | null |
| `receipt_number` | CharField |  |
| `paid_at` | DateTimeField | null |
| `customer` | ForeignKey | null; → PortalCustomer |
| `use_points` | BooleanField |  |
| `points_used` | PositiveIntegerField |  |
| `discount` | PositiveIntegerField |  |
| `created_by` | ForeignKey | null; → User |
| `created_at` | DateTimeField |  |

### SaleLine (`movie_shop_saleline`)

One title in a sale, as it was when sold (the catalogue may change later), and its copy onto the drive.

| Field | Type | Notes |
|---|---|---|
| `id` | UUIDField | primary key |
| `sale` | ForeignKey | → Sale |
| `title` | ForeignKey | null; → Title |
| `library` | ForeignKey | null; → Library |
| `title_name` | CharField |  |
| `category` | CharField |  |
| `relative_path` | CharField |  |
| `kind` | CharField |  |
| `price` | PositiveIntegerField |  |
| `size_bytes` | BigIntegerField |  |
| `free` | BooleanField |  |
| `copy_status` | CharField | choices: waiting, copying, copied, failed |
| `copied_bytes` | BigIntegerField |  |
| `copy_message` | CharField |  |
| `copy_updated_at` | DateTimeField | null |

### Ad (`movie_shop_ad`)

An advertisement the shop shows on its own portal (ADR-0022 decision 8, phase 4): for the shop itself, one of its films, or another business the shop advertises for. Never shown anywhere else.

| Field | Type | Notes |
|---|---|---|
| `id` | UUIDField | primary key |
| `shop` | ForeignKey | → MovieShop |
| `title` | CharField |  |
| `text` | CharField |  |
| `advertiser` | CharField |  |
| `film` | ForeignKey | null; → Title |
| `link` | URLField |  |
| `picture` | ForeignKey | null; → FileObject |
| `starts_on` | DateField | null |
| `ends_on` | DateField | null |
| `active` | BooleanField |  |
| `position` | PositiveIntegerField |  |
| `views` | PositiveIntegerField |  |
| `taps` | PositiveIntegerField |  |
| `created_by` | ForeignKey | null; → User |
| `created_at` | DateTimeField |  |

### PasswordResetCode (`movie_shop_passwordresetcode`)

A one-time code the owner gives a customer to choose a new portal password (shown once; only its hash is kept).

| Field | Type | Notes |
|---|---|---|
| `id` | BigAutoField | primary key |
| `customer` | ForeignKey | → PortalCustomer |
| `code_hash` | CharField |  |
| `created_by` | ForeignKey | null; → User |
| `created_at` | DateTimeField |  |
| `expires_at` | DateTimeField |  |
| `used_at` | DateTimeField | null |
| `attempts` | PositiveSmallIntegerField |  |

## oauth_provider

### OAuthClient (`oauth_provider_oauthclient`)

| Field | Type | Notes |
|---|---|---|
| `id` | UUIDField | primary key |
| `name` | CharField |  |
| `client_id` | CharField | unique |
| `client_secret_hash` | CharField |  |
| `application_type` | CharField | choices: confidential_web |
| `redirect_uris` | JSONField |  |
| `post_logout_redirect_uris` | JSONField |  |
| `allowed_origins` | JSONField |  |
| `enabled` | BooleanField |  |
| `requires_consent` | BooleanField |  |
| `created_by` | ForeignKey | null; → User |
| `created_at` | DateTimeField |  |
| `updated_at` | DateTimeField |  |

### OAuthAuthorizationCode (`oauth_provider_oauthauthorizationcode`)

Single-use, short-lived (services.py: `AUTHORIZATION_CODE_TTL_SECONDS`). The plaintext code is returned to the client exactly once, in the redirect — only its hash is stored, same rationale as ApplicationCredential/the code itself is never sensitive-data-bearing: it is a random lookup key, not a signed/encoded claim carrier.

| Field | Type | Notes |
|---|---|---|
| `id` | UUIDField | primary key |
| `code_hash` | CharField | unique |
| `client` | ForeignKey | → OAuthClient |
| `user` | ForeignKey | → User |
| `redirect_uri` | CharField |  |
| `scope` | CharField |  |
| `code_challenge` | CharField |  |
| `code_challenge_method` | CharField |  |
| `nonce` | CharField |  |
| `expires_at` | DateTimeField |  |
| `used_at` | DateTimeField | null |
| `created_at` | DateTimeField |  |

### OAuthAccessToken (`oauth_provider_oauthaccesstoken`)

Opaque, server-validated bearer token — the same shape as ApplicationCredential rather than a JWT, deliberately: this token is looked up and checked (expiry/revocation) on every use, exactly like the platform's existing bearer-token mechanism, and there is no resource server other than IntraForge's own `/oauth/userinfo/` that would need to verify it offline. The `id_token` (models.py has no row for it — see services.py `issue_id_token`) is the one token in this flow with a real offline-verification need (the spare-parts backend must check it without calling back into IntraForge), so it alone is a signed JWT. No refresh token is issued: the spare-parts backend exchanges the code once, reads `/oauth/userinfo/` (or just the ID token) immediately, and mints its OWN long-lived local session from that — this access token only needs to survive that one round trip, so a short, non-renewable lifetime (see ACCESS_TOKEN_TTL_SECONDS) is the deliberately simpler, smaller-attack- surface choice over adding refresh-token rotation/revocation.

| Field | Type | Notes |
|---|---|---|
| `id` | UUIDField | primary key |
| `token_hash` | CharField | unique |
| `client` | ForeignKey | → OAuthClient |
| `user` | ForeignKey | → User |
| `scope` | CharField |  |
| `expires_at` | DateTimeField |  |
| `revoked_at` | DateTimeField | null |
| `created_at` | DateTimeField |  |

### OAuthSigningKey (`oauth_provider_oauthsigningkey`)

RSA keypair used to sign `id_token` JWTs (RS256). The private key is Fernet-encrypted at rest (oauth_provider/crypto.py, same pattern as accounts/crypto.py's MFA-secret encryption, keyed by the existing CREDENTIAL_ENCRYPTION_KEY — no new secret to provision). `kid` is this row's own id, published in the JWKS alongside the public key so a client can select the right key after rotation; `active` marks the one key new tokens are signed with, while older, still-`active=False` keys remain published (until deliberately deleted) so a JWKS consumer can still verify a token issued just before a rotation.

| Field | Type | Notes |
|---|---|---|
| `id` | UUIDField | primary key |
| `private_key_encrypted` | BinaryField |  |
| `public_key_pem` | TextField |  |
| `algorithm` | CharField |  |
| `active` | BooleanField |  |
| `created_at` | DateTimeField |  |

### OAuthConsent (`oauth_provider_oauthconsent`)

A person's "Allow" for one application, and the scopes it covered. An application asking for more later asks again; deleting the row (or the client) withdraws it.

| Field | Type | Notes |
|---|---|---|
| `id` | UUIDField | primary key |
| `client` | ForeignKey | → OAuthClient |
| `user` | ForeignKey | → User |
| `scope` | CharField |  |
| `created_at` | DateTimeField |  |
| `updated_at` | DateTimeField |  |

## org_units

### OrganizationalUnit (`org_units_organizationalunit`)

A node in an organization's own structural hierarchy (branch, campus, department, warehouse, team, or any other label the organization chooses -- `unit_type` is a free-form descriptive label, never a hardcoded enum, so this stays a generic primitive rather than baking one industry's vocabulary into the platform, matching the App Platform's own "no industry-specific concept in the core" rule (see docs/implementation/APP_PLATFORM_PHASE4.md).

| Field | Type | Notes |
|---|---|---|
| `id` | UUIDField | primary key |
| `organization` | ForeignKey | → Organization |
| `parent` | ForeignKey | null; → OrganizationalUnit |
| `unit_type` | CharField |  |
| `name` | CharField |  |
| `created_at` | DateTimeField |  |
| `created_by` | ForeignKey | → User |

### UnitMembership (`org_units_unitmembership`)

A user's placement in a unit. Many-to-many by design (unlike organizations.Membership.team's single nullable FK) -- a person can sit in a department and a branch and a team simultaneously.

| Field | Type | Notes |
|---|---|---|
| `id` | UUIDField | primary key |
| `unit` | ForeignKey | → OrganizationalUnit |
| `user` | ForeignKey | → User |
| `created_at` | DateTimeField |  |
| `created_by` | ForeignKey | → User |

## organizations

### Organization (`organizations_organization`)

| Field | Type | Notes |
|---|---|---|
| `id` | UUIDField | primary key |
| `name` | CharField |  |
| `slug` | SlugField | unique |
| `external_sharing_enabled` | BooleanField |  |
| `created_at` | DateTimeField |  |
| `created_by` | ForeignKey | → User |

### Team (`organizations_team`)

| Field | Type | Notes |
|---|---|---|
| `id` | UUIDField | primary key |
| `organization` | ForeignKey | → Organization |
| `name` | CharField |  |
| `created_at` | DateTimeField |  |

### Membership (`organizations_membership`)

| Field | Type | Notes |
|---|---|---|
| `id` | UUIDField | primary key |
| `user` | ForeignKey | → User |
| `organization` | ForeignKey | → Organization |
| `team` | ForeignKey | null; → Team |
| `status` | CharField | choices: invited, active, suspended |
| `invited_by` | ForeignKey | null; → User |
| `created_at` | DateTimeField |  |

## permissions

### Permission (`permissions_permission`)

Static, code-defined capability string (e.g. "storage.read"). The catalog is seeded from permissions.catalog.PERMISSIONS via the `seed_permissions` management command — never created ad hoc through the API (docs/security/PERMISSIONS.md Section 2).

| Field | Type | Notes |
|---|---|---|
| `code` | CharField | primary key |
| `description` | CharField |  |

### Role (`permissions_role`)

A named bundle of Permissions. `organization=None` marks one of the seeded system roles (docs/security/PERMISSIONS.md Section 3), usable by every organization and never deletable/renamable. An organization may later define its own custom roles (organization set, is_system=False) — not exercised yet in Phase 2.

| Field | Type | Notes |
|---|---|---|
| `id` | UUIDField | primary key |
| `organization` | ForeignKey | null; → Organization |
| `slug` | SlugField |  |
| `name` | CharField |  |
| `is_system` | BooleanField |  |
| `created_at` | DateTimeField |  |
| `permissions` | ManyToManyField | → Permission |

### RoleAssignment (`permissions_roleassignment`)

Grants a Role to a User, either scoped to one Organization or, for platform-wide operators, `organization=None`. A null organization is only valid when the assigned Role includes `system.admin` (enforced in permissions.services.assign_role, not at the DB layer, since "which permissions a role has" is data, not schema).

| Field | Type | Notes |
|---|---|---|
| `id` | UUIDField | primary key |
| `user` | ForeignKey | → User |
| `role` | ForeignKey | → Role |
| `organization` | ForeignKey | null; → Organization |
| `granted_by` | ForeignKey | null; → User |
| `created_at` | DateTimeField |  |

### ResourceGrant (`permissions_resourcegrant`)

Grants exactly one Permission on exactly one resource to one User, with an optional expiry. Used for internal sharing (Phase 9) and for restricting an Application's scope to specific resources (Phase 7) — the same mechanism, per ADR-0008. `resource_type` is a free-form label until concrete resource types exist (Phase 3+); nothing in Phase 2 grants against real resources yet.

| Field | Type | Notes |
|---|---|---|
| `id` | UUIDField | primary key |
| `user` | ForeignKey | → User |
| `permission` | ForeignKey | → Permission |
| `organization` | ForeignKey | → Organization |
| `resource_type` | CharField |  |
| `resource_id` | UUIDField |  |
| `granted_by` | ForeignKey | null; → User |
| `expires_at` | DateTimeField | null |
| `created_at` | DateTimeField |  |

## service_apps

### ServiceApp (`service_apps_serviceapp`)

| Field | Type | Notes |
|---|---|---|
| `id` | UUIDField | primary key |
| `organization` | ForeignKey | → Organization |
| `project` | ForeignKey | → Project |
| `deployment` | CharField | unique |
| `app_type` | CharField | choices: spare_parts, intraforge_pay, pharmacy |
| `display_name` | CharField |  |
| `config` | JSONField |  |
| `enabled` | BooleanField |  |
| `removed_at` | DateTimeField | null |
| `schema_name` | CharField | unique |
| `bucket` | OneToOneField | unique; → Bucket |
| `reported_version` | CharField |  |
| `last_seen_at` | DateTimeField | null |
| `created_by` | ForeignKey | → User |
| `created_at` | DateTimeField |  |
| `updated_at` | DateTimeField |  |

### ServiceAppSession (`service_apps_serviceappsession`)

A browser session for one service application, minted by "Open" in IntraForge.

| Field | Type | Notes |
|---|---|---|
| `id` | BigAutoField | primary key |
| `token_hash` | CharField | unique |
| `service_app` | ForeignKey | → ServiceApp |
| `user` | ForeignKey | → User |
| `django_session_key` | CharField |  |
| `created_at` | DateTimeField |  |
| `expires_at` | DateTimeField |  |
| `last_used_at` | DateTimeField | null |
| `revoked_at` | DateTimeField | null |

### ServiceAppAuditReceipt (`service_apps_serviceappauditreceipt`)

Makes audit relay idempotent: the service sends each event at least once, identified by the id it gave the event in its own transactional log; IntraForge records it exactly once.

| Field | Type | Notes |
|---|---|---|
| `event_id` | CharField | primary key |
| `service_app` | ForeignKey | → ServiceApp |
| `audit_event` | ForeignKey | → AuditEvent |
| `received_at` | DateTimeField |  |

## sharing

### ShareGrant (`sharing_sharegrant`)

Records that a resource was shared with a principal (User/Team/ Organization) at a given level. This is the human-facing "who shared what with whom" record — it is not a second enforcement path. Enforcement is entirely the existing `permissions.ResourceGrant`/ `has_permission` mechanism (docs/architecture/DATA_MODEL.md Section 3.8; permissions/models.py's `ResourceGrant` docstring: "Used for internal sharing (Phase 9) and for restricting an Application's scope to specific resources (Phase 7) — the same mechanism, per ADR-0008"). `sharing/services.py` creates one `ResourceGrant` per (target user, permission code) implied by `level` when a `ShareGrant` is created, and removes them on revoke.

| Field | Type | Notes |
|---|---|---|
| `id` | UUIDField | primary key |
| `organization` | ForeignKey | → Organization |
| `resource_type` | CharField |  |
| `resource_id` | UUIDField |  |
| `principal_type` | CharField | choices: user, team, organization |
| `user` | ForeignKey | null; → User |
| `team` | ForeignKey | null; → Team |
| `level` | CharField | choices: read, write, admin, sell, receive, adjust, transfer |
| `expires_at` | DateTimeField | null |
| `revoked_at` | DateTimeField | null |
| `created_by` | ForeignKey | null; → User |
| `created_at` | DateTimeField |  |

## storage

### Bucket (`storage_bucket`)

| Field | Type | Notes |
|---|---|---|
| `id` | UUIDField | primary key |
| `project` | ForeignKey | → Project |
| `environment` | OneToOneField | null; unique; → Environment |
| `name` | CharField |  |
| `versioning_enabled` | BooleanField |  |
| `trash_days` | PositiveIntegerField |  |
| `version_days` | PositiveIntegerField |  |
| `created_at` | DateTimeField |  |
| `created_by` | ForeignKey | → User |

### Folder (`storage_folder`)

Virtual hierarchy stored as metadata rows (adjacency list) — never a real filesystem directory (docs/architecture/DATA_MODEL.md Section 3.4).

| Field | Type | Notes |
|---|---|---|
| `id` | UUIDField | primary key |
| `bucket` | ForeignKey | → Bucket |
| `parent` | ForeignKey | null; → Folder |
| `name` | CharField |  |
| `created_at` | DateTimeField |  |
| `created_by` | ForeignKey | → User |

### FileObject (`storage_fileobject`)

| Field | Type | Notes |
|---|---|---|
| `id` | UUIDField | primary key |
| `bucket` | ForeignKey | → Bucket |
| `folder` | ForeignKey | null; → Folder |
| `object_key` | CharField | unique |
| `original_filename` | CharField |  |
| `display_filename` | CharField |  |
| `mime_type` | CharField |  |
| `size` | BigIntegerField |  |
| `checksum_sha256` | CharField |  |
| `storage_backend` | CharField |  |
| `status` | CharField | choices: active, deleted, quarantined |
| `creator` | ForeignKey | → User |
| `created_at` | DateTimeField |  |
| `updated_at` | DateTimeField |  |

### FileVersion (`storage_fileversion`)

Append-only version history, populated when a file is overwritten in a bucket with versioning enabled (docs/architecture/DATA_MODEL.md Section 3.4).

| Field | Type | Notes |
|---|---|---|
| `id` | UUIDField | primary key |
| `file` | ForeignKey | → FileObject |
| `object_key` | CharField | unique |
| `size` | BigIntegerField |  |
| `checksum_sha256` | CharField |  |
| `mime_type` | CharField |  |
| `quarantined` | BooleanField |  |
| `created_at` | DateTimeField |  |
| `created_by` | ForeignKey | → User |

### FileShareLink (`storage_filesharelink`)

A link that lets anyone who has it download one file until it expires (at most 30 days), is revoked, or reaches its download limit. Only a hash of the link's token is kept; the link is shown once.

| Field | Type | Notes |
|---|---|---|
| `id` | UUIDField | primary key |
| `file` | ForeignKey | → FileObject |
| `token_hash` | CharField | unique |
| `expires_at` | DateTimeField |  |
| `max_downloads` | PositiveIntegerField | null |
| `downloads` | PositiveIntegerField |  |
| `created_by` | ForeignKey | null; → User |
| `created_at` | DateTimeField |  |
| `revoked_at` | DateTimeField | null |

## system

### BackupRecord (`system_backuprecord`)

One `pg_dump` attempt against a control-plane or tenant PostgreSQL connection (system/backups.py). `verified_restorable` is never set True by the backup itself — only a subsequent, independent restore- and-validate pass against an isolated database sets it (docs/operations/BACKUP_RESTORE.md Section 6/7: "a backup strategy is not considered complete until restoration has actually been tested").

| Field | Type | Notes |
|---|---|---|
| `id` | UUIDField | primary key |
| `backup_type` | CharField | choices: control_db, tenant_db, object_storage, configuration |
| `status` | CharField | choices: running, success, failed |
| `file_path` | CharField |  |
| `size_bytes` | BigIntegerField | null |
| `error_message` | TextField |  |
| `started_at` | DateTimeField |  |
| `completed_at` | DateTimeField | null |
| `verified_restorable` | BooleanField |  |
| `verified_at` | DateTimeField | null |
| `verification_error` | TextField |  |
| `restored_at` | DateTimeField | null |
| `restore_error` | TextField |  |

### HealthSample (`system_healthsample`)

One run of the health checks (system.health.record, every 5 minutes): which checks passed. Kept HEALTH_HISTORY_DAYS days.

| Field | Type | Notes |
|---|---|---|
| `id` | BigAutoField | primary key |
| `at` | DateTimeField |  |
| `checks` | JSONField |  |

### HealthAlert (`system_healthalert`)

A check that failed twice in a row; closed by itself when the check passes again.

| Field | Type | Notes |
|---|---|---|
| `id` | BigAutoField | primary key |
| `check_name` | CharField |  |
| `detail` | CharField |  |
| `opened_at` | DateTimeField |  |
| `closed_at` | DateTimeField | null |

## workspaces

### Workspace (`workspaces_workspace`)

| Field | Type | Notes |
|---|---|---|
| `id` | UUIDField | primary key |
| `organization` | ForeignKey | → Organization |
| `name` | CharField |  |
| `created_at` | DateTimeField |  |
| `created_by` | ForeignKey | → User |

### Project (`workspaces_project`)

| Field | Type | Notes |
|---|---|---|
| `id` | UUIDField | primary key |
| `workspace` | ForeignKey | → Workspace |
| `name` | CharField |  |
| `created_at` | DateTimeField |  |
| `created_by` | ForeignKey | → User |

