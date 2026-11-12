"""Rentals -- items and bookings. A pure, DB-free builder for a shop that hires things out (tools, party
equipment, cameras, cars): the items and their daily price, customers, bookings with their dates, deposit and
condition on return, and payments. Built only from app_platform's generic primitives.

Deliberately excluded:
- No overlap check between bookings of one item: the counter checks the calendar (a composite constraint can
forbid two bookings starting the same day for one item, which this template does, but not overlapping ranges).
- No calculated price: the booking's amount is entered.
- status is free text (booked, out, returned, cancelled).
"""

import uuid

from ._helpers import _field, _model, _relationship


def rentals_reference_definition() -> dict:
    ids = {key: str(uuid.uuid4()) for key in ("category", "item", "customer", "booking", "payment")}

    category = _model(
        ids["category"],
        "category",
        "Category",
        [_field("name", "Name", "text", required=True, unique=True)],
    )
    item = _model(
        ids["item"],
        "item",
        "Item",
        [
            _field("name", "Name", "text", required=True),
            _field("code", "Code", "text", required=True, unique=True),
            _field("daily_price", "Price per Day", "decimal", required=True),
            _field("deposit", "Deposit", "decimal"),
            _field("available", "Available for hire", "boolean", default_value=True),
            _field("notes", "Notes", "text"),
        ],
    )
    customer = _model(
        ids["customer"],
        "customer",
        "Customer",
        [
            _field("name", "Name", "text", required=True),
            _field("phone", "Phone", "text", required=True, unique=True),
            _field("id_document", "ID Document", "text"),
        ],
    )
    starts_id, starts = _field("starts_on", "Starts On", "date", required=True)
    booking = _model(
        ids["booking"],
        "booking",
        "Booking",
        [
            (starts_id, starts),
            _field("ends_on", "Ends On", "date", required=True),
            _field("status", "Status", "text", required=True, default_value="booked"),
            _field("amount", "Amount", "decimal"),
            _field("deposit_taken", "Deposit Taken", "decimal"),
            _field("returned_on", "Returned On", "date"),
            _field("condition_on_return", "Condition on Return", "text"),
        ],
    )
    payment = _model(
        ids["payment"],
        "payment",
        "Payment",
        [
            _field("paid_on", "Paid On", "date", required=True),
            _field("amount", "Amount", "decimal", required=True),
            _field("method", "Method", "text", required=True, default_value="cash"),
        ],
    )
    booking_item = _relationship("booking_item", "Item", ids["booking"], ids["item"])
    booking["constraints"] = [
        {
            "key": "item_start_unique",
            "label": "One booking per Item starting on the same day",
            "field_ids": [starts_id],
            "relationship_ids": [booking_item["id"]],
        }
    ]
    return {
        "schema_version": 1,
        "models": [category, item, customer, booking, payment],
        "relationships": [
            _relationship(
                "item_category", "Category", ids["item"], ids["category"], deletion_policy="set_null"
            ),
            booking_item,
            _relationship("booking_customer", "Customer", ids["booking"], ids["customer"]),
            _relationship("payment_booking", "Booking", ids["payment"], ids["booking"]),
        ],
    }
