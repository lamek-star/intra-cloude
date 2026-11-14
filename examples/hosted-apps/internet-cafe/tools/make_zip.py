"""Packs the website into the zip IntraForge's Websites page takes: intraforge.json, server.js, lib/ and public/.
Tests and tools stay out. Run from this folder:  python tools/make_zip.py   ->  dist/internet-cafe-site.zip
"""

import pathlib
import zipfile

HERE = pathlib.Path(__file__).resolve().parents[1]
OUT = HERE / "dist" / "internet-cafe-site.zip"
INCLUDE = ["intraforge.json", "server.js", "package.json", "lib", "public"]

OUT.parent.mkdir(exist_ok=True)
with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as archive:
    for name in INCLUDE:
        path = HERE / name
        files = [path] if path.is_file() else sorted(p for p in path.rglob("*") if p.is_file())
        for f in files:
            archive.write(f, f.relative_to(HERE).as_posix())
print(OUT, OUT.stat().st_size, "bytes")
