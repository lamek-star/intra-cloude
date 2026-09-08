# ADR-0013: Bundle Docker Engine Into the WSL2 Rootfs (Release-Pinned, Not Live-Updated)

Status: Accepted
Date: 2026-09-02

## Decision

The WSL2 rootfs tarball `Import-IntraCloudDistro.ps1` imports ships with
Docker Engine, the Compose plugin, and `systemd=true` already baked in,
built by a new release-time pipeline (`installer/release/
Build-IntraCloudRootfs.ps1`) on a Linux build agent. `Initialize-
IntraCloudDistro.ps1` no longer installs Docker via `curl -fsSL
https://get.docker.com | sh` inside the customer's distro at
configure-time — that call is removed outright, not left as a fallback.
If a rootfs somehow arrives without Docker already present (e.g. a
hand-assembled one for support/debugging, per that script's own
"idempotent by design" contract), `Initialize-IntraCloudDistro.ps1`
fails loudly with a clear remediation message rather than silently
reaching for the internet.

Docker Engine's version is therefore **pinned at IntraForge release
time**, not continuously patched inside an already-installed appliance.
Keeping it current is a release-cadence concern — rebuild the rootfs
with an updated Docker Engine version as part of a new IntraForge
release, the customer upgrades to that release — not a live/background
auto-update mechanism running inside the installed product.

## Context

ADR-0012 chose the WSL2-managed-appliance architecture and already
flagged "offline install: Good — distribution image + container images
ship together" as one of its advantages, but that was aspirational at
the time: no rootfs-build pipeline existed, `Import-IntraCloudDistro.
ps1`'s own docstring already described the rootfs as "a Docker Engine +
Compose base image, produced by the release pipeline — Phase 21," and
Phase 21 never built one. `WINDOWS_QUALIFICATION_MATRIX.md` documents
this gap explicitly: "a real release bundle populating `AppBundlePath`
doesn't exist as a build artifact yet." In practice, every install to
date has depended on internet access at configure-time to fetch Docker
Engine — a real violation of CLAUDE.md's non-negotiable rule 7
("Local-first. No internet dependency for normal operation") for the
installation step specifically, even though the *running* stack has
always been genuinely offline.

This ADR is scoped narrowly to the Internal Pilot v0.9 mandate: make
installation itself offline, without inventing a new update-delivery
system that doesn't exist anywhere else in this product.

## Alternatives Considered

1. **Keep `get.docker.com` at configure-time (status quo).** Rejected —
   the entire point of this decision is to close the one remaining
   internet dependency in installation.
2. **Bundle Docker Engine's `.deb` packages directly in `AppBundlePath`**
   (alongside the container image tarballs) and have `Initialize-
   IntraCloudDistro.ps1` `dpkg -i` them into an already-imported plain
   distro. Rejected in favor of baking them into the rootfs itself:
   `dpkg -i`-ing a package set at configure-time still means resolving
   and validating a dependency closure on the customer's machine, which
   is exactly the kind of per-machine variance a rootfs-level bake
   avoids — a rootfs built once, by the release pipeline, on a known
   base image, is more reproducible and easier to verify (`docker
   version` after import, no install step to fail at all) than a
   package install repeated on every customer machine.
3. **Bundle Docker Engine, but add a live auto-update channel inside the
   running appliance (Watchtower-style, or a scheduled `apt upgrade`
   inside the distro).** Rejected — this would add a genuinely new
   internet-dependent, self-modifying background process to an
   otherwise local-first product, is a meaningfully bigger security
   surface (an unattended privileged package upgrade inside the
   distribution, sight-unseen by the customer), and nothing else in
   IntraForge auto-updates itself this way today. Introducing that
   mechanism deserves its own dedicated design pass and threat-model
   entry, not a side effect of closing the offline-install gap — see
   Open Items.

## Consequences

- **Positive:** installation genuinely needs no internet access once
  the release bundle (container images + rootfs) is staged on the
  Windows machine — closes the last internet dependency `ROADMAP.md`'s
  Phase 21 entry flagged as still open.
- **Positive:** more reproducible installs — every customer on the same
  IntraForge release gets the exact same Docker Engine version, built
  and verified once by the release pipeline, rather than "whatever
  `get.docker.com` resolves to on install day."
- **Negative, accepted:** Docker Engine no longer receives independent
  security patches between IntraForge releases. A Docker Engine CVE
  fixed upstream reaches an installed appliance only when IntraForge
  itself cuts a new release with a rebuilt rootfs — this is a real
  latency tradeoff, not a hidden one. Mitigate by treating "Docker
  Engine version" as a tracked line in each release's `RELEASE_NOTES.md`
  (already auto-generated by `New-ReleaseArtifacts.ps1` from commit
  history — the rootfs-build commit will show there) and by not letting
  the pinned version go stale indefinitely; a concrete rebuild cadence
  is a release-process decision for whoever owns cutting IntraForge
  releases, not fixed by this ADR.
- **Negative, accepted:** the release pipeline gains a new artifact
  class (a Linux rootfs tarball) and a new build-agent requirement (a
  Linux runner capable of running real `apt install docker-ce`, since
  Windows CI can't produce this natively) — genuine new engineering
  surface, not a trivial config change.

## Security Considerations

- No new network trust boundary is introduced — Docker Engine still
  never exposes its daemon socket over TCP (ADR-0006's rule, unchanged).
- Redistributing Ubuntu base packages + Docker Engine CE packages inside
  the rootfs is a license-compliance question that needs the review
  already tracked as an open item in `RELEASE_READINESS.md` — this ADR
  does not resolve that, it creates the first concrete artifact that
  review must cover.
- The removed `get.docker.com` fallback was itself a real, if narrow,
  supply-chain trust point (fetching and piping a remote install script
  to a shell at configure-time, on every customer machine, using
  whatever Docker Engine version happens to be current that day).
  Removing it in favor of a single release-time build is a net
  reduction in that surface, not just a convenience change.

## Open Items

- **No update-delivery mechanism exists yet for Docker Engine CVEs that
  land between IntraForge releases.** If the Internal Pilot proves out
  and this becomes a real product concern, a live-update mechanism is a
  legitimate future direction — but it needs its own ADR and threat-
  model entry (see Alternative 3 above), not retrofitting into this
  decision.
- **Rootfs rebuild cadence** (how often Docker Engine's pinned version
  gets refreshed, independent of an IntraForge feature release) is
  unset — a release-process decision, not an engineering one, left to
  whoever owns the release calendar.
- **License-compliance review** of the bundled Ubuntu base + Docker
  Engine CE packages is still open, tracked in `RELEASE_READINESS.md`.
