# Catalogue storage (`catalogue_storage`)

A minimal, shared **reference catalogue** of OEM parts and the diagrams
they're called out on — built for the Harmoney Spare Parts integration's
"resolve a part number to a diagram + hotspot" lookup, and deliberately
nothing more. See `catalogue_storage/models.py`'s own module docstring
for the exact scope.

## Simplify the Toyota/OEM integration

The obvious design for this would clone a Toyota-style Electronic Parts
Catalogue (EPC): Make → Model → Generation → Variant → fitment matrix →
diagram → part. That's a large, slow-changing reference dataset this
project has no need to own or keep in sync. The decision here is to keep
only the three things the spare-parts application's own lookup actually
needs:

- **`OEMPart`** — what part is this (manufacturer, part number in both
  official-display and normalized-for-search form, description).
- **`Diagram`** — one image, shared by every part drawn on it.
- **`DiagramPart`** — the join: which callout/hotspot on which diagram
  points at which part.

No vehicle/fitment hierarchy, no selling price, no stock level. A part's
vehicle applicability (`OEMPart.applicability`/`fitment_notes`) is kept
only as the free-text string a source provider states it as — never
parsed into a structured Make/Model matrix, because this app doesn't
need to answer fitment questions, only "what is this part and where is
it on the diagram." If a real fitment matrix is ever needed, that's a
*reference* concept the spare-parts application owns, not something to
retrofit here.

## Access model

This catalogue is deliberately **not** organization-owned data — every
other tenant-owned resource type in this platform (buckets, databases,
App Platform records) carries an explicit `organization` and is gated by
a capability string through `permissions.services.has_permission`
(ADR-0008). A shared OEM parts/diagrams table has no natural organization
owner to check a capability against, so it uses a different, narrower
gate instead:

- **Read** (`GET /api/v1/catalogue/oem-parts/`,
  `GET /api/v1/catalogue/oem-parts/{id}/`,
  `GET /api/v1/catalogue/diagrams/{id}/image/`): any authenticated
  session or bearer credential (`IsAuthenticated`). This is reference
  data, not sensitive, and every registered user on the deployment is a
  legitimate reader.
- **Write** (`POST /api/v1/catalogue/oem-parts/import/`): gated on
  authentication *shape*, not a capability — only a request authenticated
  via an `applications.ApplicationCredential` bearer token (`request.auth`
  is that credential, not `None`/a Django session) may write. A plain
  human session is refused with 403, even for an otherwise fully
  legitimate, active user — see `OEMPartImportView`'s own docstring and
  `environments.services.check_environment_scope` for the identical
  `isinstance(request.auth, ApplicationCredential)` pattern used
  elsewhere in this codebase for the same reason (a capability model
  doesn't apply, so the check falls back to "was this call made by a
  deliberately issued machine credential at all"). Every write emits an
  `AuditEvent` (`catalogue.oem_part.import`, `DENIED` on the
  session-authenticated-refusal path too) — see
  `catalogue_storage/tests/test_catalogue.py`'s `ImportEndpointTests`.

This is intentionally *not* scoped further to the one specific seeded
"Harmoney Spare Parts — Catalogue Storage" Application — any bearer
credential an operator has deliberately issued (through the existing
`applications` admin API, itself capability-gated) may write. Narrowing
further would mean hardcoding one Application's identity into this app,
which buys no real security margin over "an operator explicitly issued
this machine a credential."

## Licensing

`Diagram.license_status` starts, and stays, `EXTERNAL_REFERENCE_ONLY`
unless a real redistribution permission has been separately confirmed
for that image's provider — never inferred, never defaulted to
permissive. In that state only `source_image_url` (the provider's own
hosted copy) and provenance metadata are kept; no image bytes are ever
read or stored, and `DiagramImageView` 404s.

Only `catalogue_storage.services.attach_local_image` may promote a
`Diagram` to `LOCALLY_STORED`, and only after the caller has already
written real bytes to this platform's own object storage
(`storage.services.upload_file`) — `attach_local_image` itself only
records the resulting `FileObject` on the `Diagram` row, it never
uploads anything or decides permission on its own.

`import_oem_catalogue`'s CSV path mirrors this at the tool level:
image bytes are only ever read from `--images-dir` when
`--license-confirmed` is explicitly passed. Without it, every row still
imports (part/diagram/link metadata, plus `source_image_url` if
`--source-base-url` is given) — `license_status` simply stays
`EXTERNAL_REFERENCE_ONLY`. `OEMPartImportView` (the live API path) never
accepts image bytes at all, by design — it can't be used to smuggle
local storage around the CSV importer's own gate.

## Image highlighting

`DiagramPart.x`/`y`/`width`/`height` are a hotspot rectangle in the
diagram image's own pixel coordinate space, in the exact form a source
provider supplies one. Left `null` when the provider (or a manually
entered row) doesn't give one — never fabricated, estimated, or
defaulted to a computed layout. A caller rendering these must treat a
null hotspot as "no highlight available for this callout," not as
`(0, 0, 0, 0)`.

## First end-to-end proof

The sample loaded by
`catalogue_storage/migrations/0002_seed_spare_parts_catalogue.py` is a
real record, not synthetic fixture data — read live from the Toyota EPC
aggregator during this feature's development:

- Part: `15690-65010`, Toyota, "VALVE ASSY, OIL COOLER RELIEF"
- Diagram: provider `toyota-epc`, diagram `MAB896` (catalog `EU/A2`,
  section 1503 "ENGINE OIL COOLER")
- Callout `15690`, hotspot rect `{536,672}–{602,692}`
- `license_status`: `EXTERNAL_REFERENCE_ONLY` (unchanged — toyota-epc
  redistribution permission remains unverified, same as every other
  Toyota-EPC-related decision in this project;
  `docs/INTRAFORGE_OIDC_PROVIDER.md`'s own seed migration makes the same
  call for the unrelated reason of not needing it)

This is the fixture `catalogue_storage/tests/test_catalogue.py`'s
`SearchAPITests` exercises directly, and what a fresh
`docker compose up` has searchable with no manual step.

## Bootstrap identity

The same seed migration also registers a dedicated
`applications.Application` ("Harmoney Spare Parts — Catalogue Storage")
and issues it a bearer credential (printed once, to
`docker compose logs`, at migration time) — this app's own bootstrap
integration identity, distinct from `oauth_provider`'s end-user SSO
client (that's *human* sign-in; this is *server-to-server* catalogue
access — see `docs/INTRAFORGE_OIDC_PROVIDER.md` "Why a new app, not an
extension of `applications`" for the same distinction applied there). If
the printed secret is lost, `python manage.py rotate_catalogue_credential`
issues a fresh one for that same Application rather than requiring the
migration to be re-run.

## Search

`GET /api/v1/catalogue/oem-parts/?q=<anything>` — exact match on the
normalized part number first (`normalize_part_number` strips
spaces/dashes and uppercases, so `15690-65010`, `1569065010`, and
`15690 65010` are all the same lookup key — kept in lockstep with the
spare-parts application's own identical client-side rule on purpose);
falls back to a case-insensitive substring match on `description` if no
part number matched. Returns one best match, never a result list — this
integration's own scope is a single quick lookup, not a search UI.

## Open items

- No pagination/bulk endpoints — one part per import call, one result
  per search call, matching the "quick lookup" scope this app was built
  for. A bulk import path for a real catalogue-scale sync is tracked as
  a future need in `docs/SPARE_PARTS_INTEGRATION_READINESS.md` Section 7,
  not built here.
- No admin UI for browsing/editing the catalogue directly — only the CSV
  importer, the seed migration, and the read/import API exist today.
