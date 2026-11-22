# Chapter 9 — Known limits, open items and how to scale — How to scale

Topic for: software engineers. Source: IntraForge Engineering Handbook, Chapter 9 — Known limits, open items and how to scale.

IntraForge was designed for one shop on one PC, but its boundaries were chosen so it can grow without a rewrite.

| Need | What to do | What stays the same |
|---|---|---|
| More users in one shop | Raise gunicorn workers and Celery concurrency; give PostgreSQL more memory | Everything else — throttles already share Valkey |
| A bigger server | Move the same compose file to a Linux server (ADR-0012's customer-managed host) | The kit's images and data volumes |
| Several shops, one company | One installation, one organization with **org units** (branches); unit-scoped grants limit each branch's staff | Capabilities, audit, the ledger |
| Several companies | Separate organizations on one installation — schema-per-organization isolation already holds | IDOR tests for every resource |
| Heavy files | Point object storage at a larger S3-compatible store (ADR-0004); files never pass through Django's database | The `storage` service API |
| High availability | Managed PostgreSQL with replicas, several backend containers behind the proxy, Valkey with persistence — then consider an orchestrator (needs a new ADR; ADR-0006 defers Kubernetes until a concrete need) | The service layer and data model |
| Other programs connecting | Applications with scoped credentials, Environments, webhooks, OAuth sign-in (`docs/EXTERNAL_APP_API_CONTRACT.md`) | Default deny |
| A new business type | A new App Platform template (Chapter 5.1) — data, not code | The generic runtime, ledger, permissions |

**Do not** scale by weakening a rule: no shared tables filtered only by `organization_id`, no stock arithmetic outside
PostgreSQL, no role-name checks, no internet dependency for normal work, no loosened rate limits.
