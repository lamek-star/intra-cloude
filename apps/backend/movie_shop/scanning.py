"""What the media agent may tell IntraForge, checked here whatever the agent did (ADR-0022 decision 5): drive
reports, library paths and scanned titles. Nothing here trusts a value because it came from our own agent."""

import re

from rest_framework.exceptions import ValidationError

VIDEO_EXTENSIONS = (".mp4", ".mkv", ".avi", ".mov", ".m4v", ".wmv", ".ts", ".webm")
MAX_TITLES_PER_BATCH = 1000
MAX_DRIVES = 26
MAX_FOLDERS_PER_DRIVE = 200

# A Windows folder: a drive letter and an absolute path ("D:\\Movies"), or a share ("\\\\nas\\Movies"). No
# device paths (\\?\, \\.\), no traversal, no control characters.
_WINDOWS_PATH = re.compile(
    r"^(?:[A-Za-z]:\\|\\\\[^\\/:*?\"<>|\x00-\x1f]+\\[^\\/:*?\"<>|\x00-\x1f]+)[^/:*?\"<>|\x00-\x1f]*$"
)
_BAD_SEGMENT = re.compile(r"(^|\\)\.\.?(\\|$)")


def clean_text(value, field: str, *, max_length: int, required: bool = True) -> str:
    text = str(value or "").strip()
    text = re.sub(r"[\x00-\x1f\x7f]", "", text)
    if required and not text:
        raise ValidationError({field: "This is required."})
    if len(text) > max_length:
        raise ValidationError({field: f"Up to {max_length} characters."})
    return text


def clean_windows_path(value, field: str = "path") -> str:
    path = clean_text(value, field, max_length=260)
    if path.startswith(("\\\\?\\", "\\\\.\\")) or not _WINDOWS_PATH.match(path) or _BAD_SEGMENT.search(path):
        raise ValidationError(
            {field: "A folder on this PC, such as D:\\Movies, or a share such as \\\\nas\\Movies."}
        )
    return path.rstrip("\\") if len(path) > 3 else path


def clean_relative_path(value, field: str = "relative_path") -> str:
    path = clean_text(value, field, max_length=400).replace("/", "\\")
    if path.startswith("\\") or ":" in path or _BAD_SEGMENT.search(path) or re.search(r'[*?"<>|]', path):
        raise ValidationError({field: "A path inside the library folder."})
    return path


def clean_bytes(value, field: str) -> int | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value < 0 or value > 2**62:
        raise ValidationError({field: "A size in bytes."})
    return value


def clean_drive_report(data) -> dict:
    """The agent's view of the PC: drives (letter or share, label, kind, sizes) and their top folders."""
    drives_in = data.get("drives") if isinstance(data, dict) else None
    if not isinstance(drives_in, list) or len(drives_in) > MAX_DRIVES:
        raise ValidationError({"drives": f"A list of up to {MAX_DRIVES} drives."})
    drives = []
    for i, d in enumerate(drives_in):
        if not isinstance(d, dict):
            raise ValidationError({"drives": "Each drive is an object."})
        kind = d.get("kind")
        if kind not in ("fixed", "removable", "network"):
            raise ValidationError({f"drives[{i}].kind": "fixed, removable or network."})
        folders = d.get("folders") or []
        if not isinstance(folders, list):
            raise ValidationError({f"drives[{i}].folders": "A list of folders."})
        drives.append(
            {
                "root": clean_windows_path(d.get("root"), f"drives[{i}].root"),
                "label": clean_text(d.get("label"), f"drives[{i}].label", max_length=80, required=False),
                "kind": kind,
                "total_bytes": clean_bytes(d.get("total_bytes"), f"drives[{i}].total_bytes"),
                "free_bytes": clean_bytes(d.get("free_bytes"), f"drives[{i}].free_bytes"),
                "folders": [
                    clean_windows_path(f, f"drives[{i}].folders") for f in folders[:MAX_FOLDERS_PER_DRIVE]
                ],
            }
        )
    agent = clean_text(data.get("agent_version"), "agent_version", max_length=40, required=False)
    computer = clean_text(data.get("computer"), "computer", max_length=80, required=False)
    return {"drives": drives, "agent_version": agent, "computer": computer}


def clean_title(item, index: int) -> dict:
    if not isinstance(item, dict):
        raise ValidationError({f"titles[{index}]": "Each title is an object."})
    kind = item.get("kind", "movie")
    if kind not in ("movie", "series"):
        raise ValidationError({f"titles[{index}].kind": "movie or series."})
    year = item.get("year")
    if year is not None and (isinstance(year, bool) or not isinstance(year, int) or not 1880 <= year <= 2100):
        raise ValidationError({f"titles[{index}].year": "A year such as 2025."})
    episodes = item.get("episodes", 1)
    if isinstance(episodes, bool) or not isinstance(episodes, int) or not 1 <= episodes <= 10000:
        raise ValidationError({f"titles[{index}].episodes": "How many video files, 1 or more."})
    return {
        "relative_path": clean_relative_path(item.get("relative_path"), f"titles[{index}].relative_path"),
        "category": clean_text(item.get("category"), f"titles[{index}].category", max_length=120),
        "title": clean_text(item.get("title"), f"titles[{index}].title", max_length=200),
        "year": year,
        "kind": kind,
        "size_bytes": clean_bytes(item.get("size_bytes"), f"titles[{index}].size_bytes") or 0,
        "episodes": episodes,
        "cover_fingerprint": clean_text(
            item.get("cover_fingerprint"), f"titles[{index}].cover_fingerprint", max_length=64, required=False
        ),
    }
