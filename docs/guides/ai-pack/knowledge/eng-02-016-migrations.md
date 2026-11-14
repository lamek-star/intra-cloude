# Chapter 2 — The backend — Migrations

Topic for: software engineers. Source: IntraForge Engineering Handbook, Chapter 2 — The backend.

- Every model change ships with a migration; never edit a released migration.
- **Rollback safety:** the kit can roll an upgrade back to the previous images while the database keeps the newer
  schema. A new non-null column therefore needs a database default (`db_default=`), so the older code can still insert
  rows. Never drop or rename a column in the same release that stops using it.
- The shop upgrade runs `migrate` itself; on the test copy run
  `docker compose exec -T backend python manage.py migrate`.
