# Chapter 6 — The shop kit: build, install, upgrade, operate — Building a kit (on the build machine, online, Docker Desktop running)

Topic for: software engineers. Source: IntraForge Engineering Handbook, Chapter 6 — The shop kit: build, install, upgrade, operate.

```bash
KIT_VERSION=1.5.7 CARRY_APPS_FROM=1.4.0-dbf44f593 MINIO_TAG=RELEASE.2025-09-07T16-13-09Z \
PAY_IMAGE=intraforge-shop-pay:1.5.6-counters PAY_SOURCE="<pay repo and commit>" \
SPAREPARTS_IMAGE=intraforge-shop-spareparts:labels PHARMACY_IMAGE=intraforge-shop-pharmacy:labels \
SPAREPARTS_SOURCE="<spare-part-shop commit>" \
bash scripts/shop-kit/build-shop-kit.sh <output-folder>
bash scripts/shop-kit/build-setup-exe.sh <output-folder>
```

- The kit is built from **committed source only** (`git archive HEAD`); `scripts/shop-kit` must have no uncommitted
  changes or the build stops.
- The result is `IntraForge-Local-<version>-<commit>.zip` + `.sha256`, then `IntraForge-Setup-<version>-<commit>.exe`
  (Setup = stub + zip + optional Docker Desktop and WSL installers, each with its SHA-256 in a trailer).
- The C# programs are compiled with `csc.exe` from .NET Framework 4.x, which every Windows 10/11 has — no SDK needed.
