# Scale qualification -- Spare Parts at a small shop's realistic size

Date: 2026-09-20. Status: **PASSED for Local Edition scale**, with one defect found and fixed (browser N+1) and
three observations that are deliberately not optimized. Logs: `scale-generate.log`, `scale-measure.log`,
`scale-http.log`, `scale-browser.log` / `scale-browser-after.log` (in the private qualification log folder).

## Environment

- Host: Intel Core i7-8700T (6 cores / 12 threads), 15.8 GB RAM (0.7-2.3 GB free while running -- the host was
  under memory pressure the whole time, so these are conservative numbers), SSD, Windows 11 Pro 10.0.26200.
- Docker Desktop 29.6.2, 12 CPUs / 7.6 GB assigned. Disposable stack `intraforge-local-qualification`:
  PostgreSQL 18.4 (control and tenant), Valkey 9, MinIO, gunicorn (3 workers), Caddy TLS proxy on 127.0.0.1:8444.
- Default PostgreSQL configuration (no tuning), production Django settings, the configured rate limits.

## Dataset (built by `scripts/qualification/scale/scale.py`, never through a browser)

| What | Count |
| --- | --- |
| Products (Part) | 5,000 |
| Part numbers | 10,000 (two per product: an OEM-style `12345-00017` and an aftermarket `AM 00017 OIL`) |
| Stock movements | 10,000 (5,000 receives, 5,000 sale movements) |
| Sales (order + 2 lines + 2 movements + invoice) | 2,500 |
| Customers / suppliers / warehouses | 500 / 50 / 4 |

Generated through the **same services the API uses** (`records.create_record`, `transactions.run`): validation,
composite constraints, audit, the operation journal and the quantity-ledger triggers all ran; nothing was inserted
by raw SQL. Verified afterwards straight from the database (`reconcile_scale.py`, `scale-reconcile.log`): drift `[]`,
5,001 balance rows totalling 630,527 on hand equal the sum of the 10,086 movements (the 10,000 generated plus 86 from
the measurement runs).
Generation took about 20 minutes (products 177 s, part numbers 305 s, receives 185 s, sales 510 s).

## Method

1. **In-process** (`scale.py measure`): the real DRF views, real permission checks and real PostgreSQL through
   `APIClient`, each endpoint warmed up twice then timed 15 times (25 for receive/sale); query counts are taken on
   both databases; throttling is bypassed **in that shell process only** (it measures endpoint cost; the deployed
   limits are untouched).
2. **Real HTTP** (`http_latency.py`): host -> Caddy (TLS) -> gunicorn -> PostgreSQL over one keep-alive
   connection with a real login session, obeying the real rate limit (12 timed calls per endpoint, 15 for writes).
   The probe dials 127.0.0.1: Python has no happy-eyeballs, so `localhost` cost about 2 s per new connection on
   this machine -- a client artefact (curl sees 0.2 s), found and removed from the probe, not an application delay.
3. **Browser** (`e2e/scale-browser-probe.spec.ts`): one login, then each screen is loaded and the requests, bytes
   and time to network-idle are recorded.
4. **Query plans**: `EXPLAIN (ANALYZE, BUFFERS)` of the statements each screen's request really runs.

## Results -- in-process (milliseconds)

| Endpoint | p50 | p95 | queries control / tenant | bytes |
| --- | ---: | ---: | ---: | ---: |
| product list, first page (50) | 24 | 29 | 12 / 3 | 18,549 |
| product list, deep page (offset 4950) | 24 | 36 | 12 / 3 | 18,542 |
| product search by name (`Oil Filter 025`) | 59 | 73 | 13 / 3 | 2,625 |
| part-number search, exact (`AM 04284 OIL`) | 79 | 99 | 12 / 2 | 319 |
| part-number search, normalized (`am 04284 oil`) | 83 | 104 | 12 / 2 | 319 |
| part-number search, no match | 77 | 83 | 12 / 2 | 45 |
| part numbers of one product | 19 | 30 | 11 / 2 | 586 |
| inventory list, first page (50) | 22 | 28 | 11 / 2 | 14,329 |
| stock lookup for one product | 18 | 20 | 11 / 2 | 330 |
| movement history of one product | 19 | 20 | 11 / 2 | 859 |
| recent movements, all products (25) | 20 | 30 | 11 / 2 | 10,274 |
| sales list, first page | 24 | 27 | 11 / 2 | 6,848 |
| invoice lookup by number | 36 | 45 | 12 / 2 | 362 |
| home dashboard: six counts | 121 | 206 | 67 / 13 | 319 |
| application schema (one request) | 28 | 50 | 6 / 0 | 20,589 |
| RECEIVE (1 movement, atomic transaction) | 38 | 51 | 24 / 12 | 504 |
| SALE (order + line + movement + invoice, atomic) | 154 | 195 | 81 / 42 | 1,685 |

## Results -- real HTTP through the proxy (milliseconds)

| Endpoint | p50 | p95 | max | bytes |
| --- | ---: | ---: | ---: | ---: |
| product list (50) | 36 | 48 | 53 | 18,549 |
| product search by name | 79 | 96 | 104 | 2,625 |
| part-number search, normalized | 103 | 124 | 141 | 319 |
| inventory list (50) | 30 | 38 | 92 | 14,329 |
| stock lookup, one product | 35 | 41 | 46 | 615 |
| movement history, one product | 32 | 38 | 40 | 10,237 |
| application schema | 48 | 71 | 130 | 20,589 |
| RECEIVE (1 movement) | 56 | 102 | 108 | 494 |
| SALE (order+line+movement+invoice) | 146 | 177 | 183 | 1,672 |

Every measured operation stays under 210 ms at p95, a receive is about 55 ms and a sale about 150 ms end to end.

## Browser: requests per screen (5,000 products loaded)

| Screen | requests | KB | settled (ms) | largest response (KB) |
| --- | ---: | ---: | ---: | ---: |
| home (six counts) | 13 | 29 | 1,356 | 20 |
| products, first page | 6 | 37 | 1,235 | 20 |
| products, search | 1 | 0.4 | 243 | 0.4 |
| part-number search (normalized) | 7 | 28 | 1,205 | 20 |
| **stock page** | **12** (was **36**) | 55 | 1,312 | 20 |
| sales list | 7 | 35 | 1,164 | 20 |
| new sale (500 customers load) | 7 | 121 | 914 | 92 |
| receive stock (50 suppliers load) | 7 | 38 | 947 | 20 |
| product picker search | 9 | 122 | 1,273 | 92 |

## Findings

**Fixed -- browser N+1 (material).** The Stock page made 36 requests: the table put a product and a warehouse
name next to each row's ids with one `GET /records/<id>/` per distinct id (`useNames`). Besides latency, each page
spent a tenth of the 300/minute per-user rate limit -- the same class of defect as the schema fan-out found by the
accessibility run. Fix: the record list accepts `?ids=a,b,c` (validated UUIDs, at most 100, the same permission
check and tenant as any list) and `useNames` names a whole page with one request. Stock page 36 -> 12 requests.
Tests: 8 backend (exact records, unknown ids, constant query count, malformed/too many/`id`+`ids` -> 400,
combines with search/paging, no read access -> 403 with no count, other model -> 403, another organization -> nothing)
and 4 frontend (one request per page, repeats and the 100 cap, no re-request on re-render, refusal -> "(unavailable)").

**No N+1 in the API.** The control-database query count per request is constant (11-13) and identical at 40 and
5,000 products; it is per-request permission/model resolution, not per-row. A sale runs 81 control + 42 tenant
queries for four operations (about 20 per operation): it grows with the number of operations in a transaction,
not with the data, and costs ~150 ms.

**Query plans.** Stock lookup uses the composite index (`Index Scan`, 4 buffers). Name and part-number search are
a `Seq Scan` over 5,000/10,000 rows with `ILIKE` plus the normalization expression (about 50 and 80 ms): a b-tree
cannot serve a contains-match on a transformed value, and this is the cost the earlier 10,001-row check
(76-134 ms) predicted. No expression index is added -- it would only matter at sizes this edition does not target.

**Observations (not fixed, deliberately -- no hypothetical Enterprise-scale optimization):**
1. Relationship (foreign-key) columns have no index except where a composite unique constraint provides one.
   "Movement history of one product" therefore scans the movement table (10,000 rows, 139 buffer hits; the request
   takes 18.6 ms p50, indistinguishable from the indexed stock lookup at 18.5 ms). Harmless here; worth an index on relationship columns at provisioning before movements reach
   hundreds of thousands.
2. `__intraforge_operations` (the durable operation journal) is the largest table: 35,548 rows, 39 MB for a
   data set whose largest business table is 1.8 MB (~1.1 KB per mutation, ~1 GB per million). It is what makes
   audit/webhook delivery crash-safe, but nothing prunes published rows yet.
3. The customer pick list on "New sale" loads every customer (a 92 KB response for 500; the loader stops at 5,000)
   into a plain `<select>`. Fine for a small shop; a shop with thousands of customers needs a searchable picker,
   as products already have.

**Not measured:** memory of the browser and of the Python workers during the run (host free memory was only
sampled at the start of heavy steps: 2.0-2.3 GB, 0.7 GB at the lowest; no run was killed); concurrent users beyond the existing concurrent-sales test.

## Re-measurement under business-operation authority (2026-09-20)

Sell and receive became server-built controlled operations (ADR-0017), so the scale scripts now measure the
customer-facing operations. Same dataset (it survived two destructive restores; 5,000 products, 10,000 part numbers,
10,310 movements), same host and method.

| Operation | in-process p50 / p95 (ms) | queries control / tenant | through Caddy p50 / p95 (ms) |
| --- | ---: | ---: | ---: |
| Receive (controlled) | 64 / 122 | 32 / 12 | 73 / 84 |
| Sale, 1 line (controlled) | 205 / 241 | 107 / 42 | 203 / 232 |
| Sale, 5 lines (controlled) | - | - | 471 / 525 |

* Reads are unchanged (product list 29 ms, stock lookup 21 ms, movement history 22 ms in-process; normalized
  part-number search 96 ms, p95 192 ms).
* The authority check runs for every movement and adds about **35%** to a sale (queries 24 -> 32 for a receive, 81 -> 107
  for a one-line sale). Cost grows roughly **65 ms per extra line**: a typical counter sale (1-5 lines) is 0.2-0.5 s, a
  50-line sale would be about 3 s. Not material for a small shop; if it ever matters, the per-movement re-check can be
  replaced by the single check at the start of the operation.
* Two isolated ~2 s responses (one receive, one movement-history read) appeared in roughly 100 requests through the
  proxy on separate runs. They do not move p95 and are **unexplained**; they are recorded so a pilot that sees an
  occasional slow click can compare.
* The probe tops up stock before measuring sales: repeated measurement sales drained the part and the ledger
  (correctly) refused the last movement.
