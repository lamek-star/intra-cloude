# IntraForge guides

Three deliverables, all built from the Markdown and screenshots in this folder (no downloads needed):

| File | For | What it is |
|---|---|---|
| [`out/IntraForge-Training-Guide.pdf`](out/IntraForge-Training-Guide.pdf) | Shop owners, managers, staff, trainers | Nine lessons with screenshots: signing in, the owner's jobs, files and data, Spare Parts, the Movie Shop and portal, Pay, keeping the shop safe, the internet café website, a training-day plan and troubleshooting |
| [`out/IntraForge-Engineering-Handbook.pdf`](out/IntraForge-Engineering-Handbook.pdf) | Software engineers | Architecture, backend, frontend, security, applications, the shop kit, the other repositories, workflow and limits, plus references generated from the code: every API endpoint, every model and every source file |
| [`ai-pack/`](ai-pack/README.md) | Anyone, through AnythingLLM | The same knowledge as topic cards for an offline AI mentor that shows the matching screenshot — see `ai-pack/README.md` to set it up |

## Folders

| Folder | Contents |
|---|---|
| `training/` | The Training Guide's lessons (Markdown) |
| `engineering/` | The Engineering Handbook's chapters; `90-`/`91-`/`92-reference-*.md` are generated — do not edit by hand |
| `screenshots/web/`, `screenshots/control-center/` | The pictures, taken from a test copy with test data |
| `ai-pack/` | The AnythingLLM pack (its `knowledge/` and `screenshots/` are generated) |
| `tools/` | The scripts that build everything |
| `out/` | The PDFs |

## Rebuilding

From the repository root:

```bash
# 1. Screenshots (optional): from a running test copy, with its test logins
PW_PATH=apps/frontend/node_modules/playwright node docs/guides/tools/capture-screens.cjs docs/guides/screenshots <logins-file>
# 2. Generated references (inside the backend container of a running copy)
docker compose exec -T backend python manage.py shell < docs/guides/tools/gen_reference.py > ref.md   # split at "=====MODELS====="
python docs/guides/tools/gen_modules.py
# 3. PDFs and the AI pack
python docs/guides/tools/build_guides.py
python docs/guides/tools/build_ai_pack.py
```

The screenshots show a test installation (test shop names, fictional customers). They must never show a real shop's
data, keys or passwords.

## Example hosted app

[`examples/hosted-apps/internet-cafe/`](../../examples/hosted-apps/internet-cafe/README.md) — a complete internet café website
that sells the router's Wi-Fi voucher codes for IF Pay: the owner's set-up guide, the code, its tests and the zip builder.
