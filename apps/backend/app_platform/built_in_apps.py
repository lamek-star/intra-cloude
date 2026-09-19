"""Built-in business applications: the customer-facing catalog and one-click install.

Until now, getting a ready-made application meant creating a template, publishing
it, installing it, then planning, reserving and provisioning a runtime -- a
developer workflow. A shop owner must not run API commands or edit JSON (Local
Edition §27). `install()` does that whole sequence in one call, through the same
services (so every capability check is unchanged), and `listing()` is what the
production gallery shows.

Release status is real, not marketing. A built-in application appears to
customers only when its status is QUALIFIED; PARTIALLY_QUALIFIED and EXPERIMENTAL
entries exist for development and demos and are shown, clearly labelled, only when
`SHOW_UNQUALIFIED_BUILT_IN_APPS` is on. Flip an entry to QUALIFIED only with the
evidence the Local Edition qualification requires (main workflow through the
normal UI, relationships, constraints, permissions, restart, template upgrade,
backup and restore of it), and record where that evidence lives in `evidence`.

Definitions get deterministic ids (`stabilize_ids`). The reference builders
generate random UUIDs on every call; template upgrades diff an installed
instance against a newer version by those ids, so a random id per build would
make every future upgrade look like "everything removed, everything added".
"""

import json
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import StrEnum
from typing import cast

from django.conf import settings
from django.db import transaction
from rest_framework import serializers
from rest_framework.exceptions import APIException, NotFound

from . import instances, provisioning, templates
from .definitions import validate_definition
from .models import AppInstance, AppTemplate
from .reference_templates import REGISTRY
from .runtime_plan import plan_runtime

# Marks an organization's AppTemplate as the copy of a built-in application (the
# model has no key column; a description marker needs no migration and stays
# visible to an administrator reading the template).
BUILT_IN_MARKER = "Built-in application: "
# Fixed namespace so the same app key + definition path always yields the same id.
_ID_NAMESPACE = uuid.UUID("6f1c3d1e-7a5b-5c1e-9d2f-1f0b6a2c4e11")


class Status(StrEnum):
    QUALIFIED = "qualified"
    PARTIALLY_QUALIFIED = "partially_qualified"
    EXPERIMENTAL = "experimental"


STATUS_LABELS = {
    Status.QUALIFIED: "Ready for use",
    Status.PARTIALLY_QUALIFIED: "Pilot preview",
    Status.EXPERIMENTAL: "Experimental",
}


@dataclass(frozen=True)
class BuiltInApp:
    key: str  # a REGISTRY key
    label: str
    summary: str
    highlights: tuple[str, ...]
    status: Status
    # Where the qualification evidence for this status lives -- never empty for QUALIFIED.
    evidence: tuple[str, ...] = field(default_factory=tuple)


CATALOG: dict[str, BuiltInApp] = {
    app.key: app
    for app in (
        BuiltInApp(
            key="spare_parts",
            label="Spare Parts",
            summary=(
                "Sell and stock spare parts: parts and part numbers, warehouses, stock, purchase and sales "
                "orders, invoices."
            ),
            highlights=(
                "Parts and part numbers",
                "Vehicles",
                "Warehouses and stock",
                "Purchase orders",
                "Sales and invoices",
            ),
            status=Status.PARTIALLY_QUALIFIED,
            evidence=(
                "docs/architecture/adr/0016-tenant-operation-journal.md (atomic inventory, verified)",
                "docs/operations/RECOVERY_DRILL.md (backup and restore, verified at the data plane)",
                "Not yet qualified: receive/sell screens, browser journey, restart, upgrade of an "
                "installed app.",
            ),
        ),
        BuiltInApp(
            key="hr",
            label="Employee Management",
            summary=(
                "Employees, positions and departments, leave, timesheets, payroll records, reviews and "
                "onboarding tasks."
            ),
            highlights=("Employees", "Leave", "Timesheets", "Payroll records", "Reviews"),
            status=Status.EXPERIMENTAL,
            evidence=("Provisions and passes its template tests; no end-to-end qualification has been run.",),
        ),
        BuiltInApp(
            key="school",
            label="School Management",
            summary=(
                "Students, guardians, teachers, courses and terms, enrollment, attendance, grades and "
                "invoices."
            ),
            highlights=("Students", "Teachers", "Enrollment", "Attendance", "Grades"),
            status=Status.EXPERIMENTAL,
            evidence=("Provisions and passes its template tests; no end-to-end qualification has been run.",),
        ),
        BuiltInApp(
            key="crm",
            label="Customer Pipeline",
            summary=("Accounts, contacts, leads, campaigns, opportunities, activities and notes."),
            highlights=("Accounts", "Leads", "Opportunities", "Activities"),
            status=Status.EXPERIMENTAL,
            evidence=("Reference application; not part of the Local Edition v1.0 scope.",),
        ),
        BuiltInApp(
            key="procurement",
            label="Procurement",
            summary=(
                "Vendors, purchase requisitions and orders, goods receipts, vendor invoices and approvals."
            ),
            highlights=("Vendors", "Requisitions", "Goods receipts", "Approvals"),
            status=Status.EXPERIMENTAL,
            evidence=("Reference application; not part of the Local Edition v1.0 scope.",),
        ),
        BuiltInApp(
            key="assets",
            label="Asset Register",
            summary=("Assets by category and location, assignments, maintenance, depreciation and disposal."),
            highlights=("Assets", "Assignments", "Maintenance", "Depreciation"),
            status=Status.EXPERIMENTAL,
            evidence=("Reference application; not part of the Local Edition v1.0 scope.",),
        ),
        BuiltInApp(
            key="projects",
            label="Projects",
            summary=("Clients, projects, milestones, tasks, time entries and risks."),
            highlights=("Projects", "Tasks", "Time entries", "Risks"),
            status=Status.EXPERIMENTAL,
            evidence=("Reference application; not part of the Local Edition v1.0 scope.",),
        ),
        BuiltInApp(
            key="documents",
            label="Document Library",
            summary=("Document categories and folders, documents with versions, tags and reviews."),
            highlights=("Documents", "Versions", "Reviews"),
            status=Status.EXPERIMENTAL,
            evidence=("Reference application; not part of the Local Edition v1.0 scope.",),
        ),
        BuiltInApp(
            key="warehouses",
            label="Warehouse Logistics",
            summary=(
                "Warehouses, zones and bin locations, items, stock levels, shipments and transfer orders."
            ),
            highlights=("Bins", "Stock levels", "Shipments", "Transfers"),
            status=Status.EXPERIMENTAL,
            evidence=("Reference application; not part of the Local Edition v1.0 scope.",),
        ),
    )
}
assert set(CATALOG) == set(REGISTRY), "every reference template needs an honest catalog status"


def stabilize_ids(definition: dict, app_key: str) -> dict:
    """Return `definition` with every id replaced by a deterministic uuid5 derived
    from its path (app key, model key, field key ...), remapping every reference to
    it (relationship ends, constraint members, workflow fields/states, ledger
    declarations). Keys are unique in their scope, so paths are unambiguous."""

    def new_id(path: str) -> str:
        return str(uuid.uuid5(_ID_NAMESPACE, f"{app_key}/{path}"))

    mapping: dict[str, str] = {}

    def assign(item: dict, path: str) -> None:
        old, new = item.get("id"), new_id(path)
        item["id"] = new
        if old:
            mapping[old] = new

    result = json.loads(json.dumps(definition))
    for model in result["models"]:
        model_key = model["key"]
        assign(model, f"model/{model_key}")
        for item in model["fields"]:
            assign(item, f"field/{model_key}/{item['key']}")
        for item in model.get("constraints", []):
            assign(item, f"constraint/{model_key}/{item['key']}")
        for workflow in model.get("workflows", []):
            assign(workflow, f"workflow/{model_key}/{workflow['key']}")
            for state in workflow["states"]:
                assign(state, f"state/{model_key}/{workflow['key']}/{state['key']}")
            for transition in workflow["transitions"]:
                assign(transition, f"transition/{model_key}/{workflow['key']}/{transition['key']}")
    for relation in result["relationships"]:
        assign(relation, f"relationship/{relation['key']}")

    assert len(set(mapping.values())) == len(mapping), "built-in application ids must be unique"
    text = json.dumps(result)
    for old, new in mapping.items():
        text = text.replace(old, new)
    return json.loads(text)


def definition_for(key: str) -> dict:
    """The validated, id-stable definition of a built-in application."""
    builder = cast(Callable[[], dict], REGISTRY[key]["builder"])
    return validate_definition(stabilize_ids(builder(), key))


def _shown_to_customers(app: BuiltInApp) -> bool:
    return app.status == Status.QUALIFIED or settings.SHOW_UNQUALIFIED_BUILT_IN_APPS


def visible_apps() -> list[BuiltInApp]:
    return [app for app in CATALOG.values() if _shown_to_customers(app)]


def listing() -> list[dict]:
    """What the application gallery shows: only what this deployment may offer."""
    return [
        {
            "key": app.key,
            "label": app.label,
            "summary": app.summary,
            "highlights": list(app.highlights),
            "status": app.status.value,
            "status_label": STATUS_LABELS[app.status],
            "evidence": list(app.evidence),
        }
        for app in visible_apps()
    ]


class InstallFailed(APIException):
    status_code = 500
    default_detail = (
        "The application could not be prepared. Nothing is lost: open Applications to retry, "
        "or contact support with the diagnostics."
    )
    default_code = "install_failed"


def install(actor, project, key: str, label: str | None = None) -> AppInstance:
    """Publish (once), install and provision a built-in application into `project`.

    Idempotent for the template: the organization keeps ONE template per built-in
    application, and a new version is published only when the shipped definition
    changed. Every step goes through the ordinary services, so the actor needs the
    same capabilities as the manual path (`app_template.manage/publish`,
    `app_instance.manage`, `database.schema.manage`)."""
    app = CATALOG.get(key)
    if app is None or not _shown_to_customers(app):
        raise NotFound("No such application.")
    label = (label or app.label).strip()
    if not label or len(label) > 200:
        raise serializers.ValidationError({"label": "A name of 1 to 200 characters is required."})
    organization = project.workspace.organization
    definition = definition_for(key)
    marker = f"{BUILT_IN_MARKER}{key}"

    with transaction.atomic():
        template = AppTemplate.objects.filter(
            organization=organization, description__startswith=marker, archived=False
        ).first()
        if template is None:
            template = templates.create_template(
                actor,
                organization,
                {"label": app.label, "description": f"{marker}\n{app.summary}", "draft": definition},
            )
        elif template.draft != definition:
            template = templates.update_template(actor, template, {"draft": definition})
        version = template.versions.order_by("-number").first()
        if version is None or version.definition != definition:
            version = templates.publish_template(actor, template)
        instance = instances.install(actor, project, {"label": label, "template_version": str(version.id)})

    try:
        plan = plan_runtime(actor, instance)
        provisioning.reserve(actor, instance, plan["fingerprint"])
        provisioning.execute(instance.id, actor)
    except APIException:
        raise
    except Exception as exc:  # noqa: BLE001 - never leak an infrastructure traceback to the customer
        raise InstallFailed() from exc
    return instance
