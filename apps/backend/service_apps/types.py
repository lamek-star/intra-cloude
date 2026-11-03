"""What IntraForge knows about each service application type.

The configuration schema mirrors the application's own validation (Spare Parts
`src/server/standalone/config.ts`): IntraForge is the store of record for it, so
it validates before storing, and the application validates again before use.
"""

import re
from dataclasses import dataclass, field

from rest_framework.exceptions import ValidationError

from permissions.catalog import PERMISSIONS


@dataclass(frozen=True)
class AppType:
    key: str
    product_name: str
    description: str
    # Capabilities this application is gated by (all default-deny).
    capabilities: tuple[str, ...]
    # The capability that lets someone open it at all.
    open_capability: str
    settings_capability: str
    defaults: dict = field(default_factory=dict)


_TEXT_FIELDS = {
    "shopName": 200,
    "address": 2000,
    "phone": 100,
    "email": 254,
    "taxRegistration": 100,
    "quotationTerms": 2000,
    "invoiceNotes": 2000,
}
_INT_FIELDS = {
    # name: (minimum, maximum)
    "defaultTaxBp": (0, 100000),
    "quotationValidityDays": (0, 3650),
    "invoiceDueDays": (0, 3650),
}
_CURRENCY = re.compile(r"^[A-Z]{3}$")

SPARE_PARTS = AppType(
    key="spare_parts",
    product_name="Spare Parts",
    description=(
        "Reference catalogue, your own products and stock, customers and suppliers, "
        "enquiry to quotation to order to invoice to payment, and reports."
    ),
    capabilities=tuple(p for p in PERMISSIONS if p.startswith("spareparts.")),
    open_capability="spareparts.view",
    settings_capability="spareparts.settings.manage",
    defaults={
        "shopName": "",
        "address": "",
        "phone": "",
        "email": "",
        "taxRegistration": "",
        "currency": "AED",
        "defaultTaxBp": 500,
        "quotationValidityDays": 14,
        "invoiceDueDays": 30,
        "quotationTerms": "",
        "invoiceNotes": "",
    },
)

APP_TYPES = {SPARE_PARTS.key: SPARE_PARTS}


def get_type(key: str) -> AppType:
    return APP_TYPES[key]


def clean_config(app_type: AppType, current: dict, patch: dict) -> dict:
    """Returns the full configuration after applying `patch`. Unknown keys are refused rather
    than stored, so the configuration can never become a place to hide arbitrary data."""
    if not isinstance(patch, dict):
        raise ValidationError({"config": "Expected an object."})
    unknown = sorted(set(patch) - set(app_type.defaults))
    if unknown:
        raise ValidationError({"config": f"Unknown setting(s): {', '.join(unknown)}."})
    merged = {**app_type.defaults, **(current or {})}
    for key, value in patch.items():
        if key in _TEXT_FIELDS:
            if not isinstance(value, str):
                raise ValidationError({key: "Must be text."})
            value = value.strip()
            if len(value) > _TEXT_FIELDS[key]:
                raise ValidationError({key: f"At most {_TEXT_FIELDS[key]} characters."})
        elif key in _INT_FIELDS:
            low, high = _INT_FIELDS[key]
            if isinstance(value, bool) or not isinstance(value, int) or not low <= value <= high:
                raise ValidationError({key: f"Must be a whole number from {low} to {high}."})
        elif key == "currency":
            if not isinstance(value, str) or not _CURRENCY.match(value.strip().upper()):
                raise ValidationError({key: "Must be a 3-letter currency code."})
            value = value.strip().upper()
        merged[key] = value
    return merged


def public_config(app_type: AppType, config: dict) -> dict:
    """The configuration as the application and the settings page see it (defaults filled in)."""
    return {**app_type.defaults, **{k: v for k, v in (config or {}).items() if k in app_type.defaults}}
