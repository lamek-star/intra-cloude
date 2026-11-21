# ADR-0025: Feature groups -- chosen in Setup, changed by the Super Administrator, refused by the server

Status: accepted; implemented (2026-11-21).

## Problem

A shop that only sells spare parts does not want the Developer section, hosted websites or the database builder on
every screen, and a shop owner asked to choose at installation which parts IntraForge shows, and to add them later.
Hiding menu items alone would leave every hidden part one typed URL (or one API call) away.

## Decision

1. **Four groups** (agreed with the shop owner), defined in `apps/backend/system/features.py`:
   `business_apps` (Spare Parts, Pharmacy, App Platform templates), `pay_media` (IntraForge Pay, Movie Shop and its
   portal), `websites_developer` (hosted websites, the internet gate, Developer: applications, credentials,
   environments, webhooks, OAuth) and `files_data` (storage, databases, imports, analytics, dashboards, sharing).
   The core is never a group: sign-in, organizations, members and roles, teams, units, audit log, backups, health,
   licence, version and portable export stay whatever is chosen.
2. **One installation-wide setting**, `system.FeatureSettings` (one row). Setup writes the owner's choice to the keys
   file as `INTRAFORGE_FEATURES` (`business_apps,files_data`; empty = none; unset = all, so every installation from
   before this ADR keeps everything). It seeds the row the first time it is read; from then on the row is the truth,
   it travels in the control-database backups, and upgrades never touch it.
3. **Only the Super Administrator** (`system.admin`, platform-wide) changes it: `PATCH /api/v1/system/features/`
   (browser sessions only), audited as `system.features.update` with the before and after lists. Anyone signed in may
   read it (`GET`), which is how the web app hides what is off.
4. **The server refuses a switched-off group** -- the web app hiding it is presentation only:
   - whole URL modules are wrapped at the URL level (`features.gated(group, "storage.urls")`), so a view added to one
     of those modules later is covered without anyone remembering to: they answer `403 {"error": {"code":
     "feature_disabled", ...}}`; the same for the OAuth endpoints, hosted-site serving and its certificate check;
   - application types: a switched-off type is not offered, cannot be installed, is left out of the Apps list, cannot
     be opened, its sign-in page is a 404, and session introspection refuses its sessions (everyone is signed out of
     it, without deleting the sessions); Spare Parts and Pharmacy cannot ask a switched-off Pay for payments;
   - application credentials (`Bearer pdc_sk_...`) are refused outright while `websites_developer` is off.
   The internal service API that installed applications use (`/api/v1/internal/service-apps/...`) is not gated, so an
   application's own files, audit relay and heartbeat keep working while it is hidden.
5. **Nothing is deleted.** Switching a group off hides and refuses it; switching it back on brings everything back as
   it was (tested).
6. **Internet access must be switched off before `websites_developer` is hidden**: otherwise the tunnel would keep the
   shop reachable from the internet with nobody able to see or switch it off (the change is refused with a message).

## Consequences

- A shop can install with only the parts it uses and add the rest later on the **Features** page (Dashboard → System
  health → Features), without reinstalling.
- New URL modules must be placed in a group in `config/api_urls.py` deliberately; leaving one ungated makes it core.
- Not covered: the Control Center has no Features screen (the web page is the one place to change it), and hiding a
  group does not stop that group's containers (they idle; Spare Parts/Pay containers keep their health checks).
