# ADR-0023: Licensing -- a 30-day trial, then one serial number per PC

Status: accepted; implemented (2026-11-11).

## Problem

IntraForge Local Edition is sold to shops. The owner wants a free first month, then a serial number (SN) that works
on one PC only, and a master SN for their own PCs. IntraForge runs without the internet, so there is no licence server
it can always reach, and it must never lock a shop out of its own data.

## Decision

1. **Signed, offline activation.** The vendor's licence tool (`scripts/licensing/intraforge-license.py`, run on the
   vendor's PC) holds an Ed25519 private key; IntraForge holds only the public key (`LICENSE_PUBLIC_KEY`). An
   activation code (`IFA1.<payload>.<signature>`) binds one SN to one PC code. Nobody without the private key can make
   a working code, and a code made for one PC fails on any other. The private key lives in the vendor's licensing
   folder (default `C:\Users\<vendor>\intraforge\licensing`), never in a repository or a kit.
2. **One SN, one PC** is kept by the vendor's registry (`registry.json` next to the key): the tool refuses to activate
   a sold SN for a second PC unless the vendor says `--transfer`. Offline, nothing else can know that an SN was used
   before; this is why activation goes through the vendor (one message: the SN and the PC code).
3. **The master SN** (`IFM-...`) activates any number of the vendor's own PCs, each still with its own signed
   activation code, so a leaked master SN alone unlocks nothing.
4. **PC code**: the first 8 bytes of SHA-256 over the Windows machine id and the motherboard UUID, written by the kit's
   start script (`Write-ShopMachineIdentity`) to `<data folder>\machine\pc-code`, mounted read-only into the backend.
   The containers cannot see the hardware themselves.
5. **Trial**: 30 days from the first start, kept in the database and in the Windows registry
   (`HKCU\Software\IntraForge\FirstStart`, also written to `machine\first-start`), so a reinstall does not start a new
   trial. A clock set back by more than a day ends the trial.
6. **Without a licence after the trial IntraForge is read-only** (`licensing.middleware`): signing in and out,
   activating the licence and the internal service API stay open; every other request that would change something is
   refused with `licence_required`. Reading, exporting and the scheduled backups keep working: a shop never loses
   access to its data.
7. **Who activates**: the Super Administrator or an administrator of any organization (`permissions.manage`).
   Activation is audited (`licence.activate`) and rate-limited like sign-in.
8. **Enforced only in the shop kit** (`LICENSE_ENFORCED=true` in its compose file); development and tests run
   without it.

## Consequences

- The vendor must keep the licensing folder safe and backed up: losing the private key means no new activation codes
  (existing ones keep working); leaking it means anyone can make codes.
- A new motherboard or a Windows reinstall changes the PC code; the vendor moves the SN with `--transfer`.
- Offline licensing stops ordinary copying, not a determined programmer with access to the PC (the code is on it).

## Rejected

- **An online licence server**: IntraForge must work without the internet; an online activation can be added later
  as an option on top of this one.
- **Locking IntraForge completely after the trial**: a shop must always be able to reach and export its own data.
