# Chapter 9 — Known limits, open items and how to scale — Open items worth knowing

Topic for: software engineers. Source: IntraForge Engineering Handbook, Chapter 9 — Known limits, open items and how to scale.

- **Missing ADR files.** Hosted websites and the app runner cite "ADR-0019" and "ADR-0020" decisions in their code, but
  `docs/architecture/adr/` has 0019 = passkeys and no 0020. Write those two decisions down (as 0025/0026) and fix the
  references.
- **Undocumented code.** Reference C marks with a dash every file that has no description yet (many `models.py`,
  `views.py`, `serializers.py`, `urls.py`). The API reference shows an empty description where a view has no
  docstring. Adding one-line docstrings improves both references and the AI pack automatically.
- **`docs/development/CONTRIBUTING.md`** is still the Phase 0 placeholder; Chapter 8 of this handbook is the current
  practice.
- **Configuration restore** is deliberately manual (the other three backup kinds restore automatically).
- **`.icp` exports** do not include App Platform data; use full backups for that.
- **Languages.** The interface is English only. Arabic, Amharic and Tigrinya for Spare Parts were estimated at about
  three working days for screens plus one for printed documents, and need a decision on fonts and on per-person vs
  shop-wide language.
- **Reports, returns, quotations, stock transfers and tax compliance** are outside the qualified built-in Spare Parts
  (the standalone Spare Parts app has quotations and invoices).
