"""Pharmacy -- Medicines, Stock & Sales: the Spare Parts reference application (spare_parts.py) in its
pharmacy edition. Same models, relationships, constraints and quantity ledger -- so stock, receiving
and selling run through exactly the qualified engine (ADR-0016, ADR-0017) -- with the medicine facts a
pharmacy needs on the product: generic name, pack, manufacturer, origin, whether a prescription is
required, what it is used for, where it is kept on the shelves, and a reference price from a supplier
catalogue next to the shop's own selling price.

Keys stay those of the reference application ("part", "part_number" ...): the business screens resolve
everything by key, and the pharmacy wording is the frontend's (it sees `generic_name` on the product). No
industry-specific concept is added to `app_platform` itself; this module only produces a definition dict.
"""

from ._helpers import _field
from .spare_parts import spare_parts_reference_definition

# The medicine facts, added to the product ("part"). Prices are plain decimals the shop writes; the
# reference price is a supplier catalogue's (for example in INR), never the shop's selling price
# ("list_price", in the shop's currency).
MEDICINE_FIELDS: tuple[tuple[str, str, str, dict], ...] = (
    ("generic_name", "Generic Name", "text", {}),
    ("pack", "Pack", "text", {}),
    ("manufacturer", "Manufacturer", "text", {}),
    ("country_of_origin", "Country of Origin", "text", {}),
    ("prescription_required", "Prescription Required", "boolean", {"default_value": False}),
    ("used_for", "Used For", "text", {}),
    ("storage_location", "Storage Location", "text", {}),
    ("reference_price", "Reference Price", "decimal", {}),
    ("reference_currency", "Reference Currency", "text", {}),
    # Pictures stay where they are published (links), apart from the shop's own photos, which are attachments.
    ("image_links", "Image Links", "text", {}),
    ("source_url", "Source", "text", {}),
)


def pharmacy_reference_definition() -> dict:
    definition = spare_parts_reference_definition()
    part = next(m for m in definition["models"] if m["key"] == "part")
    part["label"] = "Medicine"
    existing = {f["key"] for f in part["fields"]}
    for key, label, data_type, extra in MEDICINE_FIELDS:
        assert key not in existing, key
        part["fields"].append(_field(key, label, data_type, **extra)[1])
    return definition
