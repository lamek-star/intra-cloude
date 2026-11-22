# Chapter 4 — Security and permissions — Access requests and single-use links (ADR-0026)

Topic for: software engineers. Source: IntraForge Engineering Handbook, Chapter 4 — Security and permissions.

- **One identity.** Apps never store passwords: "each app's own login" is each app's branded sign-in page and its
  **Request access** page (`apps/frontend/src/app/request-access`), backed by IntraForge accounts.
- **Asking** (`POST /api/v1/access/apps/<app>/`, throttle scope `auth`): signed out it creates an **inactive** `User`
  and an `organizations.AccessRequest`; the answer is the same whether or not the email exists (no enumeration).
  Signed in, it asks for the current account. Only that app's role slugs may be asked for.
- **Deciding** (`organizations/access.py`): needs `users.manage` **and** `permissions.manage`; the administrator's
  `role_slug` is given through `Membership` + `permissions.services.assign_role` (so the gateway MFA rule applies).
  The app's own list goes through `GET/POST /api/v1/internal/service-apps/access-requests/` acting for the signed-in
  person (`actorId`), with the same capability check; the confirmation-link host must pass `ALLOWED_HOSTS`.
- **Links** (`accounts/links.py`, `accounts.AccountLink`): 32 random bytes, only SHA-256 stored, 72 hours, token in
  the URL **fragment** (`/confirm#t=...`) so it reaches no log or Referer; a new link revokes the old; used, revoked
  and expired links do nothing; `account.link.create|use|expired` are audited. No temporary password is ever shown.
  E-mail is optional (`EMAIL_HOST`, `accounts/mail.py`).
- **Who may register** (`system/features.py`: `closed` / `requests` / `open`, on `FeatureSettings.registration`):
  `/auth/register/` answers 403 `registration_closed` unless open or **first run** (no organization made by a person;
  organizations created by `@service.internal` identities do not count).
- **Phone approver** (`manage.py approver_account create`): an inactive account with an unusable password; its link
  allows the first passkey without a password (`passkeys.registration_options`) and then sets `passkey_only`.
- Tests: `organizations/tests/test_access_requests.py` (including cross-organization IDOR).
