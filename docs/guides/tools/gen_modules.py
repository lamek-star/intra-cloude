"""Generates the handbook's module reference (Reference C) from the code's own module descriptions:
every backend module, frontend library/component and shop-kit script, with the first paragraph of its docstring
or leading comment. Run from the repository root:  python docs/guides/tools/gen_modules.py
"""

import ast
import pathlib
import re

REPO = pathlib.Path(__file__).resolve().parents[3]
OUT = REPO / "docs" / "guides" / "engineering" / "92-reference-modules.md"


def first_para(text: str) -> str:
    return " ".join(text.strip().split("\n\n")[0].split()).replace("|", "/")[:400]


def py_doc(path: pathlib.Path) -> str:
    try:
        return first_para(ast.get_docstring(ast.parse(path.read_text(encoding="utf-8"))) or "")
    except (SyntaxError, UnicodeDecodeError):
        return ""


def comment_doc(path: pathlib.Path) -> str:
    """The leading comment block of a TS/PS1/shell/C# file (//, /* */, #, <# #>)."""
    head = path.read_text(encoding="utf-8", errors="replace")[:4000]
    synopsis = re.search(r"<#.*?\.SYNOPSIS\s*(.*?)(?:\n\s*\.[A-Z]+|#>)", head, re.S)
    if synopsis:  # PowerShell comment-based help
        return first_para(synopsis.group(1))
    lines, started = [], False
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines()[:60]:
        s = raw.strip()
        if not started and (not s or s.startswith(("#!", '"use client"', "'use client'", "#Requires", "Set-StrictMode"))):
            continue
        m = re.match(r"^(//+|#+|\*+|/\*+|<#)\s?(.*)$", s)
        if m and not s.startswith("#region"):
            started = True
            text = m.group(2).rstrip("*/").rstrip("#>").strip()
            if text.startswith((".SYNOPSIS", ".DESCRIPTION")):
                continue
            if not text and lines:
                break
            if text:
                lines.append(text)
        elif started:
            break
        else:
            break
    return first_para(" ".join(lines))


def table(rows):
    out = ["| File | What it is |", "|---|---|"]
    out += [f"| `{name}` | {doc or '—'} |" for name, doc in rows]
    return "\n".join(out) + "\n"


parts = ["# Reference C — the modules\n",
         "Every source file, with the first paragraph of its own description (docstring or leading comment), generated "
         "by `docs/guides/tools/gen_modules.py`. A dash means the file has no description yet — read the code.\n"]

backend = REPO / "apps" / "backend"
parts.append("## Backend apps (`apps/backend/<app>/`)\n")
for app in sorted(p for p in backend.iterdir() if (p / "apps.py").exists()):
    rows = []
    for f in sorted(app.rglob("*.py")):
        rel = f.relative_to(app).as_posix()
        if any(x in rel for x in ("migrations/", "tests/", "__pycache__")) or f.name in ("__init__.py", "apps.py", "admin.py"):
            continue
        rows.append((rel, py_doc(f)))
    if rows:
        parts.append(f"### {app.name}\n\n" + table(rows))

fe = REPO / "apps" / "frontend" / "src"
for title, folder in (("Frontend libraries (`apps/frontend/src/lib/`)", fe / "lib"),
                      ("Frontend components (`apps/frontend/src/components/`)", fe / "components")):
    rows = [(f.relative_to(folder).as_posix(), comment_doc(f)) for f in sorted(folder.rglob("*.ts*"))
            if ".test." not in f.name]
    parts.append(f"## {title}\n\n" + table(rows))

kit = REPO / "scripts" / "shop-kit"
rows = []
for f in sorted(kit.rglob("*")):
    if f.suffix.lower() in (".ps1", ".sh", ".cs", ".cmd") and "tests" not in f.parts and "bin" not in f.parts and "obj" not in f.parts:
        rows.append((f.relative_to(kit).as_posix(), comment_doc(f)))
parts.append("## The shop kit (`scripts/shop-kit/`)\n\n" + table(rows))

OUT.write_text("\n".join(parts), encoding="utf-8")
print(OUT, sum(p.count("\n| `") for p in parts), "files")
