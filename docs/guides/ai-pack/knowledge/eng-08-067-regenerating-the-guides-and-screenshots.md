# Chapter 8 — Working on IntraForge: setup, tests, release — Regenerating the guides and screenshots

Topic for: software engineers. Source: IntraForge Engineering Handbook, Chapter 8 — Working on IntraForge: setup, tests, release.

| Tool | What it does |
|---|---|
| `docs/guides/tools/capture-screens.cjs` | Playwright: signs in to a test copy and saves the web screenshots in `docs/guides/screenshots/web/` |
| `INTRAFORGE_CC_RENDER_UI=<folder>` + the Control Center | Renders every Control Center screen to PNG |
| `docs/guides/tools/gen_reference.py`, `gen_modules.py` | The generated reference parts of this handbook |
| `docs/guides/tools/build_guides.py` | Markdown → HTML → PDF (Microsoft Edge headless, no downloads) |
| `docs/guides/tools/build_ai_pack.py` | Assembles the AnythingLLM knowledge pack |
