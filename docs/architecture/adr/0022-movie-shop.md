# ADR-0022 — Movie Shop: a catalogue of the shop's own video library, sold at the counter and on the shop Wi-Fi

Status: accepted; phases 1 and 2 implemented (2026-11-10), phases 3-4 planned.
Date: 2026-11-10. Builds on ADR-0001 (control plane / data plane), ADR-0008 (capabilities), ADR-0018 (service
applications and the Pay bridge), ADR-0021 (shop names). Adds one Django app (`movie_shop`) and one Windows helper
(the media agent); no new datastore, identity provider or container image.

## Problem

A video shop keeps its films and series as folders and files on its own drives (an internal disk, an external disk,
a NAS share). The owner wants IntraForge to show that library as a catalogue (folders as categories, a cover and the
details for each title), to sell titles for IntraForge Pay credits with rewards, to copy a sold title onto the
customer's USB stick or phone, and to let customers browse and buy on the shop Wi-Fi through a customer portal that
also shows the shop's own ads. Design mockups: `design-references/movie-shop-mockups/`.

IntraForge runs in Docker (WSL2) on the shop PC, on an internal-only network: the containers cannot see the PC's
drives, a USB stick plugged in at the counter, or a NAS share mapped in Windows.

## Decision

1. **The files never enter IntraForge.** The library stays where it is. IntraForge keeps only metadata: the shop,
   its libraries (a folder on a drive), the titles found there (category, title, year, kind, relative path, size,
   episodes), prices, and a small cover picture per title (stored as an ordinary IntraForge file in the shop's
   `movie-covers` bucket, through `storage.services.upload_file`, so it is scanned, audited and backed up like any
   file). This is ADR-0001 unchanged: the control plane holds metadata, object storage holds the covers.
2. **The media agent does all file work, on Windows.** `IntraForgeMediaAgent.exe` (C# 5, built like the Control
   Center with the .NET Framework compiler that ships with Windows) runs as the signed-in user on the shop PC, so it
   sees exactly the drives the owner sees (fixed, removable, mapped network drives). It is a **client** of
   IntraForge's API, never a server: it reports the PC's drives and their top folders, scans the folders the owner
   chose, uploads covers, and (phase 2) carries out copy jobs onto the customer's drive. No container gains access to
   the host and no inbound port is opened.
3. **The agent authenticates as an Application.** Creating a shop registers an `applications.Application` ("Movie
   Shop media agent") with its service account; the owner issues its credential from the Movie Shop page (shown once)
   and gives it to the agent (`IntraForgeMediaAgent.exe pair <address> <token>`, kept with Windows DPAPI). Agent
   endpoints accept only that application's own credential (`request.auth` is an `ApplicationCredential` whose
   application is the shop's agent application); every other endpoint refuses application credentials and requires
   a human session. Revoking the credential cuts the agent off. No new token scheme.
4. **Capabilities** (ADR-0008, default-deny): `movies.read` (see the catalogue), `movies.manage` (shops, libraries,
   prices, rewards, ads, agent credential), `movies.sell` (counter sales and copy jobs, phase 2), granted per shop
   (resource type `movie_shop`) or organization-wide. The organization administrator holds all three through its
   role; no other system role gets them by default.
5. **Scanning rules** (the agent applies them, the server re-validates): under the library folder each sub-folder is a
   category; a video file (`.mp4 .mkv .avi .mov .m4v .wmv .ts .webm`) is a title; a folder holding several video files
   (or `Season n` folders) is a series. The title and year come from the name (`Desert Wind (2025).mp4`, dots and
   underscores as spaces, release tags such as `1080p`, `x264`, `WEBRip` removed). A picture with the same name, or
   `poster`/`cover`/`folder` `.jpg`/`.png` beside it, becomes the cover (resized to 400 px wide); without one the
   catalogue draws a cover from the title. A scan replaces the library's titles atomically; a title's owner-set
   price and hidden flag survive re-scans (matched by relative path).
6. **Money stays in IntraForge Pay** (ADR-0018). A sale is a Pay payment request through the existing Pay bridge,
   taken by the shop's service identity, which needs `ifpay.checkout` on that Pay; the customer confirms in their own
   wallet. Cashback is Pay's own maker/checker cashback. Movie Shop points (welcome, every-10th-free, referral,
   birthday) are a separate loyalty ledger that only ever discounts Movie Shop purchases; turning points into wallet
   credit is a Pay allocation the owner proposes and a supervisor approves in Pay. Nothing in `movie_shop` moves money.
7. **Customer portal accounts are not IntraForge users** (phase 3). A `PortalCustomer` (name, phone, password hash,
   optional birthday) belongs to one shop, signs in only to that shop's portal, and can do nothing else in IntraForge.
   Sign-up is rate-limited with the `auth` throttle and needs the owner's approval ("Add to IF Pay"), which creates
   the customer's Pay wallet through a new internal Pay endpoint (a change to the Pay repository, reviewed there).
   The portal is reached on the shop network only (`/portal/<shop>`), never through the internet gateway.
8. **Ads** (phase 4) are the shop's own records (picture, title, link, dates) shown on its portal only.

## Phases

| Phase | Scope | Status |
| --- | --- | --- |
| 1 | `movie_shop` app (shop, libraries, titles, covers, prices), agent credential, media agent (drives, scan, covers), owner catalogue page | implemented |
| 2 | Counter sale: cart, Pay payment request, copy jobs carried out by the agent with progress, sales list | implemented |
| 3 | Customer portal: sign-up on the shop Wi-Fi, approval and Pay wallet, browse, buy, wallet and points, reward rules | planned (needs the Pay endpoint) |
| 4 | Ads on the portal | planned |

## Consequences

- The shop PC must run the media agent for scanning and copying; the catalogue stays readable when it is off.
- A NAS share works when it is mapped as a drive letter in Windows for the signed-in user.
- Titles are only as good as the folder names; the owner can edit a title, year, category and price.
- The owner is responsible for holding the rights to the films and series sold (the Movie Shop page says so).

## Rejected

- **Bind-mounting the library into the backend container**: no access to USB sticks inserted later or to mapped NAS
  drives, and it would give a container write access to the owner's disks.
- **An HTTP server inside the agent** called by the backend: the containers have no route to the host by design;
  an inbound port would be a new attack surface.
- **Customer accounts as IntraForge users**: would place strangers from the shop Wi-Fi in the organization's identity
  system and its audit of staff actions.
