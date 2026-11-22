# Chapter 5 — Applications on IntraForge — 5.2 Service applications (ADR-0018)

Topic for: software engineers. Source: IntraForge Engineering Handbook, Chapter 5 — Applications on IntraForge.

A service application is a separately built program that runs as its own container and uses IntraForge for identity,
storage, settings and audit.

- **Types** (`service_apps/types.py`) declare each app's capabilities, the one needed to open it, its settings schema
  (validated by IntraForge and again by the app) and the tables counted in the removal confirmation.
- **Deployments** (`deployments.py`, `SERVICE_APP_DEPLOYMENTS`) are the containers that exist in this installation:
  `pay-1`…`pay-3`, `spareparts`, `pharmacy`. Each gets a service token and a database password in `.env` — only the
  values it needs, never the whole file.
- **Provisioning** (`provisioning.py`) creates one PostgreSQL login role per deployment and one schema per installed
  instance in the tenant database.
- **Open** (`views.py`, `sessions.py`): a person with the open capability clicks **Apps > Open**; IntraForge creates a
  short-lived browser session for that app and redirects to `/apps/<deployment>/`.
- **The internal API** (`internal_views.py`, `/api/v1/internal/`): reachable only on the internal network, authenticated
  by the deployment's token, scoped to that deployment's own instance — there is no way to name another instance.
  It serves the person's identity and capabilities, settings, file storage and audit writes.
- **The Pay bridge** (`pay_bridge.py`, `app_pay.py`): other apps (the Movie Shop, a hosted Node.js app with its
  `IF_API_TOKEN`) ask the organization's Pay to take a payment; IntraForge picks the Pay and passes the result back.
