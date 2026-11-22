# Chapter 6 — The shop kit: build, install, upgrade, operate — Building a kit (on the build machine, online, Docker Desktop running)

Topic for: software engineers. Source: IntraForge Engineering Handbook, Chapter 6 — The shop kit: build, install, upgrade, operate.

```bash
KIT_VERSION=1.5.9 CARRY_APPS_FROM=1.4.0-dbf44f593 MINIO_TAG=RELEASE.2025-09-07T16-13-09Z \
PAY_IMAGE=intraforge-shop-pay:1.5.9-srv PAY_SOURCE="<pay repo and commit>" \
PAY_REPO=<pay checkout> PAY_REF=<pay commit> \
SPAREPARTS_IMAGE=intraforge-shop-spareparts:labels PHARMACY_IMAGE=intraforge-shop-pharmacy:labels \
SPAREPARTS_SOURCE="<spare-part-shop commit>" \
bash scripts/shop-kit/build-shop-kit.sh <output-folder>
bash scripts/shop-kit/build-setup-exe.sh <output-folder>
```

- The kit is built from **committed source only** (`git archive HEAD`); `scripts/shop-kit` must have no uncommitted
  changes or the build stops.
- **Pay image:** Pay runs from its image's WorkingDir, `/srv/ifpay`. A newer Pay is the 1.5.0 image with that folder
  replaced from a commit (`FROM intraforge-shop-pay:1.5.0-cashback`, `RUN rm -rf /srv/ifpay/ifpay`,
  `COPY --chown=ifpay:ifpay ifpay /srv/ifpay/ifpay`, the context from `git archive <commit> ifpay`). The build refuses
  a Pay image whose `<WorkingDir>/ifpay` is not exactly `PAY_REF`'s `ifpay`: kits 1.5.6-1.5.8 copied it into
  `/app/ifpay`, which Pay never reads, and shipped the 1.5.0 code.
- The result is `IntraForge-Local-<version>-<commit>.zip` + `.sha256`, then `IntraForge-Setup-<version>-<commit>.exe`
  (Setup = stub + zip + optional Docker Desktop and WSL installers, each with its SHA-256 in a trailer).
- The C# programs are compiled with `csc.exe` from .NET Framework 4.x, which every Windows 10/11 has — no SDK needed.
