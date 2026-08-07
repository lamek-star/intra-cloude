# ADR-0010: Asynchronous Job Processing — Celery + Redis

Status: Accepted
Date: 2026-08-07

## Decision

Use Celery, backed by Redis as broker, for all asynchronous/background
work: CSV import bulk processing, backups, malware-scan hooks, thumbnail
generation, and scheduled jobs (Celery Beat). Redis is also used as a
general-purpose cache and rate-limiting store, but nothing durable is
stored in Redis exclusively — it is treated as rebuildable.

## Context

Section 3 specifies Celery/Redis. Section 11 requires large CSV imports to
run asynchronously and never load multi-gigabyte files entirely into
memory; Section 19/20 require backup automation and health checks that fit
naturally into a scheduled-job model.

## Alternatives Considered

1. Synchronous processing with request-time streaming for imports — 
   violates Section 11's async requirement and risks request timeouts on
   large files.
2. A different queue system (RQ, Dramatiq, cloud-managed queue) — Celery
   is explicitly named in Section 3 and has the most mature ecosystem for
   the retry/chunking/scheduling patterns this platform needs.
3. (Chosen) Celery + Redis, with chunked/streaming task design for large
   imports (process the CSV in bounded-size batches, track progress in the
   `ImportJob` row, not in task memory).

## Advantages

- Mature retry, rate-limiting, and scheduling (Beat) support covers CSV
  import, backup automation, and future recurring health/quota jobs with
  one system.
- Redis as broker is already needed for caching/rate-limiting, so this
  doesn't add a fully separate piece of infrastructure.
- Chunked task design (a task processes N rows, re-enqueues itself or a
  continuation task for the next chunk) keeps memory bounded regardless of
  file size, satisfying Section 11 directly.

## Disadvantages

- Celery has a real operational surface (worker concurrency tuning, task
  visibility, dead-letter handling) that must be monitored (Section 20).
- Redis being non-durable by design means in-flight task state must be
  reconstructable from durable state (the `ImportJob`/`AuditEvent` rows in
  Postgres), not solely trusted from the queue — task design must treat
  Redis as a dispatch mechanism, not a source of truth.

## Security Considerations

- Redis is never exposed outside the internal Docker network (Section 17
  explicitly lists internal Celery interfaces as never-expose).
- Task payloads reference resource IDs and re-check authorization at
  execution time (THREAT_MODEL.md TB5) rather than trusting the enqueuing
  request's authorization context to still be valid/unforged.

## Operational Considerations

- Worker and Beat run as separate Compose services from the main API
  process so import/backup load doesn't starve request handling.
- Queue depth and task failure rate are tracked as health/observability
  metrics (Section 20, Phase 11).

## Final Recommendation

Adopt Celery + Redis as specified, with a chunked-processing convention
established in Phase 5 (CSV import) that later async features (backups,
scans) follow rather than each inventing its own batching approach.
