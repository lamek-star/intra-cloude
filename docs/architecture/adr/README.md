# Architecture Decision Records

| ADR | Title | Status |
|---|---|---|
| [0001](0001-control-plane-data-plane-separation.md) | Separate control plane (Django) from data plane (PostgreSQL + object storage) | Accepted |
| [0002](0002-backend-framework-django-drf.md) | Backend framework — Django + DRF, modular apps | Accepted |
| [0003](0003-authentication-strategy.md) | Authentication strategy — Django-native first, OIDC-ready interface | Accepted |
| [0004](0004-object-storage-abstraction.md) | S3-compatible object storage abstraction, MinIO locally | Accepted |
| [0005](0005-tenant-database-isolation-strategy.md) | Tenant database isolation — schema-per-organization | Accepted |
| [0006](0006-deployment-orchestration-docker-compose-first.md) | Deployment orchestration — Docker Compose first, Kubernetes deferred | Accepted |
| [0007](0007-frontend-framework-nextjs-react.md) | Frontend framework — TypeScript + React, Next.js where appropriate | Accepted |
| [0008](0008-permission-model-capability-based.md) | Capability/permission-based authorization, not hard-coded roles | Accepted |
| [0009](0009-external-database-connector-modes.md) | External database integration — distinct connected vs imported modes | Accepted |
| [0010](0010-async-job-processing-celery-redis.md) | Asynchronous job processing — Celery + Redis | Accepted |

New architecturally significant decisions get a new numbered ADR here
rather than silently changing behavior described in an existing one.
