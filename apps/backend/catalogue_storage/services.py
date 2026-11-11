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


MAX_FIGURE_ROWS = 2000


class FigureError(ValueError):
    pass


def _validated_groups(figure_data) -> list[dict]:
    if not isinstance(figure_data, dict) or not isinstance(figure_data.get("groups"), list):
        raise FigureError('figure_data must be an object with a "groups" list.')
    groups = figure_data["groups"]
    total = 0
    for group in groups:
        if not isinstance(group, dict) or not isinstance(group.get("rows", []), list):
            raise FigureError("Every group must be an object with a rows list.")
        for row in group.get("rows", []):
            if not isinstance(row, dict) or not str(row.get("part_number", "")).strip():
                raise FigureError("Every row needs a part_number.")
            total += 1
    if total > MAX_FIGURE_ROWS:
        raise FigureError(f"A figure may carry at most {MAX_FIGURE_ROWS} rows.")
    return groups


def _applicability(row: dict) -> str:
    start, end = row.get("valid_from"), row.get("valid_to")
    if not start and not end:
        return ""
    return f"Production {start or '?'}–{end or 'current'}"


@transaction.atomic
def import_figure(
    *,
    provider: str,
    provider_diagram_id: str,
    diagram_code: str,
    source_image_url: str,
    manufacturer: str,
    figure_data: dict,
) -> ImportResult:
    """Persists one whole figure -- its display snapshot on the Diagram and
    every distinct part number it lists as an OEMPart + DiagramPart link
    (callout and hotspot rect from the group each row sits under) -- so
    every number shown on the figure is independently searchable offline.
    Bounded to the one figure the caller fetched; never a crawl. Rows
    that repeat a number (production/fitment variants) share one OEMPart;
    the first row seen supplies its description/applicability."""
    groups = _validated_groups(figure_data)
    result = ImportResult()
    seen: set[str] = set()
    for group in groups:
        rect = group.get("rect") or {}
        for row in group.get("rows", []):
            normalized = normalize_part_number(str(row["part_number"]))
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            import_row(
                ImportRow(
                    part_number=str(row["part_number"]),
                    description=str(row.get("description", ""))[:500],
                    manufacturer=manufacturer,
                    diagram_code=diagram_code,
                    provider=provider,
                    provider_diagram_id=provider_diagram_id,
                    callout=str(group.get("callout", ""))[:50],
                    source_image_url=source_image_url,
                    applicability=_applicability(row),
                    fitment_notes="",
                    x=rect.get("x"), y=rect.get("y"), width=rect.get("width"), height=rect.get("height"),
                ),
                result,
            )
    diagram, _ = Diagram.objects.get_or_create(
        provider=provider,
        provider_diagram_id=provider_diagram_id,
        defaults={
            "diagram_code": diagram_code or provider_diagram_id,
            "source_image_url": source_image_url,
            "license_status": Diagram.LicenseStatus.EXTERNAL_REFERENCE_ONLY,
        },
    )
    diagram.figure_data = figure_data
    fields = ["figure_data", "updated_at"]
    if source_image_url and not diagram.source_image_url:
        # A drawing attached from local files exists before any part does;
        # remember where the source published it once we learn that.
        diagram.source_image_url = source_image_url
        fields.append("source_image_url")
    diagram.save(update_fields=fields)
    return result


CATALOGUE_ORG_NAME = "Harmoney Spare Parts — Catalogue Ops"


def ensure_catalogue_bucket():
    """The bucket holding locally stored catalogue drawings, created on first
    use inside the catalogue integration's own organization (the one the
    seed migration creates) -- never in a customer's workspace."""
    from organizations.models import Organization
    from storage.models import Bucket
    from workspaces.models import Project, Workspace

    org = Organization.objects.filter(name=CATALOGUE_ORG_NAME).first()
    if org is None:
        raise LookupError(f'Organization "{CATALOGUE_ORG_NAME}" does not exist (run migrations).')
    owner = org.created_by
    workspace, _ = Workspace.objects.get_or_create(
        organization=org, name="Catalogue", defaults={"created_by": owner}
    )
    project, _ = Project.objects.get_or_create(
        workspace=workspace, name="Catalogue drawings", defaults={"created_by": owner}
    )
    bucket, _ = Bucket.objects.get_or_create(
        project=project, name="catalogue-drawings", defaults={"created_by": owner}
    )
    return bucket
