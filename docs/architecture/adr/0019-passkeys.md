# ADR-0019 — Passkeys: signing in with the owner's phone (WebAuthn)

Status: accepted; implemented in 1.5.1.
Date: 2026-11-08. Builds on ADR-0008 (capabilities; nothing here grants authority) and the Phase 10 TOTP
second factor. No new identity provider or datastore: credentials live in the control database next to `User`.

## Problem

The owner wants the highest authority in the shop -- the Super Administrator account, which is also the account
that opens IntraForge Pay as its administrator -- to be usable only by them, tied to the fingerprint or face on
their own phone, and started by scanning a QR code. A password (even with an authenticator code) can be shared,
phished or watched over a shoulder at a shop counter.

## Decision

1. **WebAuthn passkeys** (FIDO2), verified server-side with the `webauthn` library (Duo Labs, BSD-3-Clause,
   3.0.1, released 2026-09-25; new transitive dependencies `cbor2`, `pyasn1`, `pyasn1-modules`, `pyOpenSSL`).
   Writing CBOR/COSE/attestation parsing by hand is exactly what the engineering rules forbid for security code.
   The browser side uses only the built-in `navigator.credentials` API (no new npm dependency).
2. **The phone and the QR code are the browser's own feature.** IntraForge asks for a passkey with the `hybrid`
   hint, so Chrome/Edge on the shop PC show "use a phone or tablet" with a QR code first; the phone unlocks the
   passkey with its biometric. IntraForge never sees a fingerprint or face, only a signature. The phone-to-PC
   link (CTAP hybrid) is run by the operating systems and needs **Bluetooth on both devices and an internet
   connection for the phone and the PC** (the browsers relay the encrypted exchange through their vendor's
   tunnel service). IntraForge itself keeps working with no internet; on a shop with none, a passkey stored on
   the PC itself (Windows Hello) or a USB security key still works, and password sign-in stays available unless
   the owner switches it off (point 5).
3. **Bound to the address.** A passkey belongs to one relying-party ID, the host name the browser used. IntraForge
   uses the request's host (already validated by `ALLOWED_HOSTS`, the same value Django's CSRF origin check uses)
   as the RP ID and `https://<host[:port]>` as the expected origin, and stores the RP ID with each passkey. IP
   addresses are refused (the WebAuthn standard does not allow them): passkeys are made at
   `https://localhost:<port>` on the shop PC or at the shop-network name. A passkey made at one name does not
   work at another; the account page says which address each passkey belongs to.
4. **Adding a passkey needs the password again** (and the authenticator code when two-step is on), so a stolen
   session cannot quietly attach an attacker's passkey. Removing one needs the password too. User verification
   (biometric/PIN) is **required** at every use; a passkey sign-in therefore counts as both factors and skips the
   TOTP step. Sign-count regressions (a cloned authenticator) are refused by the library.
5. **"Passkey only" per account.** An account with at least one passkey may switch off password sign-in for
   itself. Then `auth/login/` refuses the password (audited as denied) and only a passkey signs in. Switching it
   on needs the password; switching it back off needs a passkey check made in the last five minutes in this
   session. Recovery if every passkey is lost: the `bootstrap_super_administrator`-style management command
   `passkey_reset` on the shop PC (physical access is the trust anchor, as for the keys file).
6. **Discoverable credentials, usernameless sign-in.** Sign-in options carry no user list, so the endpoint never
   reveals which emails exist or have passkeys. Challenges are 32 random bytes kept in the server-side session for
   five minutes and used once. All passkey endpoints use the existing `auth` throttle scope (10/min).
7. Every add, removal, sign-in, refused sign-in and passkey-only change is an `AuditEvent`.

## Consequences

- The owner can make the Super Administrator account passkey-only; Pay's administrator rights follow, because Pay
  staff sign in only through IntraForge.
- Customers' wallet sign-in (inside IntraForge Pay) is unchanged.
- Not verified on hardware here: the QR flow needs a real phone with Bluetooth next to the shop PC; single-label
  shop-network names (`https://shop-pc:8443`) depend on the browser accepting them as an RP ID with a trusted
  certificate. `localhost` is accepted by all current browsers.
