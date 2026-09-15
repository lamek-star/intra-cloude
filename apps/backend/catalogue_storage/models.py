"""
The minimum private catalogue this project actually needs (see the
"Simplify the Toyota/OEM integration" decision this closes —
docs/CATALOGUE_STORAGE.md): OEM part identity, one diagram image shared
by every part drawn on it, and the join between them (callout + optional
hotspot rect). Deliberately NOT a vehicle/EPC clone — no Make/Model/
Generation/Variant hierarchy, no fitment matrix. A part's vehicle
applicability, if ever needed, belongs to a *reference* concept the
spare-parts application already owns, not duplicated here.

Reuses this platform's real object storage (`storage.FileObject`) for a
diagram image once redistribution is actually permitted, and its
existing bearer-token mechanism (`applications`) for the spare-parts
backend to reach this app's endpoints — no new auth mechanism.
"""

import re
import uuid

from django.db import models


def normalize_part_number(value: str) -> str:
    """Strip spaces/dashes, uppercase — the exact rule the spare-parts
    application already uses (domain/models.ts normalizeNumber), kept in
    lockstep on purpose so `15690-65010`, `1569065010`, and
    `15690 65010` are always the same search key on both sides."""
    return re.sub(r"[\s-]", "", value).upper()


class OEMPart(models.Model):
    """Answers "what part is this" — never a selling price, stock level,
    or anything else that answers "what will we sell it for" (that's the
    spare-parts application's own CustomerCatalogueItem, deliberately not
    duplicated here — see the module docstring)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    manufacturer = models.CharField(max_length=100)
    part_number = models.CharField(max_length=100)  # official display format, e.g. "15690-65010"
    normalized_part_number = models.CharField(max_length=100, unique=True, db_index=True)
    description = models.CharField(max_length=500, blank=True)
    # Free-text, as the source provider states them -- "Production
    # 1988-08-1989-08" / "3VZE VZN85,90 HLF ATM +1" -- never parsed into
    # structured fields the source doesn't actually give us. Blank when
    # the provider (or a manually-entered row) doesn't supply one.
    applicability = models.CharField(max_length=300, blank=True)
    fitment_notes = models.CharField(max_length=300, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["part_number"]

    def save(self, *args, **kwargs):
        if not self.normalized_part_number:
            self.normalized_part_number = normalize_part_number(self.part_number)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.manufacturer} {self.part_number}"


class Diagram(models.Model):
    class LicenseStatus(models.TextChoices):
        # No local copy exists -- only the source's own URL + metadata is
        # kept. This is the only status a Diagram may have unless a real
        # redistribution permission has been separately confirmed for
        # its provider (never inferred, never defaulted to permissive).
        EXTERNAL_REFERENCE_ONLY = "EXTERNAL_REFERENCE_ONLY", "External reference only"
        # A real image file exists in this platform's own object storage
        # (`file` below is set) -- only reachable by an import path that
        # itself checked and recorded that permission; nothing in this
        # app sets this status on its own.
        LOCALLY_STORED = "LOCALLY_STORED", "Locally stored"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    provider = models.CharField(max_length=100)  # e.g. "toyota-epc"
    provider_diagram_id = models.CharField(max_length=200)  # the provider's own figure/diagram code
    diagram_code = models.CharField(max_length=200, blank=True)  # human-facing label, may equal provider_diagram_id
    # Set only once real local storage permission is confirmed for this
    # provider -- see LicenseStatus and docs/CATALOGUE_STORAGE.md
    # "Licensing". SET_NULL (not CASCADE): deleting the underlying
    # storage.FileObject must not silently delete catalogue/provenance
    # data -- it should surface as a missing image on an otherwise intact
    # record.
    file = models.ForeignKey(
        "storage.FileObject", on_delete=models.SET_NULL, related_name="+", null=True, blank=True
    )
    source_image_url = models.URLField(max_length=1000, blank=True)
    license_status = models.CharField(
        max_length=32, choices=LicenseStatus.choices, default=LicenseStatus.EXTERNAL_REFERENCE_ONLY
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["provider", "provider_diagram_id"], name="unique_diagram_per_provider"
            ),
        ]
        ordering = ["provider", "diagram_code"]

    def __str__(self):
        return f"{self.provider}/{self.diagram_code or self.provider_diagram_id}"


class DiagramPart(models.Model):
    """One diagram can show many parts; one part can appear on more than
    one diagram (a different production run's exploded view, for
    instance) -- this is a genuine many-to-many, not a FK on either side.
    `x`/`y`/`width`/`height` are the provider's own real hotspot
    rectangle when it supplies one; left null otherwise -- never
    fabricated (see docs/CATALOGUE_STORAGE.md "Image highlighting")."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    diagram = models.ForeignKey(Diagram, on_delete=models.CASCADE, related_name="diagram_parts")
    part = models.ForeignKey(OEMPart, on_delete=models.CASCADE, related_name="diagram_parts")
    callout = models.CharField(max_length=50, blank=True)
    x = models.FloatField(null=True, blank=True)
    y = models.FloatField(null=True, blank=True)
    width = models.FloatField(null=True, blank=True)
    height = models.FloatField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["diagram", "part"], name="unique_part_per_diagram"),
        ]
        ordering = ["diagram", "callout"]

    def __str__(self):
        return f"{self.part} @ {self.diagram} (callout {self.callout or '—'})"
