"""Phase 8 -- Projects (project management) reference application
(docs/implementation/APP_PLATFORM_ROADMAP.md,
docs/implementation/APP_PLATFORM_PHASE8.md). A pure, DB-free builder for
the "Projects -- Delivery & Time Tracking" AppTemplate draft: 8 generic
models covering projects, milestones, tasks, assignments, time tracking,
and risk, built entirely from Phases 1-3's existing primitives. No
industry-specific concept is added to `app_platform` itself.

Deliberately excluded, same discipline as the other Phase 8 templates:
- No calculated burn-down/percent-complete fields -- no formula/
  computed-column concept exists.
- No enum/status type -- `status`/`priority`/`severity` stay free text.
- `TaskAssignment` names its assignee as a plain text field, not a
  relationship to an Employee model -- reference-template instances are
  independent installations and cannot reference another template's (HR)
  models.
"""

import uuid

from ._helpers import _field, _model, _relationship


def projects_reference_definition() -> dict:
    ids = {
        key: str(uuid.uuid4())
        for key in (
            "client", "project", "milestone", "task_item",
            "task_assignment", "time_entry", "risk", "tag",
        )
    }

    client = _model(
        ids["client"], "client", "Client",
        [
            _field("name", "Name", "text", required=True),
            _field("contact_email", "Contact Email", "text"),
        ],
    )
    project = _model(
        ids["project"], "project", "Project",
        [
            _field("name", "Name", "text", required=True),
            _field("code", "Code", "text", required=True, unique=True),
            _field("status", "Status", "text", required=True, default_value="planning"),
            _field("start_date", "Start Date", "date"),
            _field("end_date", "End Date", "date"),
            _field("budget", "Budget", "decimal"),
        ],
    )
    milestone = _model(
        ids["milestone"], "milestone", "Milestone",
        [
            _field("name", "Name", "text", required=True),
            _field("due_date", "Due Date", "date"),
            _field("status", "Status", "text", required=True, default_value="pending"),
        ],
    )
    task_item = _model(
        ids["task_item"], "task_item", "Task",
        [
            _field("title", "Title", "text", required=True),
            _field("description", "Description", "text"),
            _field("status", "Status", "text", required=True, default_value="todo"),
            _field("priority", "Priority", "text", required=True, default_value="medium"),
            _field("due_date", "Due Date", "date"),
            _field("estimated_hours", "Estimated Hours", "decimal"),
        ],
    )
    task_assignment = _model(
        ids["task_assignment"], "task_assignment", "Task Assignment",
        [
            _field("assigned_at", "Assigned At", "datetime"),
            _field("role", "Role", "text"),
            _field("assignee_name", "Assignee Name", "text"),
        ],
    )
    time_entry = _model(
        ids["time_entry"], "time_entry", "Time Entry",
        [
            _field("logged_date", "Logged Date", "date"),
            _field("hours", "Hours", "decimal"),
            _field("notes", "Notes", "text"),
        ],
    )
    risk = _model(
        ids["risk"], "risk", "Risk",
        [
            _field("title", "Title", "text", required=True),
            _field("description", "Description", "text"),
            _field("severity", "Severity", "text", required=True, default_value="medium"),
            _field("status", "Status", "text", required=True, default_value="open"),
        ],
    )
    tag = _model(ids["tag"], "tag", "Tag", [_field("name", "Name", "text", required=True, unique=True)])

    relationships = [
        _relationship("project_client", "Client", ids["project"], ids["client"], deletion_policy="set_null"),
        _relationship("milestone_project", "Project", ids["milestone"], ids["project"]),
        _relationship("task_item_project", "Project", ids["task_item"], ids["project"]),
        _relationship(
            "task_item_milestone", "Milestone", ids["task_item"], ids["milestone"], deletion_policy="set_null"
        ),
        _relationship("task_assignment_task", "Task", ids["task_assignment"], ids["task_item"]),
        _relationship("time_entry_task", "Task", ids["time_entry"], ids["task_item"]),
        _relationship("risk_project", "Project", ids["risk"], ids["project"]),
        # Native many-to-many: a project can carry several tags.
        _relationship("tags", "Tags", ids["project"], ids["tag"], kind="many_to_many"),
    ]

    return {
        "schema_version": 1,
        "models": [
            client, project, milestone, task_item,
            task_assignment, time_entry, risk, tag,
        ],
        "relationships": relationships,
    }
