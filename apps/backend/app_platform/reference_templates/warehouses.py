"""Phase 8 -- Warehouses (warehouse / logistics management) reference
application (docs/implementation/APP_PLATFORM_ROADMAP.md,
docs/implementation/APP_PLATFORM_PHASE8.md). A pure, DB-free builder for
the "Warehouses -- Bin-Level Logistics" AppTemplate draft: 10 generic
models covering warehouse/zone/bin structure, bin-level stock, and
inbound/outbound/transfer movement, built entirely from Phases 1-3's
existing primitives, including two distinct relationships from the same
model (`TransferOrder`) to the same target model (`Warehouse`). No
industry-specific concept is added to `app_platform` itself.

Deliberately distinct from Phase 4's "Spare Parts" template: that
template's `Inventory`/`Warehouse` models are a simple, single-level
quantity-per-(part, warehouse) count for an auto-parts sales business.
This template models bin-level warehouse operations generically (zones,
bins, inbound/outbound shipments, inter-warehouse transfers) with no
sales/purchasing concept of its own -- the two do not duplicate each
other's business logic, they cover different depths of the same broad
domain.

Deliberately excluded, same discipline as the other Phase 8 templates:
- No calculated on-hand/available-to-promise quantities beyond the two
  plain counters already on `StockLevel` -- no formula/computed-column
  concept exists.
- No enum/status type -- `status` fields stay free text.
- No cross-request atomicity -- e.g. completing a transfer and updating
  both warehouses' stock stays separate record-CRUD calls.
"""

import uuid

from ._helpers import _field, _model, _relationship


def warehouses_reference_definition() -> dict:
    ids = {
        key: str(uuid.uuid4())
        for key in (
            "warehouse", "zone", "bin_location", "item", "stock_level",
            "inbound_shipment", "inbound_shipment_line",
            "outbound_shipment", "outbound_shipment_line", "transfer_order",
        )
    }

    warehouse = _model(
        ids["warehouse"], "warehouse", "Warehouse",
        [
            _field("name", "Name", "text", required=True),
            _field("code", "Code", "text", required=True, unique=True),
            _field("address", "Address", "text"),
        ],
    )
    zone = _model(
        ids["zone"], "zone", "Zone",
        [
            _field("name", "Name", "text", required=True),
            _field("code", "Code", "text"),
        ],
    )
    bin_location = _model(
        ids["bin_location"], "bin_location", "Bin Location",
        [
            _field("code", "Code", "text", required=True),
            _field("capacity", "Capacity", "integer"),
        ],
    )
    item = _model(
        ids["item"], "item", "Item",
        [
            _field("sku", "SKU", "text", required=True, unique=True),
            _field("name", "Name", "text", required=True),
            _field("unit_of_measure", "Unit of Measure", "text"),
            _field("is_active", "Is Active", "boolean", default_value=True),
        ],
    )
    stock_level = _model(
        ids["stock_level"], "stock_level", "Stock Level",
        [
            _field("quantity_on_hand", "Quantity on Hand", "integer", required=True, default_value=0),
            _field("quantity_reserved", "Quantity Reserved", "integer", default_value=0),
        ],
    )
    inbound_shipment = _model(
        ids["inbound_shipment"], "inbound_shipment", "Inbound Shipment",
        [
            _field("reference_number", "Reference Number", "text", required=True, unique=True),
            _field("expected_date", "Expected Date", "date"),
            _field("status", "Status", "text", required=True, default_value="pending"),
        ],
    )
    inbound_shipment_line = _model(
        ids["inbound_shipment_line"], "inbound_shipment_line", "Inbound Shipment Line",
        [
            _field("quantity_expected", "Quantity Expected", "integer", required=True),
            _field("quantity_received", "Quantity Received", "integer", default_value=0),
        ],
    )
    outbound_shipment = _model(
        ids["outbound_shipment"], "outbound_shipment", "Outbound Shipment",
        [
            _field("reference_number", "Reference Number", "text", required=True, unique=True),
            _field("ship_date", "Ship Date", "date"),
            _field("status", "Status", "text", required=True, default_value="pending"),
        ],
    )
    outbound_shipment_line = _model(
        ids["outbound_shipment_line"], "outbound_shipment_line", "Outbound Shipment Line",
        [_field("quantity", "Quantity", "integer", required=True)],
    )
    transfer_order = _model(
        ids["transfer_order"], "transfer_order", "Transfer Order",
        [
            _field("status", "Status", "text", required=True, default_value="pending"),
            _field("requested_at", "Requested At", "datetime"),
        ],
    )

    stock_level_item_rel = _relationship("stock_level_item", "Item", ids["stock_level"], ids["item"])
    stock_level_bin_location_rel = _relationship(
        "stock_level_bin_location", "Bin Location", ids["stock_level"], ids["bin_location"]
    )
    # One stock row per (Item, Bin Location) -- the same relationship-only
    # composite constraint pattern Phase 4's Inventory model proved.
    stock_level["constraints"] = [
        {
            "key": "item_bin_location_unique",
            "label": "One stock level per Item and Bin Location",
            "field_ids": [],
            "relationship_ids": [stock_level_item_rel["id"], stock_level_bin_location_rel["id"]],
        }
    ]

    relationships = [
        _relationship("zone_warehouse", "Warehouse", ids["zone"], ids["warehouse"]),
        _relationship("bin_location_zone", "Zone", ids["bin_location"], ids["zone"]),
        stock_level_item_rel,
        stock_level_bin_location_rel,
        _relationship("inbound_shipment_warehouse", "Warehouse", ids["inbound_shipment"], ids["warehouse"]),
        _relationship(
            "inbound_shipment_line_shipment", "Inbound Shipment",
            ids["inbound_shipment_line"], ids["inbound_shipment"],
        ),
        _relationship("inbound_shipment_line_item", "Item", ids["inbound_shipment_line"], ids["item"]),
        _relationship("outbound_shipment_warehouse", "Warehouse", ids["outbound_shipment"], ids["warehouse"]),
        _relationship(
            "outbound_shipment_line_shipment", "Outbound Shipment",
            ids["outbound_shipment_line"], ids["outbound_shipment"],
        ),
        _relationship("outbound_shipment_line_item", "Item", ids["outbound_shipment_line"], ids["item"]),
        # Two distinct relationships from the same model to the same
        # target model -- each needs its own globally-unique key.
        _relationship("source_warehouse", "Source Warehouse", ids["transfer_order"], ids["warehouse"]),
        _relationship("destination_warehouse", "Destination Warehouse", ids["transfer_order"], ids["warehouse"]),
    ]

    return {
        "schema_version": 1,
        "models": [
            warehouse, zone, bin_location, item, stock_level,
            inbound_shipment, inbound_shipment_line,
            outbound_shipment, outbound_shipment_line, transfer_order,
        ],
        "relationships": relationships,
    }
