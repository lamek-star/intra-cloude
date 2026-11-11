"""Phase 8 -- HR (human resources) reference application
(docs/implementation/APP_PLATFORM_ROADMAP.md,
docs/implementation/APP_PLATFORM_PHASE8.md). A pure, DB-free builder for
the "HR -- Workforce & Payroll" AppTemplate draft: 9 generic models
covering organizational structure, leave, time, payroll, and performance,
built entirely from Phases 1-3/6-7's existing primitives -- including a
self-referencing manager relationship and an `org_unit_reference` field
(Phase 7 Step 1), the same pattern proven there. No industry-specific
concept is added to `app_platform` itself.

Deliberately excluded, same discipline as Phase 4/School:
- No calculated fields (e.g. tenure, leave balance) -- no formula/
  computed-column concept exists.
- No enum/status type -- `status` fields stay free text.
- No cross-request atomicity -- e.g. approving leave and updating a
  timesheet stays separate record-CRUD calls.
"""

import uuid

from ._helpers import _field, _model, _relationship


def hr_reference_definition() -> dict:
    ids = {
        key: str(uuid.uuid4())
        for key in (
            "department", "position", "employee", "leave_type", "leave_request",
            "timesheet", "payroll_record", "performance_review", "onboarding_task",
        )
    }

    department = _model(
        ids["department"], "department", "Department",
        [
            _field("name", "Name", "text", required=True),
            _field("code", "Code", "text", required=True, unique=True),
        ],
    )
    position = _model(
        ids["position"], "position", "Position",
        [
            _field("title", "Title", "text", required=True),
            _field("code", "Code", "text", required=True, unique=True),
        ],
    )
    employee = _model(
        ids["employee"], "employee", "Employee",
        [
            _field("first_name", "First Name", "text", required=True),
            _field("last_name", "Last Name", "text", required=True),
            _field("email", "Email", "text", required=True, unique=True),
            _field("hire_date", "Hire Date", "date"),
            _field("is_active", "Is Active", "boolean", default_value=True),
            # Phase 6/7: ties an Employee to this organization's own
            # hierarchy, without inventing a second "org unit" concept.
            _field("org_unit", "Organizational Unit", "org_unit_reference"),
        ],
    )
    leave_type = _model(
        ids["leave_type"], "leave_type", "Leave Type",
        [
            _field("name", "Name", "text", required=True),
            _field("code", "Code", "text", required=True, unique=True),
        ],
    )
    leave_request = _model(
        ids["leave_request"], "leave_request", "Leave Request",
        [
            _field("start_date", "Start Date", "date", required=True),
            _field("end_date", "End Date", "date", required=True),
            _field("status", "Status", "text", required=True, default_value="pending"),
            _field("reason", "Reason", "text"),
        ],
    )
    timesheet = _model(
        ids["timesheet"], "timesheet", "Timesheet",
        [
            _field("period_start", "Period Start", "date"),
            _field("period_end", "Period End", "date"),
            _field("total_hours", "Total Hours", "decimal"),
            _field("status", "Status", "text", required=True, default_value="draft"),
        ],
    )
    pay_period_start_id, pay_period_start_field = _field("pay_period_start", "Pay Period Start", "date")
    payroll_record = _model(
        ids["payroll_record"], "payroll_record", "Payroll Record",
        [
            (pay_period_start_id, pay_period_start_field),
            _field("pay_period_end", "Pay Period End", "date"),
            _field("gross_pay", "Gross Pay", "decimal"),
            _field("net_pay", "Net Pay", "decimal"),
            _field("status", "Status", "text", required=True, default_value="pending"),
        ],
    )
    performance_review = _model(
        ids["performance_review"], "performance_review", "Performance Review",
        [
            _field("review_date", "Review Date", "date"),
            _field("rating", "Rating", "integer"),
            _field("comments", "Comments", "text"),
        ],
    )
    onboarding_task = _model(
        ids["onboarding_task"], "onboarding_task", "Onboarding Task",
        [
            _field("title", "Title", "text", required=True),
            _field("due_date", "Due Date", "date"),
            _field("completed", "Completed", "boolean", default_value=False),
        ],
    )

    payroll_record_employee_rel = _relationship(
        "payroll_record_employee", "Employee", ids["payroll_record"], ids["employee"]
    )
    # One payroll record per (Employee, Pay Period Start) -- a composite
    # constraint mixing a scalar field and a relationship, the other half
    # of the capability Phase 4 closed generically (that template's own
    # Inventory constraint is relationship-only).
    payroll_record["constraints"] = [
        {
            "key": "employee_pay_period_unique",
            "label": "One payroll record per Employee and Pay Period Start",
            "field_ids": [pay_period_start_id],
            "relationship_ids": [payroll_record_employee_rel["id"]],
        }
    ]

    relationships = [
        _relationship("position_department", "Department", ids["position"], ids["department"]),
        _relationship("employee_position", "Position", ids["employee"], ids["position"]),
        # Self-referencing, nullable on delete -- removing a manager should
        # not be blocked by their reports, just orphan the reference (the
        # same pattern Spare Parts' PartNumber.supersedes already proved).
        _relationship(
            "manager", "Manager", ids["employee"], ids["employee"], deletion_policy="set_null"
        ),
        _relationship("leave_request_employee", "Employee", ids["leave_request"], ids["employee"]),
        _relationship("leave_request_leave_type", "Leave Type", ids["leave_request"], ids["leave_type"]),
        _relationship("timesheet_employee", "Employee", ids["timesheet"], ids["employee"]),
        payroll_record_employee_rel,
        _relationship("performance_review_employee", "Employee", ids["performance_review"], ids["employee"]),
        _relationship(
            "reviewer", "Reviewer", ids["performance_review"], ids["employee"], deletion_policy="set_null"
        ),
        _relationship("onboarding_task_employee", "Employee", ids["onboarding_task"], ids["employee"]),
    ]

    return {
        "schema_version": 1,
        "models": [
            department, position, employee, leave_type, leave_request,
            timesheet, payroll_record, performance_review, onboarding_task,
        ],
        "relationships": relationships,
    }
