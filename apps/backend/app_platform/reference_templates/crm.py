"""Phase 8 -- CRM (customer relationship management) reference application
(docs/implementation/APP_PLATFORM_ROADMAP.md,
docs/implementation/APP_PLATFORM_PHASE8.md). A pure, DB-free builder for
the "CRM -- Sales Pipeline" AppTemplate draft: 8 generic models covering
accounts, contacts, leads, campaigns, and the opportunity pipeline, built
entirely from Phases 1-3's existing primitives. No industry-specific
concept is added to `app_platform` itself.

Deliberately excluded, same discipline as Phase 4/School/HR:
- No calculated pipeline totals/forecasts -- no formula/computed-column
  concept exists.
- No enum/status type -- `stage`/`status` fields stay free text.
- No lead-to-opportunity conversion action -- that would be a declarative
  multi-record action, a concept this platform does not have yet.
"""

import uuid

from ._helpers import _field, _model, _relationship


def crm_reference_definition() -> dict:
    ids = {
        key: str(uuid.uuid4())
        for key in (
            "account", "contact", "lead", "campaign",
            "opportunity", "opportunity_line_item", "activity", "note",
        )
    }

    account = _model(
        ids["account"], "account", "Account",
        [
            _field("name", "Name", "text", required=True, unique=True),
            _field("industry", "Industry", "text"),
            _field("website", "Website", "text"),
        ],
    )
    contact = _model(
        ids["contact"], "contact", "Contact",
        [
            _field("first_name", "First Name", "text", required=True),
            _field("last_name", "Last Name", "text", required=True),
            _field("email", "Email", "text"),
            _field("phone", "Phone", "text"),
        ],
    )
    lead = _model(
        ids["lead"], "lead", "Lead",
        [
            _field("name", "Name", "text", required=True),
            _field("email", "Email", "text"),
            _field("phone", "Phone", "text"),
            _field("status", "Status", "text", required=True, default_value="new"),
            _field("source", "Source", "text"),
        ],
    )
    campaign = _model(
        ids["campaign"], "campaign", "Campaign",
        [
            _field("name", "Name", "text", required=True),
            _field("start_date", "Start Date", "date"),
            _field("end_date", "End Date", "date"),
            _field("budget", "Budget", "decimal"),
        ],
    )
    opportunity = _model(
        ids["opportunity"], "opportunity", "Opportunity",
        [
            _field("name", "Name", "text", required=True),
            _field("amount", "Amount", "decimal"),
            _field("stage", "Stage", "text", required=True, default_value="prospecting"),
            _field("close_date", "Close Date", "date"),
        ],
    )
    opportunity_line_item = _model(
        ids["opportunity_line_item"], "opportunity_line_item", "Opportunity Line Item",
        [
            _field("quantity", "Quantity", "integer", required=True),
            _field("unit_price", "Unit Price", "decimal", required=True),
            _field("line_total", "Line Total", "decimal", required=True),
        ],
    )
    activity = _model(
        ids["activity"], "activity", "Activity",
        [
            _field("subject", "Subject", "text", required=True),
            _field("activity_type", "Activity Type", "text"),
            _field("due_date", "Due Date", "date"),
            _field("completed", "Completed", "boolean", default_value=False),
        ],
    )
    note = _model(
        ids["note"], "note", "Note",
        [
            _field("body", "Body", "text", required=True),
            _field("created_at", "Created At", "datetime"),
        ],
    )

    relationships = [
        _relationship("contact_account", "Account", ids["contact"], ids["account"]),
        _relationship("opportunity_account", "Account", ids["opportunity"], ids["account"]),
        _relationship("opportunity_contact", "Contact", ids["opportunity"], ids["contact"]),
        _relationship(
            "opportunity_campaign",
            "Campaign",
            ids["opportunity"],
            ids["campaign"],
            deletion_policy="set_null",
        ),
        _relationship(
            "opportunity_line_item_opportunity",
            "Opportunity",
            ids["opportunity_line_item"],
            ids["opportunity"],
        ),
        _relationship("activity_contact", "Contact", ids["activity"], ids["contact"]),
        _relationship("activity_opportunity", "Opportunity", ids["activity"], ids["opportunity"]),
        _relationship("note_account", "Account", ids["note"], ids["account"]),
        # Native many-to-many: a campaign targets several contacts.
        _relationship(
            "targeted_contacts", "Targeted Contacts", ids["campaign"], ids["contact"], kind="many_to_many"
        ),
    ]

    return {
        "schema_version": 1,
        "models": [
            account, contact, lead, campaign,
            opportunity, opportunity_line_item, activity, note,
        ],
        "relationships": relationships,
    }
