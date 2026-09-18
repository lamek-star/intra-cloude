"""Phase 8 -- Procurement reference application
(docs/implementation/APP_PLATFORM_ROADMAP.md,
docs/implementation/APP_PLATFORM_PHASE8.md). A pure, DB-free builder for
the "Procurement -- Requisition to Pay" AppTemplate draft: 9 generic
models covering requisitions, purchase orders, receiving, vendor
invoicing, and approval, built entirely from Phases 1-3's existing
primitives. No industry-specific concept is added to `app_platform`
itself.

Deliberately excluded, same discipline as the other Phase 8 templates:
- No workflow-engine wiring (Phase 5) for `status`/`decision` -- these
  stay free text, matching every other reference template's `status`
  field; wiring a real WorkflowDefinition onto a reference template is
  feature-composition work for a future pass, not part of this phase's
  own exit bar (breadth of domain coverage, not workflow depth).
- No calculated totals -- `line_total`/`total_amount`/`amount` are plain
  decimals the caller computes and writes.
- No cross-request atomicity -- e.g. a goods receipt updating stock
  elsewhere stays a separate record-CRUD call (and this template has no
  inventory concept of its own -- see the Warehouses template for that).
"""

import uuid

from ._helpers import _field, _model, _relationship


def procurement_reference_definition() -> dict:
    ids = {
        key: str(uuid.uuid4())
        for key in (
            "vendor", "purchase_requisition", "requisition_line", "purchase_order",
            "purchase_order_line", "goods_receipt", "goods_receipt_line",
            "vendor_invoice", "approval",
        )
    }

    vendor = _model(
        ids["vendor"], "vendor", "Vendor",
        [
            _field("name", "Name", "text", required=True),
            _field("contact_email", "Contact Email", "text"),
            _field("contact_phone", "Contact Phone", "text"),
            _field("is_active", "Is Active", "boolean", default_value=True),
        ],
    )
    purchase_requisition = _model(
        ids["purchase_requisition"], "purchase_requisition", "Purchase Requisition",
        [
            _field("requested_by", "Requested By", "text"),
            _field("status", "Status", "text", required=True, default_value="draft"),
            _field("needed_by", "Needed By", "date"),
        ],
    )
    requisition_line = _model(
        ids["requisition_line"], "requisition_line", "Requisition Line",
        [
            _field("item_description", "Item Description", "text", required=True),
            _field("quantity", "Quantity", "integer", required=True),
            _field("estimated_cost", "Estimated Cost", "decimal"),
        ],
    )
    purchase_order = _model(
        ids["purchase_order"], "purchase_order", "Purchase Order",
        [
            _field("status", "Status", "text", required=True, default_value="draft"),
            _field("order_date", "Order Date", "date"),
            _field("expected_date", "Expected Date", "date"),
            _field("total_amount", "Total Amount", "decimal", default_value="0"),
        ],
    )
    purchase_order_line = _model(
        ids["purchase_order_line"], "purchase_order_line", "Purchase Order Line",
        [
            _field("quantity", "Quantity", "integer", required=True),
            _field("unit_cost", "Unit Cost", "decimal", required=True),
            _field("line_total", "Line Total", "decimal", required=True),
        ],
    )
    goods_receipt = _model(
        ids["goods_receipt"], "goods_receipt", "Goods Receipt",
        [
            _field("receipt_number", "Receipt Number", "text", required=True, unique=True),
            _field("received_date", "Received Date", "date"),
        ],
    )
    goods_receipt_line = _model(
        ids["goods_receipt_line"], "goods_receipt_line", "Goods Receipt Line",
        [_field("quantity_received", "Quantity Received", "integer", required=True)],
    )
    vendor_invoice = _model(
        ids["vendor_invoice"], "vendor_invoice", "Vendor Invoice",
        [
            _field("invoice_number", "Invoice Number", "text", required=True, unique=True),
            _field("invoice_date", "Invoice Date", "date"),
            _field("amount", "Amount", "decimal"),
            _field("status", "Status", "text", required=True, default_value="unpaid"),
        ],
    )
    approval = _model(
        ids["approval"], "approval", "Approval",
        [
            _field("approver_name", "Approver Name", "text"),
            _field("decision", "Decision", "text", required=True, default_value="pending"),
            _field("decided_at", "Decided At", "datetime"),
        ],
    )

    goods_receipt_line_goods_receipt_rel = _relationship(
        "goods_receipt_line_goods_receipt", "Goods Receipt", ids["goods_receipt_line"], ids["goods_receipt"]
    )
    goods_receipt_line_purchase_order_line_rel = _relationship(
        "goods_receipt_line_purchase_order_line", "Purchase Order Line",
        ids["goods_receipt_line"], ids["purchase_order_line"],
    )
    # One receipt line per (Goods Receipt, Purchase Order Line) -- the
    # same relationship-only composite constraint pattern Phase 4's
    # Inventory model already proved.
    goods_receipt_line["constraints"] = [
        {
            "key": "receipt_order_line_unique",
            "label": "One receipt line per Goods Receipt and Purchase Order Line",
            "field_ids": [],
            "relationship_ids": [
                goods_receipt_line_goods_receipt_rel["id"],
                goods_receipt_line_purchase_order_line_rel["id"],
            ],
        }
    ]

    relationships = [
        _relationship(
            "requisition_line_requisition",
            "Purchase Requisition",
            ids["requisition_line"],
            ids["purchase_requisition"],
        ),
        _relationship("purchase_order_vendor", "Vendor", ids["purchase_order"], ids["vendor"]),
        # Nullable: a purchase order can be raised directly, without a
        # prior requisition.
        _relationship(
            "purchase_order_requisition",
            "Purchase Requisition",
            ids["purchase_order"],
            ids["purchase_requisition"],
            deletion_policy="set_null",
        ),
        _relationship(
            "purchase_order_line_purchase_order",
            "Purchase Order",
            ids["purchase_order_line"],
            ids["purchase_order"],
        ),
        _relationship(
            "purchase_order_line_requisition_line",
            "Requisition Line",
            ids["purchase_order_line"],
            ids["requisition_line"],
            deletion_policy="set_null",
        ),
        _relationship(
            "goods_receipt_purchase_order", "Purchase Order", ids["goods_receipt"], ids["purchase_order"]
        ),
        goods_receipt_line_goods_receipt_rel,
        goods_receipt_line_purchase_order_line_rel,
        _relationship(
            "vendor_invoice_purchase_order", "Purchase Order", ids["vendor_invoice"], ids["purchase_order"]
        ),
        _relationship("vendor_invoice_vendor", "Vendor", ids["vendor_invoice"], ids["vendor"]),
        _relationship(
            "approval_requisition", "Purchase Requisition", ids["approval"], ids["purchase_requisition"]
        ),
    ]

    return {
        "schema_version": 1,
        "models": [
            vendor, purchase_requisition, requisition_line, purchase_order,
            purchase_order_line, goods_receipt, goods_receipt_line,
            vendor_invoice, approval,
        ],
        "relationships": relationships,
    }
