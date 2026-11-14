"""Builds the guides: docs/guides/<guide>/*.md (in order) -> one HTML file -> PDF, with the screenshots.

    python docs/guides/tools/build_guides.py            # all guides
    python docs/guides/tools/build_guides.py training   # one

No downloads: a small Markdown converter (headings, paragraphs, lists, tables, code, images, bold/italic/code/links,
notes starting "> ") and Microsoft Edge's own headless "print to PDF". Images are referenced as
![caption](../screenshots/web/03-dashboard.png) in the Markdown.
"""

import html
import pathlib
import re
import shutil
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
GUIDES = {
    "training": "IntraForge — Training Guide",
    "engineering": "IntraForge — Engineering Handbook",
}
EDGE_CANDIDATES = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
]

CSS = """
@page { size: A4; margin: 16mm 14mm 18mm 14mm; }
body { font-family: "Segoe UI", Inter, Arial, sans-serif; color: #0f172a; font-size: 10.5pt; line-height: 1.5; }
h1 { font-size: 22pt; color: #172554; border-bottom: 3px solid #2563eb; padding-bottom: 4px; margin-top: 0; page-break-before: always; }
h1.first, .cover + h1 { page-break-before: auto; }
h2 { font-size: 15pt; color: #1e3a8a; margin-top: 22px; border-bottom: 1px solid #cbd5e1; padding-bottom: 2px; }
h3 { font-size: 12pt; color: #0f172a; margin-top: 16px; }
h4 { font-size: 10.5pt; margin-top: 12px; }
p, li { orphans: 3; widows: 3; }
code { font-family: Consolas, "Cascadia Mono", monospace; font-size: 9pt; background: #f1f5f9; padding: 0 3px; border-radius: 3px; }
pre { background: #0f172a; color: #e2e8f0; padding: 8px 10px; border-radius: 6px; font-size: 8.5pt; white-space: pre-wrap; word-break: break-word; page-break-inside: avoid; }
pre code { background: none; color: inherit; padding: 0; }
table { border-collapse: collapse; width: 100%; margin: 8px 0 12px; font-size: 9pt; page-break-inside: auto; }
th, td { border: 1px solid #cbd5e1; padding: 4px 6px; text-align: left; vertical-align: top; }
th { background: #eff6ff; }
td { overflow-wrap: anywhere; }
tr { page-break-inside: avoid; }
figure { margin: 10px 0 14px; page-break-inside: avoid; text-align: center; }
figure img { max-width: 100%; max-height: 150mm; border: 1px solid #cbd5e1; border-radius: 6px; }
figure.phone img { max-height: 120mm; }
figcaption { font-size: 8.5pt; color: #475569; margin-top: 3px; }
blockquote { margin: 10px 0; padding: 6px 10px; border-left: 4px solid #2563eb; background: #eff6ff; border-radius: 4px; }
blockquote.warn { border-color: #d97706; background: #fffbeb; }
.cover { text-align: center; padding-top: 70mm; page-break-after: always; }
.cover h1 { border: none; font-size: 30pt; page-break-before: auto; }
.cover p { color: #475569; font-size: 12pt; }
.toc { page-break-after: always; }
.toc ol { line-height: 1.8; }
a { color: #1d4ed8; text-decoration: none; }
"""


def inline(text: str) -> str:
    text = html.escape(text, quote=False)
    text = re.sub(r"`([^`]+)`", lambda m: f"<code>{m.group(1)}</code>", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<![*\w])\*([^*\n]+)\*(?![*\w])", r"<em>\1</em>", text)
    text = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", r'<a href="\2">\1</a>', text)
    return text


def convert(md: str, base: pathlib.Path) -> tuple[str, list[str]]:
    out, toc = [], []
    lines = md.replace("\r\n", "\n").split("\n")
    i = 0
    para: list[str] = []

    def flush():
        if para:
            out.append("<p>" + inline(" ".join(para)) + "</p>")
            para.clear()

    while i < len(lines):
        line = lines[i]
        if not line.strip():
            flush(); i += 1; continue
        if line.startswith("```"):
            flush(); code = []; i += 1
            while i < len(lines) and not lines[i].startswith("```"):
                code.append(lines[i]); i += 1
            out.append("<pre><code>" + html.escape("\n".join(code)) + "</code></pre>"); i += 1; continue
        m = re.match(r"^(#{1,4})\s+(.*)$", line)
        if m:
            flush(); level = len(m.group(1)); title = m.group(2).strip()
            anchor = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
            if level == 1:
                toc.append(f'<li><a href="#{anchor}">{inline(title)}</a></li>')
            out.append(f'<h{level} id="{anchor}">{inline(title)}</h{level}>'); i += 1; continue
        m = re.match(r"^!\[([^\]]*)\]\(([^)]+)\)\s*$", line)
        if m:
            flush(); cap, src = m.group(1), m.group(2)
            img = (base / src).resolve()
            cls = ' class="phone"' if "portal" in src else ""
            out.append(f'<figure{cls}><img src="{img.as_uri()}" alt="{html.escape(cap)}"><figcaption>{inline(cap)}</figcaption></figure>')
            i += 1; continue
        if line.startswith("|"):
            flush(); rows = []
            while i < len(lines) and lines[i].startswith("|"):
                rows.append(lines[i]); i += 1
            cells = [[c.strip() for c in r.strip().strip("|").split("|")] for r in rows]
            head, body = cells[0], [r for r in cells[1:] if not all(re.fullmatch(r":?-{2,}:?", c) for c in r)]
            t = "<table><thead><tr>" + "".join(f"<th>{inline(c)}</th>" for c in head) + "</tr></thead><tbody>"
            t += "".join("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in r) + "</tr>" for r in body)
            out.append(t + "</tbody></table>"); continue
        if line.startswith("> "):
            flush(); quote = []
            while i < len(lines) and lines[i].startswith(">"):
                quote.append(lines[i][1:].strip()); i += 1
            text = " ".join(quote)
            cls = ' class="warn"' if text.lower().startswith(("**careful", "**warning", "**important")) else ""
            out.append(f"<blockquote{cls}>{inline(text)}</blockquote>"); continue
        m = re.match(r"^(\s*)([-*]|\d+\.)\s+(.*)$", line)
        if m:
            flush(); ordered = m.group(2)[0].isdigit(); tag = "ol" if ordered else "ul"; items = []
            while i < len(lines):
                mm = re.match(r"^(\s*)([-*]|\d+\.)\s+(.*)$", lines[i])
                if mm:
                    items.append(mm.group(3)); i += 1
                elif lines[i].startswith("  ") and lines[i].strip() and items:
                    items[-1] += " " + lines[i].strip(); i += 1
                else:
                    break
            out.append(f"<{tag}>" + "".join(f"<li>{inline(x)}</li>" for x in items) + f"</{tag}>"); continue
        para.append(line.strip()); i += 1
    flush()
    return "\n".join(out), toc


def build(name: str) -> pathlib.Path:
    folder = ROOT / name
    parts = sorted(folder.glob("*.md"))
    body, toc = [], []
    for part in parts:
        h, t = convert(part.read_text(encoding="utf-8"), folder)
        body.append(h); toc.extend(t)
    title = GUIDES[name]
    version = (ROOT.parents[1] / "VERSION").read_text(encoding="utf-8").strip() if (ROOT.parents[1] / "VERSION").exists() else ""
    page = (f"<!doctype html><html lang='en'><head><meta charset='utf-8'><title>{html.escape(title)}</title>"
            f"<style>{CSS}</style></head><body>"
            f"<div class='cover'><h1>{html.escape(title)}</h1><p>IntraForge Local Edition 1.5.7</p>"
            f"<p>Build. Store. Connect. Privately.</p></div>"
            f"<div class='toc'><h2>Contents</h2><ol>{''.join(toc)}</ol></div>"
            + "\n".join(body) + "</body></html>")
    html_path = ROOT / "out" / f"{name}.html"
    html_path.parent.mkdir(exist_ok=True)
    html_path.write_text(page, encoding="utf-8")
    pdf = ROOT / "out" / f"IntraForge-{name.capitalize()}-Guide.pdf" if name == "training" else ROOT / "out" / "IntraForge-Engineering-Handbook.pdf"
    edge = next((p for p in EDGE_CANDIDATES if pathlib.Path(p).exists()), shutil.which("msedge"))
    # Its own throwaway profile: otherwise a running Edge takes the job over and nothing is printed.
    import tempfile

    # Edge may still hold a file of the profile for a moment after printing: never fail the build over the cleanup.
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as profile:
        subprocess.run([edge, "--headless=new", "--disable-gpu", "--no-first-run", f"--user-data-dir={profile}",
                        "--no-pdf-header-footer", "--allow-file-access-from-files", "--virtual-time-budget=20000",
                        f"--print-to-pdf={pdf}", html_path.as_uri()], check=True, timeout=600)
        # msedge.exe can return before its renderer has finished writing: wait until the file exists and stops growing.
        import time

        size = -1
        for _ in range(240):
            if pdf.exists() and pdf.stat().st_size == size and size > 0:
                break
            size = pdf.stat().st_size if pdf.exists() else -1
            time.sleep(0.5)
    if not pdf.exists():
        raise SystemExit(f"Edge did not write {pdf}")
    return pdf


if __name__ == "__main__":
    for n in (sys.argv[1:] or list(GUIDES)):
        print(build(n))
