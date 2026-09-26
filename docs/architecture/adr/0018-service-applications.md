# ADR-0018 — Service applications: separately deployed apps on IntraForge storage, identity and audit

Status: accepted; being implemented for the separately developed Spare Parts application.
Date: 2026-09-27. Builds on ADR-0001 (control/data plane), ADR-0005 (schema-per-organization tenant data),
ADR-0008 (capabilities), ADR-0014/0015 (App Platform). No new datastore, identity provider or orchestration
platform: the service stores its data in the existing tenant PostgreSQL and object storage.

## Problem

A separately developed application (the Spare Parts application, repository `intraforge-spareparts-demo`) was
bundled next to IntraForge on `127.0.0.1:3000` with its **own** users, its **own** SQLite database and its **own**
files. Two logins, two stores, two audit trails, and a backup that did not include the application's data. The
owner's requirement is one system of record: IntraForge owns identity, data storage, files, audit, configuration,
the application registry, backup/restore and lifecycle.

The application publishes its integration contract (`docs/INTRAFORGE_INTEGRATION_CONTRACT.md` in its repository):
provider interfaces for identity, repositories, files, audit and configuration behind a composition root. Its
ground rule 1 is that one business operation (a sale: stock, reservation, document number, invoice, audit) commits
or rolls back **as a unit**.

Why not the generic record API (`docs/EXTERNAL_APP_API_CONTRACT.md`)? It is the right surface for external apps
that own no business rules, but one sale would become dozens of independent HTTP writes with no shared
transaction, which breaks ground rule 1. `docs/SPARE_PARTS_INTEGRATION_READINESS.md` assessed the generic surface
before the application had its own domain layer; this ADR does not change that document's conclusions for generic
integrations.

## Decision

A **service application** is a separately built and deployed service (its own container and code, not merged into
the IntraForge repository) that IntraForge registers, provisions, authenticates, audits, backs up and serves.

1. **Registry.** `service_apps.ServiceApp` records one installed instance: organization, project, `app_type`
   (`spare_parts`), display name (the configured shop name, never hard-coded), validated configuration,
   `enabled`, the provisioned schema and bucket, the reported version and health. A deployment slot (the
   service container that exists in this installation) can hold at most one instance.
2. **Data storage.** Installing the application provisions a dedicated schema in the tenant PostgreSQL
   database (ADR-0005), owned by a dedicated least-privilege login role that can reach nothing else. The
   service runs its own versioned migrations there and keeps full transactional semantics (writes serialized
   with a transaction-scoped advisory lock, reads on a repeatable-read snapshot). The schema is **not** a
   `TenantDatabase`: the visual database builder must never edit an application's tables behind its business
   rules. The existing tenant-database backup (`pg_dump` of the whole tenant database) includes it.
3. **Identity.** IntraForge is the only login. **Open** in IntraForge (session + CSRF, capability
   `spareparts.view`) mints an application session: a random token stored hashed, bound to the user, the
   instance and the user's Django session, set as an `HttpOnly; Secure; SameSite=Strict` cookie scoped to the
   application's path. The service resolves it on every request through an internal introspection endpoint
   authenticated with the deployment's service token. Logging out of IntraForge, disabling the user, removing
   their membership or capability, or disabling the application ends access on the next request. No identity
   ever travels in a query parameter, and the service never trusts a browser-supplied role.
4. **Capabilities.** New default-deny capabilities `spareparts.*` (catalogue, products, cost, inventory, sales,
   suppliers, purchasing, reports, audit, settings). The application's five roles are reproduced as IntraForge
   system roles; the mapping from capabilities to the application's own permission names lives in the service's
   identity provider, as its contract requires.
5. **Routing.** The service is published only through the IntraForge proxy, same origin, under
   `/apps/spare-parts/`. It has no host port. `/api/v1/internal/*` is refused at the proxy and reachable only on
   the internal Docker network.
6. **Files.** Files go to IntraForge object storage through the existing upload pipeline (size limits, optional
   malware scanning, SHA-256), into a bucket owned by the instance; the service keeps the file id and
   verifies the SHA-256 on every read.
7. **Audit.** The service writes each audit event in the same transaction as the business change (its contract's
   ground rule 1) and relays it to IntraForge's audit log (`application=<app>`), idempotently by event id,
   at least once. IntraForge audit semantics are unchanged.
8. **Configuration.** Shop identity and document settings are the instance's IntraForge configuration.
   Document number sequences stay in the application schema, because they must be atomic with the transaction
   that uses them.
9. **Removal.** An instance can be removed without touching IntraForge, other applications or unrelated data;
   removing its data requires an explicit confirmation.

## Consequences

- One authoritative store per instance. The standalone SQLite build remains for development and for the
  application's own tests; the one-off migration tool moves a standalone database into the platform schema.
- A service application is trusted code shipped with the installation (like the frontend), but it is confined:
  its database role reaches one schema, and its service token reaches only the internal endpoints of its
  own instance.
- Portable `.icp` exports do not include service-application schemas; full backups do.
