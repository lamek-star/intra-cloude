# Chapter 8 — Working on IntraForge: setup, tests, release — Setting up a development machine

Topic for: software engineers. Source: IntraForge Engineering Handbook, Chapter 8 — Working on IntraForge: setup, tests, release.

Needs: Git, Docker Desktop (with WSL 2 on Windows), Node 24, Python 3.13 (for the docs tools and linters).

1. Copy `.env.example` to `.env` and fill in the secrets (database passwords, `SECRET_KEY`, object-storage root
   credentials, `CREDENTIAL_ENCRYPTION_KEY`). Never commit `.env`.
2. `docker compose build`
3. `docker compose up -d postgres-control postgres-tenant valkey object-storage` and wait for the health checks.
4. `docker compose run --rm backend python manage.py migrate`
5. `docker compose run --rm backend python manage.py seed_permissions`
6. `docker compose run --rm backend python manage.py bootstrap_super_administrator you@example.com`
7. `docker compose up -d backend worker beat frontend proxy`
8. Open `https://localhost:8443/` (accept the local certificate, or trust Caddy's root CA).

For a disposable copy for tests, drills and demos use the qualification stack (`scripts/qualification/compose.yaml`,
port 8444). A full shop-like test copy can be installed from a kit into its own folder (the project's own was
`test-1.5.0`, port 9543), with test-only logins kept beside it.
