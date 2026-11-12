"""Reference-application template builders (Phase 4, Phase 8 --
docs/implementation/APP_PLATFORM_ROADMAP.md). Each module in this package
is a pure, DB-free function returning a `DefinitionInput`-shaped dict,
built entirely from `app_platform`'s existing generic primitives -- no
industry-specific concept is ever added to `app_platform` itself.
`REGISTRY` is the single source of truth both `manage.py
seed_spare_parts_reference_app` (Phase 4, unchanged) and `manage.py
seed_reference_app` (Phase 8, generic) publish from."""

from .assets import assets_reference_definition
from .crm import crm_reference_definition
from .documents import documents_reference_definition
from .hr import hr_reference_definition
from .pharmacy import pharmacy_reference_definition
from .procurement import procurement_reference_definition
from .projects import projects_reference_definition
from .rentals import rentals_reference_definition
from .repair_shop import repair_shop_reference_definition
from .school import school_reference_definition
from .spare_parts import spare_parts_reference_definition
from .warehouses import warehouses_reference_definition

REGISTRY = {
    "spare_parts": {
        "label": "Spare Parts -- Inventory & Sales",
        "builder": spare_parts_reference_definition,
    },
    "pharmacy": {
        "label": "Pharmacy -- Medicines, Stock & Sales",
        "builder": pharmacy_reference_definition,
    },
    "school": {
        "label": "School -- Enrollment & Records",
        "builder": school_reference_definition,
    },
    "hr": {
        "label": "HR -- Workforce & Payroll",
        "builder": hr_reference_definition,
    },
    "crm": {
        "label": "CRM -- Sales Pipeline",
        "builder": crm_reference_definition,
    },
    "procurement": {
        "label": "Procurement -- Requisition to Pay",
        "builder": procurement_reference_definition,
    },
    "assets": {
        "label": "Assets -- Lifecycle & Depreciation",
        "builder": assets_reference_definition,
    },
    "projects": {
        "label": "Projects -- Delivery & Time Tracking",
        "builder": projects_reference_definition,
    },
    "documents": {
        "label": "Documents -- Library & Review",
        "builder": documents_reference_definition,
    },
    "warehouses": {
        "label": "Warehouses -- Bin-Level Logistics",
        "builder": warehouses_reference_definition,
    },
    "repair_shop": {
        "label": "Repair Shop -- Job Cards",
        "builder": repair_shop_reference_definition,
    },
    "rentals": {
        "label": "Rentals -- Items & Bookings",
        "builder": rentals_reference_definition,
    },
}

__all__ = [
    "REGISTRY",
    "assets_reference_definition",
    "crm_reference_definition",
    "documents_reference_definition",
    "hr_reference_definition",
    "pharmacy_reference_definition",
    "procurement_reference_definition",
    "rentals_reference_definition",
    "repair_shop_reference_definition",
    "projects_reference_definition",
    "school_reference_definition",
    "spare_parts_reference_definition",
    "warehouses_reference_definition",
]
