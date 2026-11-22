# Chapter 5 — Applications on IntraForge — 5.4a The Developer section (Organization > Developer)

Topic for: software engineers. Source: IntraForge Engineering Handbook, Chapter 5 — Applications on IntraForge.

Every tab is real; none is a placeholder any more.

| Tab | Backed by |
|---|---|
| Overview, Applications, Environments, Webhooks, SDKs, Docs | `applications/`, `environments/` (unchanged) |
| Database, Storage | the organization-wide lists (`organizations/<id>/tenant-databases/`, `.../buckets/`), the same pages as Organization > Databases / Storage, shown with the Developer tab bar |
| API Keys | each application's own credentials endpoint, combined in the browser (same permission check per application); flags active keys unused for 30+ days; revoke with a confirmation |
| API Logs | `GET organizations/<id>/api-requests/` (`?application=`, `?errors=1`, `?method=`, limit/offset) over `ApiRequestLog` (`applications/activity.py`) |
| Usage | `GET organizations/<id>/api-usage/?days=1..30` (never more than `API_REQUEST_LOG_DAYS`): per application requests, failures, average/slowest time, last request; per day |
| Auth | the platform OAuth/OpenID provider's client admin (`oauth-clients/`, Super Administrator only, whole installation); a new client **asks each person for consent unless the Super Administrator unticks it** for IntraForge's own apps |

API Logs and Usage accept browser sessions only and need membership plus `application.read`: an application's key
cannot read every application's traffic.

**Daily request limits** (`applications/quotas.py`): `Application.daily_request_limit` (empty = no limit) is set with
`PATCH applications/<id>/` by a person holding `application.credentials.manage` — never by an application key, which
could lift its own limit (audit `application.limit.update`). It is enforced in `ServiceAccountAuthentication`, so it
covers every endpoint a key can reach, also those with their own `throttle_classes` (uploads, imports) that DRF's
default throttles never see. One shared counter per application per day lives in the cache (Valkey, shared by all
gunicorn workers); a day is `settings.TIME_ZONE` (UTC). Over the limit: 429 with `Retry-After` until midnight, and the
refused request is still written to `ApiRequestLog`. If the cache is down the request is allowed and a warning logged:
the limit protects resources, it is not an access rule. The application page shows "N of LIMIT today"; Usage has a
"Today / daily limit" column. People's own sessions are never counted.
