"""Resource limits for portable packages, before decompressing any member.

The format remains unchanged. Full appliance backups use a separate path;
these budgets apply only to uploaded portable packages.
"""

from pathlib import PurePosixPath
from zipfile import ZipFile

from django.conf import settings


class PackageBudgetError(ValueError):
    pass


def validate_archive_budget(archive: ZipFile) -> None:
    members = archive.infolist()
    if len(members) > settings.PORTABLE_MAX_MEMBERS:
        raise PackageBudgetError("package contains too many archive members")
    expanded = 0
    names: set[str] = set()
    for member in members:
        name = member.filename
        path = PurePosixPath(name)
        if (
            not name or "\\" in name or ":" in name or "\x00" in name
            or path.is_absolute() or ".." in path.parts or str(path) != name.rstrip("/")
            or name in names
        ):
            raise PackageBudgetError("package contains an unsafe or duplicate member name")
        names.add(name)
        if member.flag_bits & 1:
            raise PackageBudgetError("ZIP member encryption is unsupported; use package encryption")
        if member.file_size > settings.PORTABLE_MAX_MEMBER_BYTES:
            raise PackageBudgetError("package member exceeds the expanded-size limit")
        if name == "manifest.json" and member.file_size > settings.PORTABLE_MAX_MANIFEST_BYTES:
            raise PackageBudgetError("package manifest exceeds the size limit")
        expanded += member.file_size
        if expanded > settings.PORTABLE_MAX_EXPANDED_BYTES:
            raise PackageBudgetError("package exceeds the total expanded-size limit")
