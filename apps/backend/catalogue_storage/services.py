"""
Business logic shared by the seed migration, the CSV importer management
command, and (read-only) the API views — one place that knows how to
normalize, deduplicate, and link, so all three stay consistent.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field

from django.db import transaction

from .models import Diagram, DiagramPart, OEMPart, normalize_part_number


def search_part(query: str) -> OEMPart | None:
    """Exact match on the normalized part number (`15690-65010`,
    `1569065010`, `15690 65010` all resolve to the same part) first;
    falls back to a case-insensitive substring match on `description`
    (searching "by name") if nothing matched as a part number. Returns
    the single best match — first exact, then first description hit —
    not a result list; a query genuinely ambiguous by name alone still
    resolves to one part, matching this feature's own "quick" scope."""
    query = query.strip()
    if not query:
        return None
    normalized = normalize_part_number(query)
    exact = OEMPart.objects.filter(normalized_part_number=normalized).first()
    if exact:
        return exact
    return OEMPart.objects.filter(description__icontains=query).first()


@dataclass
class ImportRow:
    part_number: str
    description: str
    manufacturer: str
    diagram_code: str
    provider: str
    provider_diagram_id: str
    callout: str = ""
    source_image_url: str = ""
    applicability: str = ""
    fitment_notes: str = ""
    x: float | None = None
    y: float | None = None
    width: float | None = None
    height: float | None = None


@dataclass
class ImportResult:
    parts_created: int = 0
    parts_updated: int = 0
    diagrams_created: int = 0
    diagrams_reused: int = 0
    links_created: int = 0
    links_updated: int = 0
    errors: list[str] = field(default_factory=list)


def checksum_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


@transaction.atomic
def import_row(row: ImportRow, result: ImportResult) -> None:
    """Idempotent: re-running the same row updates in place rather than
    duplicating (dedup key: normalized_part_number for OEMPart,
    (provider, provider_diagram_id) for Diagram, (diagram, part) for
    DiagramPart — all three are real unique constraints, not just
    application-level discipline)."""
    normalized = normalize_part_number(row.part_number)
    part, part_created = OEMPart.objects.update_or_create(
        normalized_part_number=normalized,
        defaults={
            "manufacturer": row.manufacturer,
            "part_number": row.part_number,
            "description": row.description,
            "applicability": row.applicability,
            "fitment_notes": row.fitment_notes,
        },
    )
    if part_created:
        result.parts_created += 1
    else:
        result.parts_updated += 1

    diagram, diagram_created = Diagram.objects.get_or_create(
        provider=row.provider,
        provider_diagram_id=row.provider_diagram_id,
        defaults={
            "diagram_code": row.diagram_code or row.provider_diagram_id,
            "source_image_url": row.source_image_url,
            # NEVER LOCALLY_STORED from a plain row import -- only
            # attach_local_image (below) may promote a diagram to that
            # status, and only after actually writing bytes to object
            # storage under a confirmed-permitted import.
            "license_status": Diagram.LicenseStatus.EXTERNAL_REFERENCE_ONLY,
        },
    )
    if diagram_created:
        result.diagrams_created += 1
    else:
        result.diagrams_reused += 1

    _, link_created = DiagramPart.objects.update_or_create(
        diagram=diagram,
        part=part,
        defaults={"callout": row.callout, "x": row.x, "y": row.y, "width": row.width, "height": row.height},
    )
    if link_created:
        result.links_created += 1
    else:
        result.links_updated += 1


def attach_local_image(*, diagram: Diagram, file_object, actor) -> None:
    """Called only by an import path that has already confirmed local
    storage is permitted for `diagram.provider` (see
    docs/CATALOGUE_STORAGE.md "Licensing") and has already written the
    bytes via storage.services.upload_file -- this function only records
    the resulting FileObject on the Diagram row."""
    diagram.file = file_object
    diagram.license_status = Diagram.LicenseStatus.LOCALLY_STORED
    diagram.save(update_fields=["file", "license_status", "updated_at"])
