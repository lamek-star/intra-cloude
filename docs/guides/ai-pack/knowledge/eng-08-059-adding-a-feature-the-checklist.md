# Chapter 8 — Working on IntraForge: setup, tests, release — Adding a feature — the checklist

Topic for: software engineers. Source: IntraForge Engineering Handbook, Chapter 8 — Working on IntraForge: setup, tests, release.

1. **Read first:** `CLAUDE.md`, this handbook's Chapters 1–4, and the ADRs for the area.
2. **Decide where it lives:** an existing bounded app, or a new app if it is a new domain. A new datastore, identity
   mechanism or orchestration change needs a new ADR first.
3. **Model + migration** (with `db_default` on new non-null columns, for rollback safety).
4. **Service function** with the organization-scoped lookup, the capability check (and a `denied` audit on refusal),
   a transaction and a success audit event. New capability → `permissions/catalog.py` + `PERMISSIONS.md`.
5. **Thin view + serializer + URL.**
6. **Tests:** the happy path, the denied path, input validation, and **cross-organization IDOR** for any new tenant
   resource. For background work: a test that running the task twice is safe.
7. **Screen** (Chapter 3) with loading, empty, error and 403 states; a Vitest test for any logic.
8. **Docs** in the same change: the relevant doc under `docs/`, the user guide if people see it, and regenerate the
   handbook's reference parts:

```bash
docker compose exec -T backend python manage.py shell < docs/guides/tools/gen_reference.py > ref.md
python docs/guides/tools/gen_modules.py
python docs/guides/tools/build_guides.py
```

(`gen_reference.py` prints both reference parts separated by a line `=====MODELS=====`; put the first part in
`engineering/90-reference-api.md` and the second in `91-reference-models.md`.)
