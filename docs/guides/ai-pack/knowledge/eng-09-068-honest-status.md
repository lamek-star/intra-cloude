# Chapter 9 — Known limits, open items and how to scale — Honest status

Topic for: software engineers. Source: IntraForge Engineering Handbook, Chapter 9 — Known limits, open items and how to scale.

| Area | Status |
|---|---|
| Spare Parts / Inventory & Sales on the Docker runtime | **Qualified** (search, receive, sell, documents, files, restricted users, backup and recovery, offline, upgrade, accessibility, small-shop scale) |
| Pilot shop | Runs 1.5.7 on a real Windows PC; upgrades with automatic rollback have worked there |
| One-file Windows Setup | Tested on a clean Windows 11 VM and on the pilot PC |
| Pharmacy | Partially qualified |
| HR, School, Repair Shop, Rentals | Experimental |
| MySQL / SQL Server connectors | Tested against real MySQL 8.4 and SQL Server 2022 containers; not yet used at a customer |
| IF Credits Wallet (Android) | Debug build only; **not tested on a real phone** |
| Not qualified / not proven | The MSI/WSL2 route; code signing (no certificate); an external security scan; LAN access from a second PC (guide written: `docs/pilot/SECOND_PC_TEST_GUIDE.md`); commercial distribution (the MinIO AGPL and Docker Desktop licences need decisions first) |

IntraForge Pay credits are **simulated**. Real money would need a licensed payment partner, a legal review and a new
design for settlement — not a configuration change.
