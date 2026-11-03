"""Phase 8 -- Assets (fixed-asset management) reference application
(docs/implementation/APP_PLATFORM_ROADMAP.md,
docs/implementation/APP_PLATFORM_PHASE8.md). A pure, DB-free builder for
the "Assets -- Lifecycle & Depreciation" AppTemplate draft: 8 generic
models covering acquisition, assignment, maintenance, depreciation, and
disposal, built entirely from Phases 1-3/6-7's existing primitives,
including two independent `org_unit_reference` fields (an asset's owning
unit, and an assignment's target unit -- deliberately not an Employee
relationship, since reference-template instances are independent
installations and cannot reference another template's HR models). No
industry-specific concept is added to `app_platform` itself.

Deliberately excluded, same discipline as the other Phase 8 templates:
- No calculated depreciation (straight-line/declining-balance formulas)
  -- `DepreciationSchedule` rows are caller-computed facts, not derived.
- No enum/status type -- `status` stays free text.
"""

import uuid

from ._helpers import _field, _model, _relationship


def assets_reference_definition() -> dict:
    ids = {
        key: str(uuid.uuid4())
        for key in (
            "asset_category", "location", "vendor", "asset",
            "asset_assignment", "maintenance_record", "depreciation_schedule", "disposal",
        )
    }

    asset_category = _model(
        ids["asset_category"], "asset_category", "Asset Category",
        [
            _field("name", "Name", "text", required=True),
            _field("code", "Code", "text", required=True, unique=True),
        ],
    )
    location = _model(
        ids["location"], "location", "Location",
        [
            _field("name", "Name", "text", required=True),
            _field("code", "Code", "text", required=True, unique=True),
        ],
    )
    vendor = _model(
        ids["vendor"], "vendor", "Vendor",
        [
            _field("name", "Name", "text", required=True),
            _field("contact_email", "Contact Email", "text"),
        ],
    )
    asset = _model(
        ids["asset"], "asset", "Asset",
        [
            _field("name", "Name", "text", required=True),
            _field("asset_tag", "Asset Tag", "text", required=True, unique=True),
            _field("serial_number", "Serial Number", "text"),
            _field("purchase_date", "Purchase Date", "date"),
            _field("purchase_cost", "Purchase Cost", "decimal"),
            _field("status", "Status", "text", required=True, default_value="in_service"),
            _field("org_unit", "Owning Unit", "org_unit_reference"),
        ],
    )
    asset_assignment = _model(
        ids["asset_assignment"], "asset_assignment", "Asset Assignment",
        [
            _field("assigned_at", "Assigned At", "datetime"),
            _field("returned_at", "Returned At", "datetime"),
            _field("notes", "Notes", "text"),
            _field("assigned_to_unit", "Assigned To Unit", "org_unit_reference"),
        ],
    )
    maintenance_record = _model(
        ids["maintenance_record"], "maintenance_record", "Maintenance Record",
        [
            _field("performed_at", "Performed At", "date"),
            _field("description", "Description", "text"),
            _field("cost", "Cost", "decimal"),
        ],
    )
    period_date_id, period_date_field = _field("period_date", "Period Date", "date", required=True)
    depreciation_schedule = _model(
        ids["depreciation_schedule"], "depreciation_schedule", "Depreciation Schedule",
        [
            (period_date_id, period_date_field),
            _field("depreciation_amount", "Depreciation Amount", "decimal"),
            _field("book_value", "Book Value", "decimal"),
        ],
    )
    disposal = _model(
        ids["disposal"], "disposal", "Disposal",
        [
            _field("disposed_at", "Disposed At", "date"),
            _field("method", "Method", "text"),
            _field("proceeds", "Proceeds", "decimal"),
        ],
    )

    depreciation_schedule_asset_rel = _relationship(
        "depreciation_schedule_asset", "Asset", ids["depreciation_schedule"], ids["asset"]
    )
    # One depreciation entry per (Asset, Period Date) -- a composite
    # constraint mixing a scalar field and a relationship, the same shape
    # HR's PayrollRecord constraint uses.
    depreciation_schedule["constraints"] = [
        {
            "key": "asset_period_unique",
            "label": "One depreciation entry per Asset and Period Date",
            "field_ids": [period_date_id],
            "relationship_ids": [depreciation_schedule_asset_rel["id"]],
        }
    ]

    relationships = [
        _relationship("asset_category", "Category", ids["asset"], ids["asset_category"]),
        _relationship("asset_location", "Location", ids["asset"], ids["location"]),
        _relationship("asset_vendor", "Vendor", ids["asset"], ids["vendor"], deletion_policy="set_null"),
        _relationship("asset_assignment_asset", "Asset", ids["asset_assignment"], ids["asset"]),
        _relationship("maintenance_record_asset", "Asset", ids["maintenance_record"], ids["asset"]),
        depreciation_schedule_asset_rel,
        _relationship("disposal_asset", "Asset", ids["disposal"], ids["asset"]),
    ]

    return {
        "schema_version": 1,
        "models": [
            asset_category, location, vendor, asset,
            asset_assignment, maintenance_record, depreciation_schedule, disposal,
        ],
        "relationships": relationships,
    }
