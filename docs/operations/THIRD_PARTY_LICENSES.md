# Third-party licences and assets (release review)

A working review for pilot and release readiness -- **not legal advice**. Counsel should confirm the items marked
*decision needed* before any commercial distribution. Facts were gathered on 2026-09-20 from the actual installed
sets, not from memory.

## Software inside the product

### Python (production runtime image, 40 packages)

| Licence family | Packages |
| --- | --- |
| BSD | 15 |
| MIT | 15 |
| Apache-2.0 | 7 |
| **LGPL** | 3: `psycopg`, `psycopg-binary` (the PostgreSQL driver; its wheel bundles libpq), `clamd` |
| GPL / AGPL | **none** |

LGPL used **unmodified as a library** (installed with pip, replaceable by the customer) is compatible with shipping
the product; the obligations are to include the licence text and notices and not to prevent replacing the library.
That belongs in the release notices (open item: see the list at the end).

### Node (production dependency tree, 26 packages)

MIT 11, Apache-2.0 7, ISC 3, BSD-3-Clause 1, 0BSD 1, CC-BY-4.0 1 (`caniuse-lite`, browser-support *data*: attribution),
plus IntraForge's own private package. **No copyleft in the shipped image.** The optional native image library
(`sharp` and its LGPL libvips binaries) is **excluded from the frontend image** (verified: no `sharp`, no `@img` in
the rebuilt image), which removes the only LGPL Node component and a native attack surface.

### Infrastructure shipped as images or bundled into the appliance

| Component | Licence | Note |
| --- | --- | --- |
| PostgreSQL 18 | PostgreSQL Licence (permissive) | |
| Valkey 9 | BSD-3-Clause | Chosen over Redis 8 (AGPLv3) deliberately: [ADR-0011](../architecture/adr/0011-valkey-over-redis.md) |
| Caddy 2 | Apache-2.0 | |
| **MinIO** (object storage) | **GNU AGPL-3.0** (the upstream server) | **Decision needed.** Shipping an unmodified MinIO to a customer is allowed, but AGPL attaches conveyance obligations (the licence and an offer of the corresponding source) and, if MinIO is ever modified and offered as a network service, source-disclosure duties. The storage layer is an abstraction ([ADR-0004](../architecture/adr/0004-object-storage-abstraction.md)), so a permissively licensed S3-compatible store can replace it. Also: the compose files use `minio/minio:latest`, which is **not pinned** -- pin a release before shipping. |
| Docker Engine + Compose plugin (baked into the WSL rootfs, [ADR-0013](../architecture/adr/0013-docker-engine-bundled-in-wsl2-rootfs.md)) | Apache-2.0 | |
| Ubuntu WSL rootfs | Mixed, including GPL system packages | Distribution obligations (licence texts, source offer) apply to what is shipped. Not reviewed. |
| ClamAV (optional malware scanning) | GPL-2.0 | Run as a separate daemon over a socket, not linked into the application; optional. |

**Not covered by this review:** the licences of the OS packages inside every base image, the .NET runtime and the
WiX toolset used by the Windows installer and Control Center, and any font files. A complete appliance inventory does
not exist (see [SBOM.md](SBOM.md): the SBOM covers the backend image, the frontend image and the frontend source only).

## Assets

* **Brand assets** (`apps/frontend/public/brand`): the IntraForge logo lock-ups and icons. They are the project's own
  brand identity (DESIGN.md). Provenance of the source artwork should be confirmed by the owner before release.
* **Product images:** none are shipped. Customer images are uploaded by the customer and stored in their own object
  storage.
* **Catalogue and exploded-diagram (EPC) artwork:** **none is included.** No third-party EPC, parts-catalogue or OEM
  artwork is copied into this repository or the product. Reference websites that show such material were used only as
  examples of the interaction; they are reference, not a source, and nothing may be copied from them without an
  explicit licence or feed. The product distinguishes a *product image gallery* (the customer's own photographs)
  from an *exploded-diagram viewer* (not built, not offered) and does not present generic artwork as an EPC diagram.
* **Icons:** `lucide-react` (ISC).

## Open items before a commercial release

1. Counsel review of MinIO (AGPL-3.0) and a decision: comply and pin, or replace behind the storage abstraction.
2. Refresh `legal/THIRD_PARTY_NOTICES.md` (the 2026-09-06 review; it still lists the LGPL `sharp`, which the frontend
   image no longer ships) and **ship it with the product and the installer** (LGPL texts for `psycopg`/`clamd`, CC-BY
   attribution for `caniuse-lite`, Apache-2.0 notices, MinIO's AGPL terms).
3. Pin every infrastructure image to a digest.
4. A complete appliance inventory (the WSL rootfs and the installer's toolchain).

## Pilot kit pin (2026-09-21)

The own-shop pilot kit pins MinIO to `minio/minio:RELEASE.2025-09-07T16-13-09Z` (the exact release the qualification ran on; recorded with its image id in the kit's `OFFLINE_MANIFEST`). This is for the owner's own internal pilot only. The AGPL-3.0 distribution decision (comply and pin, or replace behind the storage abstraction) remains **open** and blocks any commercial distribution.
