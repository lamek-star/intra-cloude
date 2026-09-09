# App Platform — Phase 1 architecture

Continuation: the [ten-phase delivery roadmap](implementation/APP_PLATFORM_ROADMAP.md)
tracks the master brief. [Phase 2](implementation/APP_PLATFORM_PHASE2.md) has
started with a read-only runtime schema planner and now includes resumable
tenant provisioning ([ADR-0015](architecture/adr/0015-runtime-provisioning.md)).
Generic app record APIs/screens remain pending; generated tables use existing
database access. The Phase 1 contract below remains the
baseline until a later verified checkpoint explicitly supersedes it.

## Baseline and scope

Code baseline: `56c34a821b2deae4b0cac3276e4a8145931e62db` on
`rebrand/intraforge`; reconciled documentation baseline:
`389d84a842667742ea53761422e4fe173077b3bc`. Phase 1 branch:
`feature/app-platform`. Recommended tag `pre-app-platform-baseline` refers
to the reconciled baseline; no tag is created or pushed.

Phase 1 represents reusable definitions, immutable releases, and independent
installations. It does not create business-record tables, runtime screens,
an App Builder, workflows, industry applications, or a marketplace. The
existing DRF browsable API is sufficient for this foundation; no new frontend
screen is required.

## Terminology and ownership

Existing `applications.Application` is an integration identity with service
accounts, bearer credentials, and Environments. Its model, routes, frontend
developer portal, and `application.*` capabilities remain unchanged.

New bounded Django app: `app_platform`. `AppTemplate` belongs to an existing
Organization. `AppTemplateVersion` belongs to that template. `AppInstance`
belongs explicitly to the same Organization and to one existing Project
(through Workspace). No additional ownership hierarchy is introduced.
`ModelDefinition`, `FieldDefinition`, and `RelationshipDefinition` inherit
organization ownership through their instance; fields through their model.

Only organization-owned templates are supported initially. No global catalog
or cross-organization installation/sharing is implied. A later system catalog
needs a deliberate read/publish policy, not a nullable-owner shortcut.

## Templates, versions, and customization

Templates have a mutable label, description, and draft definition. Publishing
locks the template, validates the entire draft, assigns the next positive
integer version, and stores a canonical JSON snapshot with SHA-256. Versions
are immutable in both service/API and PostgreSQL UPDATE/DELETE enforcement.
Published templates/versions are retained; archive rather than hard delete.
PROTECT source relationships deliberately prevent destructive catalog deletion
while published provenance is retained, including organization removal.

Installation references one published version and copies its definitions into
customer-owned normalized rows in one control-plane transaction. Changing an
instance never writes to a template. Source version, instance UUID, and each
copied definition's source UUID are preserved for a future three-way upgrade
comparison (source snapshot, installed configuration, new version). There is
no automatic propagation or upgrade engine. Each installation gets new UUIDs;
source UUIDs are provenance, never cross-instance authorization identities.

Important rows have immutable UUID primary keys. Definition `key` is a strict
lowercase identifier, immutable after creation; `label` is mutable presentation.
References use UUIDs, not either string. Draft JSON definitions accept UUIDs
and generate missing UUIDs. Authors must retain returned UUIDs when revising a
draft to retain lineage; new UUIDs mean new definitions. Published version
JSON uses `schema_version: 1` and stores these logical definition identities.

## Minimal schema

Draft/snapshot shape:

```json
{"schema_version":1,"models":[{"id":"UUID","key":"item","label":"Item","fields":[{"id":"UUID","key":"name","label":"Name","data_type":"text","required":false}]}],"relationships":[]}
```

Each relationship has UUID, key, label, source_model UUID, target_model UUID,
kind `many_to_one`, and deletion policy `restrict` or `set_null`. The latter
means an optional future reference. No implicit cascading business-record
deletion is permitted. Relationships must remain within one definition or
instance; self-reference is allowed. Model and relationship keys are unique
within their own namespace; field keys within the model. UUIDs are unique
across one snapshot. Limits bound metadata (100 models, 100 fields/model,
500 relationships). Unknown properties and invalid identifiers are rejected.

Fields initially support text, integer, decimal, boolean, date, datetime.
Decimal runtime precision/scale and data validation beyond metadata require
the runtime phase; no SQL is generated here. Choice, file/image, email, URL,
and computed fields are deferred. Definition deletion and changing field
types after creation are deferred to a migration-aware runtime; Phase 1 can
add definitions, edit labels/required flags, and archive an instance.

## Storage decision

Control metadata stays in Django's control PostgreSQL, consistent with
ADR-0001. Future business records should use the existing validated relational
tenant database services and schema isolation, not new control-plane EAV.
This direction follows the real DDL/row/FK/index, import/export, authorization,
audit, and backup foundations already present. Physical table mapping is a
runtime decision and will use stable IDs, not mutable labels.

| Alternative | Assessment |
|---|---|
| Existing managed tenant tables | Real FK integrity, SQL query/reporting/index performance, existing backups and offline operation; requires explicit migrations and mapping from definition UUIDs |
| Generic JSON/EAV business records | Flexible shape but weaker typed/FK integrity, harder indexing/reporting and policy enforcement; duplicates existing data services |
| New generated datastore/schema engine | Repeats validated DDL and permission machinery, increasing security and migration risk |
| Hybrid | Chosen: normalized control metadata + immutable JSON template snapshots; relational tenant records later |

No physical schema or irreversible runtime storage mapping is created now.
Runtime implementation must specify transactions, migration rollback, record
permissions, auditing, and reporting before creating any business tables.

## Authorization and audit

Capabilities: `app_template.read`, `.manage`, `.publish`; `app_instance.read`,
`.manage`, `.schema.manage`. Existing organization administrators receive these
through the catalog. Other roles do not receive new authority automatically.
`has_permission` accepts exact `app_template` or `app_instance` ResourceGrants;
children inherit the instance scope. Active organization membership is always
required even with a grant. Lists filter to resources with read permission,
then paginate; they must not reveal a forbidden definition via serialization.
Fine-grained grant provisioning uses the existing shared authorization service
and operator tooling; the Sharing API/UI's resource-type catalog is not extended
in Phase 1. Organization administrators can use all foundation endpoints.
Creation requires organization-wide manage; installation additionally requires
read access to the selected same-organization template. No frontend-only gate.

Phase 1 APIs are human-session administration only: environment-scoped bearer
credentials must not acquire access to unbound new metadata. Service-account
principals are explicitly rejected; a future integration API needs an explicit
environment/resource binding contract, not an accidental bypass.

Significant create/update/publish/install/archive/definition mutations record
`app_template.*` or `app_instance.*` events through the existing audit service
inside their transaction. Audit stores IDs and operation names, not whole
definition payloads. Denied service capability checks emit denied events.
Database constraints enforce uniqueness; transaction locks serialize publication
and schema mutation. Direct SQL UPDATE cannot mutate published snapshots or
identity/ownership bindings; relationship boundary triggers reject cross-instance
links. SQL triggers use fixed schema/table names, never user SQL.

## API boundaries

All under `/api/v1/`, existing DRF authentication/errors and limit/offset pages:

- `organizations/{org}/app-templates/`: GET list, POST create draft.
- `app-templates/{id}/`: GET, PATCH label/description/draft/archive.
- `app-templates/{id}/versions/`: GET list, POST publish current draft.
- `app-template-versions/{id}/`: GET immutable snapshot.
- `projects/{id}/app-instances/`: GET list, POST install template_version + label.
- `app-instances/{id}/`: GET, PATCH label/archive.
- `app-instances/{id}/models/`: GET, POST.
- `app-models/{id}/`: GET, PATCH label.
- `app-models/{id}/fields/`: GET, POST.
- `app-fields/{id}/`: GET, PATCH label/required.
- `app-instances/{id}/relationships/`: GET, POST.
- `app-relationships/{id}/`: GET, PATCH label/deletion policy.

Clients cannot mass-assign owner, organization, source lineage, instance parent,
or timestamps. No DELETE, executable configuration, or arbitrary SQL endpoint.

## Backup, restore, and migration

Full control-plane pg_dump/pg_restore includes all new tables, immutable
snapshots, IDs, constraints, and triggers. This is the supported Phase 1 backup
path. Portable `.icp` does not yet include App Platform metadata: its manifest
explicitly declares exclusion and packages from organizations with definitions
carry an export warning. Restore continues to create only the supported scope;
it must not claim to reconstruct an application instance. Implementing portable
support later must extend the existing durable RestoreJob protocol, map all
source/instance/definition UUIDs, and test tenant isolation and replay. It must
not dispatch a separate uncoordinated installer during restore.

Migrations are additive only. Existing integrations, data/storage tables, and
restore identity are unchanged. Apply reviewed migrations and seed_permissions
on upgrade; old workers must be drained per the existing restore deployment
contract. Fresh and upgrade paths are tested on real PostgreSQL. Template
format versions permit future parsers to reject unsupported versions rather
than silently reinterpret definitions.

## Future compatibility and remaining scope

Runtime can map immutable definition IDs onto existing tenant DB resources;
Builder can edit through the same services; workflow/hierarchy metadata can
reference IDs and reuse capabilities/audit. Enterprise authorization must
extend the shared grant mechanism. Template upgrades need conflict detection
and migration plans; no automatic overwrite of customer configuration.
System templates, fine-grained field/record permissions, portable packages,
schema deletion/type conversion, and installation-request idempotency remain
future work. An install POST intentionally creates a new independent instance.
Existing health-check P2/external release work is unchanged.

## Phase 1 verification checkpoint

Implemented and verified 2026-09-08: 436 full backend/integration/security
tests pass, including 32 new foundation tests; real HTTPS session/CSRF smoke,
migration/backup/concurrency checks, Ruff, Mypy, and backend Docker build pass.
See [implementation evidence](implementation/APP_PLATFORM_PHASE1.md) for exact
commands, counts, limits, and the local Git baseline. This is readiness for
the next scoped runtime phase, not implementation of that phase.
