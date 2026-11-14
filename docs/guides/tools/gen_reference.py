"""Generates the engineering handbook's reference chapters from the running code (never by hand):
the API (every URL, its methods, view and description) and the data model (every model, field and relation).

Run inside the backend container, writing Markdown to stdout:
    docker compose exec -T backend python manage.py shell < docs/guides/tools/gen_reference.py > api+models.md
The output has two parts separated by a line "=====MODELS=====".
"""

import inspect

from django.apps import apps
from django.urls import URLPattern, URLResolver, get_resolver

OWN_APPS = {
    "accounts", "organizations", "permissions", "workspaces", "storage", "databases", "imports", "applications",
    "oauth_provider", "environments", "sharing", "audit", "system", "exports", "analytics", "app_platform",
    "org_units", "service_apps", "hosted_sites", "sites", "movie_shop", "licensing", "catalogue_storage",
}


def first_paragraph(obj) -> str:
    # The object's own description only: an undocumented view must not show Django's base-class docstring.
    own = obj.__dict__.get("__doc__") if isinstance(obj, type) else getattr(obj, "__doc__", None)
    doc = inspect.cleandoc(own) if own else ""
    return " ".join(doc.split("\n\n")[0].split())


def walk(patterns, prefix=""):
    for p in patterns:
        if isinstance(p, URLResolver):
            yield from walk(p.url_patterns, prefix + str(p.pattern))
        elif isinstance(p, URLPattern):
            yield prefix + str(p.pattern), p


rows = {}
for path, pattern in walk(get_resolver().url_patterns):
    view = getattr(pattern.callback, "view_class", None) or getattr(pattern.callback, "cls", None)
    func = view or pattern.callback
    module = getattr(func, "__module__", "")
    app = module.split(".")[0]
    if app not in OWN_APPS:
        continue
    methods = [m.upper() for m in ("get", "post", "put", "patch", "delete") if view and hasattr(view, m)]
    rows.setdefault(app, []).append((path, ", ".join(methods) or "-", getattr(func, "__name__", "?"), first_paragraph(func)))

print("# Reference A — the API\n")
print("Every endpoint, generated from the URL configuration and the views' own descriptions. Paths under `api/v1/` "
      "need a signed-in session (or an application's bearer credential where the view allows it); each view checks its "
      "capability itself (see Chapter 4). `<uuid:...>` is an id.\n")
for app in sorted(rows):
    print(f"## {app}\n")
    print("| Path | Methods | View | What it does |")
    print("|---|---|---|---|")
    for path, methods, name, doc in sorted(rows[app]):
        doc = doc.replace("|", "/")[:260]
        print(f"| `/{path}` | {methods} | `{name}` | {doc} |")
    print()

print("=====MODELS=====")
print("# Reference B — the data model\n")
print("Every model of IntraForge's own apps, generated from the models: table, fields (type; null; relation) and the "
      "model's description. Tenant business data (tables people create, installed apps' records) lives in per-"
      "organization PostgreSQL schemas, not here (ADR-0005).\n")
for config in sorted(apps.get_app_configs(), key=lambda c: c.label):
    if config.name.split(".")[0] not in OWN_APPS:
        continue
    models = list(config.get_models())
    if not models:
        continue
    print(f"## {config.label}\n")
    for model in models:
        print(f"### {model.__name__} (`{model._meta.db_table}`)\n")
        doc = first_paragraph(model)
        if doc and not doc.startswith(model.__name__ + "("):
            print(doc + "\n")
        print("| Field | Type | Notes |")
        print("|---|---|---|")
        for f in model._meta.get_fields():
            if f.auto_created and not f.concrete:
                continue
            kind = type(f).__name__
            notes = []
            if getattr(f, "null", False):
                notes.append("null")
            if getattr(f, "unique", False) and not getattr(f, "primary_key", False):
                notes.append("unique")
            if getattr(f, "primary_key", False):
                notes.append("primary key")
            if f.is_relation and f.related_model:
                notes.append(f"→ {f.related_model.__name__}")
            if getattr(f, "choices", None):
                notes.append("choices: " + ", ".join(str(c[0]) for c in f.choices)[:120])
            print(f"| `{f.name}` | {kind} | {'; '.join(notes)} |")
        print()
