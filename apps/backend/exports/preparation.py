"""Repeatable external preparation, before any restore publication locks.

The immutable package plus RestoreJob UUID is the resource map. Only
server-derived UUIDs enter physical storage keys or tenant schema names.
"""

import uuid
import zipfile
from dataclasses import dataclass, field

from django.core.files.base import ContentFile

from storage.services import PreparedUpload, UploadTooLarge, prepare_upload


@dataclass
class RestorePlan:
    operation_id: uuid.UUID
    databases: dict[tuple[int, int, int], uuid.UUID] = field(default_factory=dict)
    files: dict[tuple[int, int, int, int], PreparedUpload | None] = field(default_factory=dict)


def prepare_restore(zf: zipfile.ZipFile, manifest: dict, operation_id: uuid.UUID) -> RestorePlan:
    plan = RestorePlan(operation_id)
    for wi, workspace in enumerate(manifest["organization"].get("workspaces", [])):
        for pi, project in enumerate(workspace.get("projects", [])):
            for di, _ in enumerate(project.get("tenant_databases", [])):
                plan.databases[wi, pi, di] = uuid.uuid5(operation_id, f"database:{wi}:{pi}:{di}")
            for bi, bucket in enumerate(project.get("buckets", [])):
                for fi, entry in enumerate(bucket["files"]):
                    file_id = uuid.uuid5(operation_id, f"file:{wi}:{pi}:{bi}:{fi}")
                    content = ContentFile(zf.read(entry["content_ref"]), name=entry["original_filename"])
                    try:
                        prepared = prepare_upload(
                            uploaded_file=content,
                            file_id=file_id,
                            object_key=f"restore-files/{operation_id}/{file_id}",
                        )
                    except UploadTooLarge:
                        prepared = None  # same explicit report warning as ordinary restore
                    plan.files[wi, pi, bi, fi] = prepared
    return plan
