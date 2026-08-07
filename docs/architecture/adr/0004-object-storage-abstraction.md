# ADR-0004: S3-Compatible Object Storage Abstraction, MinIO Locally

Status: Accepted
Date: 2026-08-07

## Decision

Access all blob storage through a provider-agnostic storage interface
(e.g. a thin abstraction over `boto3`/S3 API semantics: put, get, presign,
delete, list, multipart upload) implemented against MinIO for local/
self-hosted deployment, with AWS S3 or another S3-compatible provider as
drop-in alternatives later via configuration, not code changes.

## Context

Section 3 and Section 8 require an S3-compatible abstraction that avoids
tight coupling to one provider, supporting local storage now and AWS S3 or
another provider later.

## Alternatives Considered

1. Direct filesystem storage on the Django host, no object-storage
   abstraction.
2. Hard dependency on AWS S3 specifically (SDK calls scattered through the
   codebase).
3. (Chosen) A storage interface implemented once against the S3 API
   (which MinIO, AWS S3, and other compatible providers all speak), with
   provider selection purely a matter of endpoint/credential configuration.

## Advantages

- One code path for local and cloud storage; local-first today, cloud-
  capable later without redesign, directly satisfying Section 8/Section 1.
- MinIO is self-hostable, S3-API-compatible, and works well with the HDD-
  pool/ZFS storage assumptions in Section 4.
- Presigned URLs, multipart upload, and versioning are natively supported
  by the S3 API, avoiding hand-rolled equivalents.

## Disadvantages

- An additional service to operate locally (MinIO) versus "just write to
  disk."
- S3 API semantics (eventual consistency edge cases on some providers,
  multipart upload complexity) leak into the abstraction to some degree.

## Security Considerations

- Object keys are server-generated (UUID-based), never derived from
  user-supplied filenames — prevents path traversal and enumeration.
- Buckets are private by default; presigned URLs are short-lived and
  scoped to a single object/operation.
- MinIO's admin console is never exposed outside the internal network
  (Section 17).

## Operational Considerations

- MinIO data directory is a bind mount onto the HDD pool per
  LOCAL_DEPLOYMENT.md; backup via `mc mirror` or server-side replication
  per BACKUP_RESTORE.md.
- Health checks integrate into the same `/readyz` pattern as other
  dependencies.

## Final Recommendation

Build the storage abstraction first, implement it against MinIO for Phase
3, and treat "swap in AWS S3" as a configuration-only exercise validated by
at least one integration test run against both backends where feasible.
