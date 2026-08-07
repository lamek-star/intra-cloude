# ADR-0011: Use Valkey Instead of Redis for the Celery Broker / Cache

Status: Accepted
Date: 2026-08-07

## Decision

Use Valkey (the Linux Foundation–governed, BSD-3-licensed, wire-compatible
fork of Redis) as the concrete implementation behind every place the master
prompt and ADR-0010 refer to "Redis" — Celery broker, cache, rate-limit
counters. The `REDIS_URL` environment variable name and `redis://` client
protocol are kept unchanged, since Valkey is wire-compatible and every
client library used (`redis-py`, Celery's Redis transport) works against
it without modification.

## Context

ADR-0010 adopted Celery + Redis per Section 3 of the master prompt. Section
27 of the master prompt requires checking that a dependency's actual
released version is currently supported before adopting it, and recording
materially important choices rather than blindly using whatever a prompt
or older doc names. In March 2024 (well before this Phase 1 implementation
date of August 2026), Redis Ltd. relicensed Redis 7.4+ under a dual
SSPL/RSALv2 scheme that the OSI does not recognize as open source. In
response, the Linux Foundation forked the last BSD-licensed release as
Valkey. As of this implementation date, Valkey is production-ready
(current stable line 9.x), is the default on major managed cache services,
and most Linux distributions have stopped packaging Redis at all. Redis
itself returned to an open license (AGPLv3) starting with Redis 8, but
AGPL's copyleft terms are a materially different obligation than the
permissive BSD terms Valkey offers.

## Alternatives Considered

1. **Redis (current, AGPLv3-licensed as of Redis 8+).** Now open source
   again, but AGPLv3 is a strong copyleft license; for a platform this
   prompt explicitly wants organizations to self-host and potentially
   extend/integrate with internal tooling, a permissive license removes a
   category of legal-review friction with no functional cost.
2. **Redis 7.2.x (last BSD release, no longer maintained).** Rejected —
   using an unmaintained version to dodge a licensing question violates
   the master prompt's "avoid unsupported/EOL releases" rule directly.
3. **(Chosen) Valkey**, BSD-3, actively maintained, wire-compatible, so it
   is a drop-in replacement requiring no application code changes — this
   is a deployment/infrastructure substitution, not an architectural one.

## Advantages

- Permissive BSD-3 license matches the self-hosted, vendor-independent
  spirit of the whole project (Section 1: "without depending on AWS,
  Azure, or Google Cloud" — the same reasoning applies to avoiding
  copyleft or source-available obligations on infrastructure components).
- Fully wire/API-compatible with Redis, so Celery's broker transport and
  `redis-py`/`valkey-py` client usage require zero code changes — this ADR
  changes an image tag and a doc, not application code.
- Actively developed, broad industry adoption and governance backing
  reduces long-term maintenance/EOL risk relative to pinning an old BSD
  Redis release.

## Disadvantages

- One more name for operators to know ("Valkey" vs the more widely
  recognized "Redis" brand) — mitigated by keeping the `REDIS_URL`
  variable name and documenting the substitution clearly here and in
  `docker-compose.yml`.
- Minor risk that some future Redis-only feature (e.g. a Redis Enterprise
  module) is unavailable — not a concern for this platform's usage
  (broker + basic cache + counters), which uses only baseline
  command-set functionality present in both.

## Security Considerations

- No change to the threat model in `docs/security/THREAT_MODEL.md` TB5 —
  Valkey is bound to the internal Docker network exactly as Redis would
  be, never exposed publicly.
- Licensing is a legal/compliance concern, not a security one, but is
  treated with the same "don't blindly inherit a choice, verify it"
  discipline this project applies to security decisions.

## Operational Considerations

- `docker-compose.yml` uses the official `valkey/valkey` image.
- Any future documentation or runbook referring to "the Redis service"
  should be understood to mean this Valkey deployment; new docs should
  say "Valkey" directly.

## Final Recommendation

Adopt Valkey 9.x as the concrete broker/cache implementation for all
phases from Phase 1 onward. This does not change ADR-0010's reasoning
about *why* a Redis-protocol broker was chosen — only *which* server
implements that protocol.
