# Chapter 1 — Architecture — Architecture decision records

Topic for: software engineers. Source: IntraForge Engineering Handbook, Chapter 1 — Architecture.

| ADR | Decision |
|---|---|
| 0001 | Control plane (Django) separate from data plane (PostgreSQL + object storage) |
| 0002 | Django + DRF in small bounded apps |
| 0003 | Django-native authentication first, OIDC-ready |
| 0004 | S3-compatible object storage, MinIO locally |
| 0005 | Schema-per-organization tenant isolation |
| 0006 | Docker Compose first, Kubernetes deferred |
| 0007 | TypeScript + React, Next.js |
| 0008 | Capability-based authorization |
| 0009 | External databases: connected (read-only) vs imported modes |
| 0010 / 0011 | Celery for background jobs; Valkey instead of Redis (licence) |
| 0012 / 0013 | Windows deployment (WSL2 appliance route) and Docker Engine in the rootfs — the earlier MSI route |
| 0014 / 0015 | App Platform: immutable template versions, independent instances; resumable runtime provisioning |
| 0016 | Tenant operation journal and quantity ledgers (the database decides stock) |
| 0017 | Business-operation authority over stock (sell / receive / adjust / transfer) |
| 0018 | Service applications on IntraForge storage, identity and audit |
| 0019 | Passkeys (WebAuthn) |
| 0021 | Shop names on the LAN (CoreDNS) |
| 0022 | Movie Shop and the media agent |
| 0023 | Licensing: trial, serial number, activation code |
| 0024 | MySQL and SQL Server connectors |

Hosted websites and the app runner are described in code as "ADR-0019" and "ADR-0020" decisions, but no ADR file with
those decisions exists (0019 is passkeys). See Chapter 9.
