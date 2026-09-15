# ADR-0014: App Platform definition foundation

Status: accepted for Phase 1 metadata scope, 2026-09-08.

## Context

The authorized App Platform foundation must coexist with existing integration
Applications, capability-based access, separate control/tenant PostgreSQL,
and the durable portable restore protocol. Reusing the Application model
would conflate integration credentials with business application ownership.

## Decision

Use a separate `app_platform` bounded app. Organization-owned AppTemplates
publish immutable JSON AppTemplateVersions; project-owned AppInstances copy
definitions into independent normalized control-plane rows. UUID identities
and source UUID lineage survive display-label changes. PostgreSQL constraints
and fixed triggers enforce snapshot immutability and ownership/reference
boundaries in addition to service checks.

Extend the existing capability catalog with `app_template.read`, `.manage`,
`.publish`, `app_instance.read`, `.manage`, `.schema.manage`; use exact
template/instance ResourceGrants and inherited instance scope for children.
Human-session administration only in Phase 1 avoids inventing an environment
isolation exception for existing integration credentials.

Future business records should reuse validated relational tenant services.
Phase 1 creates no physical record tables or new datastore. System templates,
runtime migrations, upgrades, and builder behavior remain outside this ADR.
Full control-plane backups cover metadata. Portable `.icp` excludes it with
explicit warnings until its mapping and replay tests are implemented.

## Consequences

Published provenance is retained and protected from deletion. Version/draft
and instance configuration cannot silently affect one another. Customers can
customize labels and add definitions without introducing industry code.
Runtime will need an explicit UUID-to-physical-resource mapping and migration
plan. Service-account access needs a deliberate resource/environment contract.
See [the architecture record](../../APP_PLATFORM_ARCHITECTURE.md) for alternatives,
API format, scope limits, ownership, and backup behavior.
