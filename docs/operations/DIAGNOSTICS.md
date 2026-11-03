# Support diagnostics

When a pilot shop has a problem, the person supporting it needs facts: is it running, what version, what did
the services say, are backups being made. This is how to collect them **without handing over a secret**.

## Collect a bundle (Docker Compose stack)

```bash
scripts/support/collect-diagnostics.sh \
  --compose-file docker-compose.yml --env-file .env \
  --url https://localhost --out ./diagnostics --tail 500
```

It writes `intraforge-diagnostics-<UTC time>.tar.gz`. It changes nothing on the stack and can run while the
stack is down (redaction runs from the application image).

**In the bundle:** host and Docker versions, the status and images of every service, `/healthz` and `/readyz`,
free disk space, whether migrations are pending, the recent backups (from the application's own backup list),
the **names** of the configured settings, and the last N log lines of every service.

**Never in the bundle:** passwords, encryption or signing keys, tokens, cookies, connection-string
credentials, the `.env` file or any of its values, and customer records. The file names of customer uploads and
the contents of the database are not collected.

## How the secrets stay out

1. **Redaction.** Every text goes through `system.redaction` (`apps/backend/system/redaction.py`, nine unit
   tests in `system/tests/test_redaction.py`). It recognizes the *shapes* of secrets rather than a list of
   known names: a value after any key that names a secret (`*PASSWORD*`, `*SECRET*`, `*TOKEN*`, `*API_KEY*`,
   `*_KEY`, `auth`, `session`, `csrf`, ...), Bearer/Basic credentials, `user:password@host` in a URL, session and
   CSRF cookies, JWTs, Fernet keys and private-key blocks. Ordinary diagnostics -- log levels, paths, IDs,
   checksums, health output -- are left untouched (tested).
2. **Fail closed.** Redaction is probed once before anything is collected. If it cannot run (for example the
   application image is missing), no raw text is kept: every section says `[omitted: redaction unavailable]` and
   the script ends with a warning.
3. **Independent self-check.** Before the bundle is sealed, every secret **value** in the environment file is
   searched for literally in the whole bundle. One hit deletes the bundle and fails the script with exit code 3.

Verified on the qualification stack (2026-09-20): 12 files, 8 secret values from the real environment file
searched independently of the script, none found.

## What redaction cannot promise

A bundle is redacted text, not a proof of absence: a secret with no recognizable shape and no secret-looking
name, written into a log by application code, could survive. That is why the third step exists for every value
the installation itself holds, and why the bundle should still go only to the person supporting the pilot.
Customer data inside a log line (a name in an error message, for instance) is not redacted; the pilot
document asks the shop to review the bundle first.

## On Windows

The Control Center's Logs & Diagnostics screen tails one service at a time
(`installer/scripts/Get-IntraCloudContainerLogs.ps1`, capped at 2,000 lines) and runs
`Test-IntraCloudHealth.ps1`. Those are **not** run through this redactor, and the collector above has not been
run on the Windows appliance (no Windows environment is available for qualification): **Windows diagnostics
bundle -- EXTERNALLY BLOCKED.**
