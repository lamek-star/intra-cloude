# IntraForge Local Edition v1.0

IntraForge is a private local business cloud for business records and files
on infrastructure the organization controls. Local Edition is a productization
target for the existing platform, not a separate codebase or feature tier.

**Qualification in progress.** Installed features, verified workflows, and
commercial release qualification are different claims. The active evidence
is in [Current State](implementation/CURRENT_STATE.md); the full acceptance
brief is [Local Edition mandate](implementation/LOCAL_EDITION_MANDATE.md).

## Architecture and ownership

The browser connects to a local Caddy proxy. Next.js supplies the interface;
Django enforces authentication and authorization. Control PostgreSQL stores
users, permissions and application definitions; tenant PostgreSQL stores
business records in managed schemas. S3-compatible storage holds files.
Valkey and Celery support background work. Windows uses the existing WSL2
appliance and Control Center. Core operation requires no public-cloud account.

Build-time dependency and font downloads are distinct from runtime operation.
Release bundles must contain the images and rootfs before offline installation.
Optional external integrations require their own connectivity. Internet-facing
deployment is opt-in; this Local Edition qualification does not enable it.

## Operator and user documentation

| Area | Existing guide / current boundary |
|---|---|
| Installation, first launch, prerequisites | [Local deployment](deployment/LOCAL_DEPLOYMENT.md), [installer](../installer/README.md); Windows lifecycle unqualified |
| Organization, users, applications, files, audit | [User guide](guide/USER_GUIDE.md); current business-journey qualification in progress |
| Control Center, start/stop, Windows recovery | [Windows qualification matrix](deployment/WINDOWS_QUALIFICATION_MATRIX.md); implemented UI, external qualification pending |
| App Builder, templates and upgrades | [App Platform roadmap](implementation/APP_PLATFORM_ROADMAP.md); all ten development phases implemented |
| Spare Parts, purchasing, sales, warehouses | [Reference application](implementation/APP_PLATFORM_PHASE4.md); record models exist; atomic stock operations remain an acceptance gap at entry |
| Part numbers, external catalogue provenance | [Catalogue storage](CATALOGUE_STORAGE.md), [external API](EXTERNAL_APP_API_CONTRACT.md); external catalogue is separate from company records |
| Permission scopes and organizational units | [Permissions](security/PERMISSIONS.md), [Phase 7](implementation/APP_PLATFORM_PHASE7.md); exact-unit scope, not implied descendant access |
| Attachments and file authorization | [Threat model](security/THREAT_MODEL.md); both record and storage authority are required |
| Backup and restore | [Backup procedure](operations/BACKUP_RESTORE.md), [runtime recovery](operations/RUNTIME_PROVISIONING.md) |
| Offline operation and LAN | [Local deployment](deployment/LOCAL_DEPLOYMENT.md); isolated-network and second-machine evidence must be recorded separately |
| Upgrade, uninstall, troubleshooting | [Upgrade guide](deployment/UPGRADE_GUIDE.md), [installer](../installer/README.md) |
| Hardware and capacity | [Hardware guide](deployment/HARDWARE_GUIDE.md); no new scale claim without measurements |
| Security and dependencies | [Threat model](security/THREAT_MODEL.md), [third-party notices](legal/THIRD_PARTY_NOTICES.md), [SBOM](operations/SBOM.md) |
| Investor demonstration | [Demo script](INVESTOR_DEMO.md); rehearsal/qualification pending |

## Recovering the whole business

A portable `.icp` export is **not** a complete installed-business backup.
It excludes App Platform definitions, workflow/customization metadata,
credentials, sharing and other scope explicitly listed in its manifest.
Included runtime tables alone do not recreate installed applications.

Full recovery requires a matched set taken while application writes and
background mutations are stopped: control database, tenant database, file
objects and configuration/secrets. Preserve the encryption recovery key
separately. Copy the set off the server. Restore into a disposable environment
and verify identities, relationships, quantities, permissions and file hashes
before relying on the procedure. Independent scheduled backups do not by
themselves prove a consistent whole-appliance recovery point.

## Future Enterprise investment

Local Edition preserves the existing permissions, organization hierarchy,
template and integration foundations. Future investment may address high
availability, fleet management, managed updates, enterprise identity,
advanced recovery, observability and larger application ecosystems. These
are future areas, not claims that Local Edition already supplies them.

Windows ISO/elevated clean-VM testing, real signing credentials and physical
second-machine LAN evidence are separate external requirements. The WSL2
prerequisite policy remains a product decision; the current path assumes
IT has prepared WSL2. No unattended host changes are implied by this guide.
