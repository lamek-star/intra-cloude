"""Phase 4 -- Inventory and Sales reference application
(docs/implementation/APP_PLATFORM_ROADMAP.md, docs/implementation/
APP_PLATFORM_PHASE4.md). A pure, DB-free builder for the "Spare Parts --
Inventory & Sales" AppTemplate draft: 13 generic models covering inventory,
purchasing, and sales, built entirely from Phases 1-3's existing primitives
(scalar fields, many_to_one/many_to_many relationships, composite unique
constraints spanning fields and/or relationships -- the capability closed
alongside this phase). No industry-specific concept is added to
`app_platform` itself; this module only produces a `DefinitionInput`-shaped
dict, exactly like the `sample()`/`composite_sample()` fixtures the test
suite already uses.

Deliberately excluded, per docs/SPARE_PARTS_INTEGRATION_READINESS.md:
- No `CataloguePart`/`CompanyProduct` split -- that's what the separately
  shipped `catalogue_storage` app is for; duplicating it here would pad
  the template with a second, redundant catalogue concept.
- No calculated/derived fields -- `line_total`/`total_amount`/`amount_due`
  are plain decimals the caller computes and writes; the platform has no
  formula/computed-column concept.
- No enum/status type -- `status` fields stay free text.
- No cross-request atomicity -- e.g. a stock receipt updating Inventory is
  left as separate record-CRUD calls; no declarative multi-record action
  concept exists yet.
"""

import uuid


def _field(key, label, data_type, **kwargs):
    field_id = str(uuid.uuid4())
    return field_id, {"id": field_id, "key": key, "label": label, "data_type": data_type, **kwargs}


def _model(model_id, key, label, fields, constraints=None):
    return {
        "id": model_id,
        "key": key,
        "label": label,
        "fields": [field for _id, field in fields],
        "constraints": constraints or [],
    }


def _relationship(key, label, source_model, target_model, *, kind="many_to_one", deletion_policy="restrict"):
    return {
        "id": str(uuid.uuid4()),
        "key": key,
        "label": label,
        "source_model": source_model,
        "target_model": target_model,
        "kind": kind,
        "deletion_policy": deletion_policy,
    }


def spare_parts_reference_definition() -> dict:
    """Build the full "Spare Parts -- Inventory & Sales" draft. Every
    model/field id is pre-generated so relationships and constraints can
    reference them directly, the same pattern `composite_sample()`
    (app_platform/tests/test_composite_constraints.py) uses for a single
    model."""
    part_id, vehicle_id, warehouse_id = str(uuid.uuid4()), str(uuid.uuid4()), str(uuid.uuid4())
    part_number_id, inventory_id, stock_movement_id = str(uuid.uuid4()), str(uuid.uuid4()), str(uuid.uuid4())
    supplier_id, purchase_order_id, purchase_order_line_id = (
        str(uuid.uuid4()),
        str(uuid.uuid4()),
        str(uuid.uuid4()),
    )
    customer_id, sales_order_id, sales_order_line_id, invoice_id = (
        str(uuid.uuid4()),
        str(uuid.uuid4()),
        str(uuid.uuid4()),
        str(uuid.uuid4()),
    )

    part = _model(
        part_id,
        "part",
        "Part",
        [
            _field("name", "Name", "text", required=True),
            _field("description", "Description", "text"),
            _field("unit_of_measure", "Unit of Measure", "text"),
            _field("is_active", "Is Active", "boolean", default_value=True),
            _field("standard_cost", "Standard Cost", "decimal"),
            _field("list_price", "List Price", "decimal"),
        ],
    )

    number_id, number_field = _field("number", "Number", "text", required=True, unique=True)
    source_id, source_field = _field("source", "Source", "text")
    part_number = _model(
        part_number_id,
        "part_number",
        "Part Number",
        [(number_id, number_field), (source_id, source_field)],
    )

    vehicle = _model(
        vehicle_id,
        "vehicle",
        "Vehicle",
        [
            _field("make", "Make", "text", required=True),
            _field("model", "Model", "text", required=True),
            _field("year", "Year", "integer"),
        ],
    )

    warehouse = _model(
        warehouse_id,
        "warehouse",
        "Warehouse",
        [
            _field("name", "Name", "text", required=True),
            _field("code", "Code", "text", required=True, unique=True),
        ],
    )

    inventory = _model(
        inventory_id,
        "inventory",
        "Inventory",
        [
            _field("quantity_on_hand", "Quantity on Hand", "integer", required=True, default_value=0),
            _field("quantity_reserved", "Quantity Reserved", "integer", default_value=0),
        ],
    )

    stock_movement = _model(
        stock_movement_id,
        "stock_movement",
        "Stock Movement",
        [
            _field("quantity_delta", "Quantity Delta", "integer", required=True),
            _field("movement_type", "Movement Type", "text", required=True),
            _field("reference", "Reference", "text"),
            _field("occurred_at", "Occurred At", "datetime"),
        ],
    )

    supplier = _model(
        supplier_id,
        "supplier",
        "Supplier",
        [
            _field("name", "Name", "text", required=True),
            _field("contact_email", "Contact Email", "text"),
            _field("contact_phone", "Contact Phone", "text"),
        ],
    )

    purchase_order = _model(
        purchase_order_id,
        "purchase_order",
        "Purchase Order",
        [
            _field("status", "Status", "text", required=True, default_value="draft"),
            _field("order_date", "Order Date", "date"),
            _field("expected_date", "Expected Date", "date"),
            _field("total_amount", "Total Amount", "decimal", default_value="0"),
        ],
    )

    purchase_order_line = _model(
        purchase_order_line_id,
        "purchase_order_line",
        "Purchase Order Line",
        [
            _field("quantity", "Quantity", "integer", required=True),
            _field("unit_cost", "Unit Cost", "decimal", required=True),
            _field("line_total", "Line Total", "decimal", required=True),
        ],
    )

    customer = _model(
        customer_id,
        "customer",
        "Customer",
        [
            _field("name", "Name", "text", required=True),
            _field("contact_email", "Contact Email", "text"),
            _field("contact_phone", "Contact Phone", "text"),
        ],
    )

    sales_order = _model(
        sales_order_id,
        "sales_order",
        "Sales Order",
        [
            _field("status", "Status", "text", required=True, default_value="draft"),
            _field("order_date", "Order Date", "date"),
            _field("total_amount", "Total Amount", "decimal", default_value="0"),
        ],
    )

    sales_order_line = _model(
        sales_order_line_id,
        "sales_order_line",
        "Sales Order Line",
        [
            _field("quantity", "Quantity", "integer", required=True),
            _field("unit_price", "Unit Price", "decimal", required=True),
            _field("line_total", "Line Total", "decimal", required=True),
        ],
    )

    invoice = _model(
        invoice_id,
        "invoice",
        "Invoice",
        [
            _field("invoice_number", "Invoice Number", "text", required=True, unique=True),
            _field("invoice_date", "Invoice Date", "date"),
            _field("amount_due", "Amount Due", "decimal", default_value="0"),
            _field("status", "Status", "text", required=True, default_value="unpaid"),
        ],
    )

    inventory_part_rel = _relationship("part", "Part", inventory_id, part_id)
    inventory_warehouse_rel = _relationship("warehouse", "Warehouse", inventory_id, warehouse_id)
    # The exact capability closed alongside this phase: a composite UNIQUE
    # constraint whose members are both relationships, not scalar fields --
    # one Inventory record per (Part, Warehouse).
    inventory["constraints"] = [
        {
            "key": "part_warehouse_unique",
            "label": "One inventory record per Part and Warehouse",
            "field_ids": [],
            "relationship_ids": [inventory_part_rel["id"], inventory_warehouse_rel["id"]],
        }
    ]

    # Relationship keys are unique per INSTANCE, not per owning model
    # (RelationshipDefinition's own `(instance, key)` constraint) -- several
    # models here reference the same target (Part, Warehouse, Sales Order),
    # so those keys are prefixed by owning model to stay globally distinct.
    relationships = [
        _relationship("part_number_part", "Part", part_number_id, part_id),
        # Self-referencing: covers both cross-reference and supersession
        # without a second join model (docs/SPARE_PARTS_INTEGRATION_
        # READINESS.md's own suggestion). Nullable/set_null -- a part
        # number that superseded something being deleted should not be
        # blocked, just orphaned.
        _relationship(
            "supersedes", "Supersedes", part_number_id, part_number_id, deletion_policy="set_null"
        ),
        inventory_part_rel,
        inventory_warehouse_rel,
        _relationship("stock_movement_part", "Part", stock_movement_id, part_id),
        _relationship("stock_movement_warehouse", "Warehouse", stock_movement_id, warehouse_id),
        _relationship("supplier", "Supplier", purchase_order_id, supplier_id),
        _relationship("purchase_order", "Purchase Order", purchase_order_line_id, purchase_order_id),
        _relationship("purchase_order_line_part", "Part", purchase_order_line_id, part_id),
        _relationship("customer", "Customer", sales_order_id, customer_id),
        _relationship("sales_order_line_sales_order", "Sales Order", sales_order_line_id, sales_order_id),
        _relationship("sales_order_line_part", "Part", sales_order_line_id, part_id),
        _relationship("invoice_sales_order", "Sales Order", invoice_id, sales_order_id),
        # Native many-to-many: real join table, already supported
        # end-to-end including the frontend multi-select picker.
        _relationship("compatible_vehicles", "Compatible Vehicles", part_id, vehicle_id, kind="many_to_many"),
    ]

    return {
        "schema_version": 1,
        "models": [
            part,
            part_number,
            vehicle,
            warehouse,
            inventory,
            stock_movement,
            supplier,
            purchase_order,
            purchase_order_line,
            customer,
            sales_order,
            sales_order_line,
            invoice,
        ],
        "relationships": relationships,
    }
