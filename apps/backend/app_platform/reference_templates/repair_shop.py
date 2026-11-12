"""Repair Shop -- job cards. A pure, DB-free builder for a phone, computer or appliance repair counter:
customers, the devices they bring, a job card per repair (fault, status, estimate, promised date, technician),
the parts and labour on it, and payments. Built only from app_platform's generic primitives; no
repair-specific concept is added to app_platform itself.

Deliberately excluded, the same discipline as the other templates:
- No stock ledger: parts used are recorded on the job, not taken out of an inventory (the Spare Parts
  application does stock).
- No calculated totals: a job's amounts are entered, not derived.
- status is free text (received, diagnosing, waiting for parts, ready, collected).
"""

import uuid

from ._helpers import _field, _model, _relationship


def repair_shop_reference_definition() -> dict:
    ids = {
        key: str(uuid.uuid4()) for key in ("customer", "device", "technician", "job", "job_line", "payment")
    }

    customer = _model(
        ids["customer"],
        "customer",
        "Customer",
        [
            _field("name", "Name", "text", required=True),
            _field("phone", "Phone", "text", required=True, unique=True),
            _field("email", "Email", "text"),
            _field("notes", "Notes", "text"),
        ],
    )
    device = _model(
        ids["device"],
        "device",
        "Device",
        [
            _field("kind", "Kind", "text", required=True),
            _field("brand", "Brand", "text"),
            _field("model", "Model", "text"),
            _field("serial_number", "Serial / IMEI", "text"),
            _field("condition", "Condition when received", "text"),
        ],
    )
    technician = _model(
        ids["technician"],
        "technician",
        "Technician",
        [
            _field("name", "Name", "text", required=True),
            _field("active", "Active", "boolean", default_value=True),
        ],
    )
    job = _model(
        ids["job"],
        "job",
        "Job Card",
        [
            _field("number", "Job Number", "text", required=True, unique=True),
            _field("fault", "Fault reported", "text", required=True),
            _field("diagnosis", "Diagnosis", "text"),
            _field("status", "Status", "text", required=True, default_value="received"),
            _field("received_on", "Received On", "date", required=True),
            _field("promised_on", "Promised On", "date"),
            _field("estimate", "Estimate", "decimal"),
            _field("total", "Total", "decimal"),
            _field("collected_on", "Collected On", "date"),
            _field("warranty_days", "Warranty (days)", "integer", default_value=0),
        ],
    )
    job_line = _model(
        ids["job_line"],
        "job_line",
        "Part or Labour",
        [
            _field("description", "Description", "text", required=True),
            _field("kind", "Kind (part or labour)", "text", required=True, default_value="part"),
            _field("quantity", "Quantity", "integer", required=True, default_value=1),
            _field("unit_price", "Unit Price", "decimal", required=True),
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
            _field("reference", "Reference", "text"),
        ],
    )
    return {
        "schema_version": 1,
        "models": [customer, device, technician, job, job_line, payment],
        "relationships": [
            _relationship("device_customer", "Customer", ids["device"], ids["customer"]),
            _relationship("job_device", "Device", ids["job"], ids["device"]),
            _relationship(
                "job_technician", "Technician", ids["job"], ids["technician"], deletion_policy="set_null"
            ),
            _relationship(
                "job_line_job", "Job Card", ids["job_line"], ids["job"], deletion_policy="restrict"
            ),
            _relationship("payment_job", "Job Card", ids["payment"], ids["job"]),
        ],
    }
