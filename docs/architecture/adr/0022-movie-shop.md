# ADR-0022 — Movie Shop: a catalogue of the shop's own video library, sold at the counter and on the shop Wi-Fi

Status: accepted; phases 1-4 implemented (2026-11-10).
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

### Phase 3 as built

- **Portal sessions.** `PortalSession` keeps the SHA-256 of a random token; the cookie `ifportal` is HttpOnly,
  SameSite=Strict, Secure in production, path `/api/v1/portal/`, 30 days. No IntraForge authentication runs on the
  portal API; every change must carry `X-Portal-Request: 1` (a custom header another site cannot send without a CORS
  preflight). Sign-up and sign-in use the `auth` throttle (10/minute). An unknown phone number is checked against a
  dummy hash so both answers take as long. A customer is looked up only among the named shop's customers.
- **Ordering, not paying, on the portal.** A portal order is a `Sale` in status `ordered` with no drive. The counter
  (a person holding `movies.sell`) charges it when the customer brings a USB drive: the drive, IF Pay or cash, and only
  then the rewards apply. So every payment request is still made on behalf of a staff member holding
  `ifpay.checkout`, exactly as in phase 2; the portal never asks Pay for money. At most 3 orders wait per customer.
- **Rewards, applied at charge time under a lock on the customer row:** every Nth title the customer buys is free (the
  cheapest in the cart first; counted over their paid sales), then their points if they chose to use them (1 point =
  1 credit, never more than what is left). Points spent are a `redeem` entry; a sale cancelled or expired gives them
  back (`returned`). Welcome points on approval, invite points to the referrer when the invited customer is approved,
  birthday points once a year in the birthday month at the first visit.
- **"Add to IF Pay"** calls Pay's new `POST /internal/customers` through the Pay bridge with the approving person's
  capabilities (they must hold `ifpay.customers.manage`), keyed by `movie-customer:<id>` so a retry opens the same
  wallet. Pay answers once with a one-time first password, shown to the owner once and never stored by IntraForge;
  the wallet makes the customer choose their own password before anything else. The portal shows the wallet's
  username and balance from `GET /internal/customers/<id>`, which Pay answers only to the application that opened it.
- **Limits:** a lost first password cannot be reset yet (neither Pay nor IntraForge has a reset); counter sales cannot
  yet be linked to a portal customer, so only portal orders earn and use rewards; the portal address is the shop PC's
  own (`https://<pc>:8443/portal/<shop>`) and shows the local certificate warning until the shop's root certificate is
  trusted on the phone.

### Phase 4 as built

- An `Ad` is the shop's own record: title, short text, who it is for (another shop or business, or empty for the shop
  itself), optional first and last day, on/off, order, and a picture stored like the covers (a real JPEG, PNG or WebP,
  up to 2 MB, in the shop's covers bucket, under the shop's own identity). At most 50 per shop; `movies.manage`.
- A tap opens one of the shop's own films or a web address. Only `http`/`https` addresses are accepted (no
  `javascript:`, `data:` or quotes), and the portal opens them in a new tab with `noopener,noreferrer`.
- The portal shows at most 10 ads that are switched on and within their dates, to anyone on the open portal (also on the
  sign-up screen), always labelled "Ad · <who it is for>". It counts views (each time the list is shown) and taps; the
  counts are the owner's and nothing identifies the customer.

### Later additions (2026-11-11)

- **Music**: audio files are titles (`music`), a folder of them an album (`album`); sold and copied like films.
- **The owner's poster**: Edit title takes a picture (JPEG/PNG/WebP up to 3 MB, stored like covers); `cover_locked`
  keeps it through every re-scan (the agent is not asked for the folder's picture, and an upload would not replace it)
  until the owner goes back to the folder's picture.
- **Renaming** a shop or a library; the owner **edits** a customer's name, phone and birthday.
- **Password recovery with the owner's permission**: the customer asks on the portal (the answer never says whether a
  phone number has an account); the owner issues a one-time code (hashed, one hour, five tries, earlier codes
  revoked); the customer sets a new password with it and their sessions end. The IF Pay wallet gets a new one-time
  password through Pay's `POST /internal/customers/<id>/reset-password` (the owner must hold
  `ifpay.customers.manage`).
- **The Movie Shop is an app**: shops are listed with the installed applications and "Movie Shop" under available
  ones; its own sidebar link is gone.
- **Faster copying**: the agent copies with Windows' `CopyFileEx` (unbuffered for files from 64 MB), one worker per
  customer drive (two drives fill at once), and progress goes to IntraForge from a timer so a slow answer never pauses
  a copy.

## Phases

| Phase | Scope | Status |
| --- | --- | --- |
| 1 | `movie_shop` app (shop, libraries, titles, covers, prices), agent credential, media agent (drives, scan, covers), owner catalogue page | implemented |
| 2 | Counter sale: cart, Pay payment request, copy jobs carried out by the agent with progress, sales list | implemented |
| 3 | Customer portal: sign-up on the shop Wi-Fi, approval and Pay wallet, browse, buy, wallet and points, reward rules | implemented (Pay: `feature/shop-app-customers`) |
| 4 | Ads on the portal | implemented |

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
