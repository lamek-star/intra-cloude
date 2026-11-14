# Chapter 4 — Security and permissions — Who is calling

Topic for: software engineers. Source: IntraForge Engineering Handbook, Chapter 4 — Security and permissions.

| Caller | How they prove it | Where |
|---|---|---|
| A person | Email + password → session cookie; optional TOTP second step; passkeys (WebAuthn); recovery codes | `accounts` |
| An application | `Authorization: Bearer pdc_sk_…` → its ServiceAccount's identity user | `applications/authentication.py` |
| A service application (Pay, Spare Parts, Pharmacy) | Its deployment's service token on the **internal** API only | `service_apps/authentication.py` |
| The media agent | That Movie Shop's own agent credential | `movie_shop/views.py` |
| The app runner | A shared runner token, fixed operations only | `sites/runner.py`, `app_runner/` |
| A portal customer | A portal account for one shop (phone number + password) | `movie_shop/portal.py` |

Person details:

- **TOTP** (RFC 6238) is implemented directly in `accounts/totp.py` with the standard library; secrets are encrypted
  at rest with Fernet (`CREDENTIAL_ENCRYPTION_KEY`).
- **Recovery codes** are stored hashed; each works once.
- **Password reset by an administrator** sets `must_change_password`; `PasswordChangeMiddleware` then refuses every API
  call except "who am I", changing the password and signing out.
- New administrative role grants can require MFA in internet-gateway mode.
- Sign-in endpoints are throttled at **10 per minute** on purpose.
