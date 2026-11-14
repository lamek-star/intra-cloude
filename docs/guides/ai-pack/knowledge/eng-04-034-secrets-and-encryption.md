# Chapter 4 — Security and permissions — Secrets and encryption

Topic for: software engineers. Source: IntraForge Engineering Handbook, Chapter 4 — Security and permissions.

| What | How |
|---|---|
| MFA secrets, connected-database passwords, environment secrets | Fernet, key from `CREDENTIAL_ENCRYPTION_KEY` |
| Environment secrets, application credentials | Shown exactly once; stored encrypted or hashed |
| Backups and `.icp` exports | AES-256-GCM with an Argon2id-derived key (`exports/container.py`) |
| Webhooks | HMAC-signed bodies, at-least-once delivery, receivers de-duplicate by event id |
| Licences | Ed25519-signed activation codes; the private key never leaves the vendor (`licensing/codes.py`) |
| Diagnostics | Secrets redacted before anything is written (`system/redaction.py`) |

The kit generates fresh random secrets per shop into `.env`. Never commit `.env`, keys or passwords; never print a
secret into a log.
