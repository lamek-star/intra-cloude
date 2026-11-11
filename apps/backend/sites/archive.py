"""
Checks an uploaded website zip before anything is stored (ADR-0019 decision 3). Nothing here trusts the zip:
names, types, sizes and counts are all validated, and the result is a plan of exactly which entries become
which site paths. Reading an entry afterwards is bounded by its declared size (zipfile stops at
`file_size`).
"""

from __future__ import annotations

import json
import posixpath
import re
import stat
import zipfile
from dataclasses import dataclass, field

from django.conf import settings

# Content type by extension. Anything not listed is not a website file (Phase 1 serves static sites only).
CONTENT_TYPES: dict[str, str] = {
    "html": "text/html; charset=utf-8",
    "htm": "text/html; charset=utf-8",
    "css": "text/css; charset=utf-8",
    "js": "text/javascript; charset=utf-8",
    "mjs": "text/javascript; charset=utf-8",
    "json": "application/json",
    "map": "application/json",
    "webmanifest": "application/manifest+json",
    "txt": "text/plain; charset=utf-8",
    "md": "text/plain; charset=utf-8",
    "csv": "text/csv; charset=utf-8",
    "xml": "application/xml",
    "svg": "image/svg+xml",
    "png": "image/png",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "gif": "image/gif",
    "webp": "image/webp",
    "avif": "image/avif",
    "bmp": "image/bmp",
    "ico": "image/x-icon",
    "woff": "font/woff",
    "woff2": "font/woff2",
    "ttf": "font/ttf",
    "otf": "font/otf",
    "eot": "application/vnd.ms-fontobject",
    "mp4": "video/mp4",
    "webm": "video/webm",
    "ogg": "audio/ogg",
    "mp3": "audio/mpeg",
    "wav": "audio/wav",
    "m4a": "audio/mp4",
    "vtt": "text/vtt; charset=utf-8",
    "pdf": "application/pdf",
}

# Code that would run on a server: named in the refusal so the uploader knows why.
SERVER_CODE = {
    "php",
    "phtml",
    "py",
    "rb",
    "pl",
    "cgi",
    "asp",
    "aspx",
    "jsp",
    "sh",
    "bat",
    "cmd",
    "ps1",
    "exe",
    "dll",
    "jar",
    "war",
}

# Operating-system clutter that zip tools add; skipped quietly.
_CLUTTER = {"__MACOSX", "Thumbs.db", "desktop.ini"}
_SEGMENT = re.compile(r"^[^\x00-\x1f\x7f\\:*?\"<>|]+$")


class SiteArchiveError(ValueError):
    pass


@dataclass
class PlannedFile:
    entry: zipfile.ZipInfo
    path: str
    size: int
    content_type: str


@dataclass
class ArchivePlan:
    files: list[PlannedFile] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    # Set for a Node.js server app (intraforge.json): {"runtime": "node", "entry": "<start file>"}.
    manifest: dict | None = None

    @property
    def total_bytes(self) -> int:
        return sum(f.size for f in self.files)


def _extension(path: str) -> str:
    name = posixpath.basename(path)
    return name.rsplit(".", 1)[1].lower() if "." in name else ""


def _clean_name(raw: str) -> list[str]:
    if "\\" in raw:
        raise SiteArchiveError(f"'{raw}' uses a backslash in its name; the zip was not made correctly.")
    if raw.startswith("/") or re.match(r"^[A-Za-z]:", raw):
        raise SiteArchiveError(f"'{raw}' is an absolute path; a website zip holds relative paths only.")
    segments = [s for s in raw.split("/") if s not in ("", ".")]
    for segment in segments:
        if segment == ".." or not _SEGMENT.match(segment):
            raise SiteArchiveError(f"'{raw}' is not a safe file name.")
    return segments


MANIFEST = "intraforge.json"
# A Node app may carry any file its code needs, but never a Windows program.
WINDOWS_PROGRAMS = {"exe", "dll", "bat", "cmd", "ps1", "com", "msi", "scr", "vbs"}
_ENTRY = re.compile(r"^[A-Za-z0-9._/-]+\.(js|mjs|cjs)$")


def _read_manifest(archive: zipfile.ZipFile, entry: zipfile.ZipInfo, paths: set[str]) -> dict:
    """intraforge.json: {"runtime": "node", "entry": "server.js"}. Nothing else is read from it -- in
    particular no command: the app is always started as `node <entry>`."""
    if entry.file_size > 4096:
        raise SiteArchiveError("intraforge.json is too large; it holds only the runtime and the entry file.")
    try:
        data = json.loads(archive.read(entry).decode("utf-8"))
    except (ValueError, UnicodeDecodeError) as exc:
        raise SiteArchiveError("intraforge.json is not valid JSON.") from exc
    if not isinstance(data, dict) or data.get("runtime") != "node":
        raise SiteArchiveError(
            'intraforge.json must say "runtime": "node" (Node.js is the supported runtime).'
        )
    entry_file = data.get("entry")
    if not isinstance(entry_file, str) or not _ENTRY.match(entry_file) or ".." in entry_file.split("/"):
        raise SiteArchiveError('intraforge.json needs "entry": the app\'s start file, e.g. "server.js".')
    if entry_file not in paths:
        raise SiteArchiveError(f"The start file '{entry_file}' named in intraforge.json is not in the zip.")
    return {"runtime": "node", "entry": entry_file}


def plan_archive(fileobj) -> tuple[zipfile.ZipFile, ArchivePlan]:
    """Opens and checks the zip. Returns the open archive and the plan; raises SiteArchiveError with a
    sentence the uploader can act on. A zip with intraforge.json at its top is a Node.js server app
    (ADR-0020); any other zip is a static website (ADR-0019)."""
    try:
        archive = zipfile.ZipFile(fileobj)
    except (zipfile.BadZipFile, OSError) as exc:
        raise SiteArchiveError("This is not a zip file.") from exc

    entries = archive.infolist()
    if len(entries) > settings.SITES_MAX_APP_FILES * 2:
        raise SiteArchiveError(f"The zip holds more than {settings.SITES_MAX_APP_FILES} files.")

    kept: list[tuple[zipfile.ZipInfo, list[str]]] = []
    skipped_hidden = 0
    for entry in entries:
        segments = _clean_name(entry.filename)
        if entry.is_dir() or not segments:
            continue
        mode = entry.external_attr >> 16
        if mode and stat.S_ISLNK(mode):
            raise SiteArchiveError(f"'{entry.filename}' is a link to another file; links are not allowed.")
        if entry.flag_bits & 0x1:
            raise SiteArchiveError("The zip is password-protected; upload it without a password.")
        if any(s in _CLUTTER or s.startswith(".") for s in segments):
            skipped_hidden += 1
            continue
        kept.append((entry, segments))
    if not kept:
        raise SiteArchiveError("The zip contains no website files.")

    plan = ArchivePlan()
    if skipped_hidden:
        plan.notes.append(
            f"{skipped_hidden} hidden or system file(s) were left out (for example .htaccess or .env)."
        )

    # Everything inside one top folder (public_html/, dist/, build/, my-app/) with nothing above it: remove
    # that folder.
    tops = {segments[0] for _, segments in kept}
    if len(tops) == 1 and all(len(segments) > 1 for _, segments in kept):
        top = tops.pop()
        kept = [(entry, segments[1:]) for entry, segments in kept]
        plan.notes.append(f"The top folder '{top}/' was removed so the site starts at its own top.")

    paths = {"/".join(segments) for _, segments in kept}
    manifest_entry = next((e for e, segments in kept if segments == [MANIFEST]), None)
    if manifest_entry is not None:
        plan.manifest = _read_manifest(archive, manifest_entry, paths)
        max_files, max_total = settings.SITES_MAX_APP_FILES, settings.SITES_MAX_APP_TOTAL_BYTES
        programs = sorted({_extension(s[-1]) for _, s in kept if _extension(s[-1]) in WINDOWS_PROGRAMS})
        if programs:
            kinds = ", ".join(f".{e}" for e in programs)
            raise SiteArchiveError(f"The app contains Windows programs ({kinds}); they cannot run here.")
    else:
        max_files, max_total = settings.SITES_MAX_FILES, settings.SITES_MAX_TOTAL_BYTES
        refused_server = sorted({_extension(s[-1]) for _, s in kept if _extension(s[-1]) in SERVER_CODE})
        if refused_server:
            kinds = ", ".join(f".{e}" for e in refused_server)
            raise SiteArchiveError(
                f"The zip contains server code ({kinds}). A website zip holds files that run in the browser "
                "(HTML, CSS, JavaScript, images). A Node.js app needs an intraforge.json at its top; other "
                "server languages are not supported."
            )
        refused_other = sorted(
            {_extension(s[-1]) or "(no extension)" for _, s in kept if _extension(s[-1]) not in CONTENT_TYPES}
        )
        if refused_other:
            kinds = ", ".join(e if e.startswith("(") else f".{e}" for e in refused_other)
            raise SiteArchiveError(f"The zip contains files that are not website files: {kinds}.")

    if len(kept) > max_files:
        raise SiteArchiveError(f"The zip holds more than {max_files} files.")

    seen: set[str] = set()
    total = 0
    for entry, segments in kept:
        path = "/".join(segments)
        if path.lower() in seen:
            raise SiteArchiveError(f"'{path}' appears twice in the zip.")
        seen.add(path.lower())
        if entry.file_size > settings.SITES_MAX_FILE_BYTES:
            raise SiteArchiveError(
                f"'{path}' is larger than {settings.SITES_MAX_FILE_BYTES // (1024 * 1024)} MB."
            )
        if entry.file_size > 1024 * 1024 and entry.file_size > entry.compress_size * settings.SITES_MAX_RATIO:
            raise SiteArchiveError(f"'{path}' unpacks to far more than its packed size; the zip was refused.")
        total += entry.file_size
        if total > max_total:
            raise SiteArchiveError(f"The website unpacks to more than {max_total // (1024 * 1024)} MB.")
        content_type = CONTENT_TYPES.get(_extension(path), "application/octet-stream")
        plan.files.append(PlannedFile(entry, path, entry.file_size, content_type))

    if plan.manifest is None and "index.html" not in paths:
        raise SiteArchiveError(
            "The website has no index.html at its top level (the page a visitor opens first). "
            "A Node.js app needs an intraforge.json there instead."
        )
    plan.files.sort(key=lambda f: f.path)
    return archive, plan
