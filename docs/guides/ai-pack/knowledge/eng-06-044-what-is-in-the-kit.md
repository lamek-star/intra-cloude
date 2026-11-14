# Chapter 6 — The shop kit: build, install, upgrade, operate — What is in the kit

Topic for: software engineers. Source: IntraForge Engineering Handbook, Chapter 6 — The shop kit: build, install, upgrade, operate.

| Part | Source | Notes |
|---|---|---|
| Container images (saved as `.tar`) | built from committed source | backend, frontend, Pay, Spare Parts, Pharmacy + pinned postgres, valkey, MinIO, caddy, coredns |
| `docker-compose.yml` | `template/docker-compose.yml` | `@TAG@`/`@MINIO_TAG@` filled in at build time; `pull_policy: never` everywhere |
| PowerShell scripts | `template/*.ps1` | install, start, stop, status, backup, restore, upgrade, uninstall, network |
| Control Center | `control-center/*.cs` | the shop owner's Windows window (status, start/stop, backups, restore, shop network, diagnostics) |
| Media agent | `media-agent/MediaAgent.cs` | the Movie Shop's file copier |
| Setup | `setup-stub/*.cs` | the self-extracting installer window |
| Manifest | generated | every component with its SHA-256; no secrets, no demo data |
