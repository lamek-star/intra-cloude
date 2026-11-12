"""Built-in business applications: the customer-facing catalog and one-click install.

Until now, getting a ready-made application meant creating a template, publishing
it, installing it, then planning, reserving and provisioning a runtime -- a
developer workflow. A shop owner must not run API commands or edit JSON (Local
Edition §27). `install()` does that whole sequence in one call, through the same
services (so every capability check is unchanged), and `listing()` is what the
production gallery shows.

Release status is real, not marketing. A built-in application appears to
customers only when its status is QUALIFIED; PARTIALLY_QUALIFIED and EXPERIMENTAL
entries exist for development, demos and the supervised pilot and are shown, clearly
labelled, only when `SHOW_UNQUALIFIED_BUILT_IN_APPS` is on. DEFERRED entries (real
reference templates outside the Local Edition v1.0 scope) are never offered and never
installable through this catalog, flag or not. Flip an entry to QUALIFIED only with the
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
from .models import AppInstance, AppTemplate, RuntimeProvision
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
    DEFERRED = "deferred"


STATUS_LABELS = {
    Status.QUALIFIED: "Ready for use",
    Status.PARTIALLY_QUALIFIED: "Pilot preview",
    Status.EXPERIMENTAL: "Experimental",
    Status.DEFERRED: "Not offered in v1.0",
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
            status=Status.QUALIFIED,
            evidence=(
                "docs/LOCAL_EDITION_APPLICATIONS.md (final qualification decision and the gate table)",
                "docs/architecture/adr/0016-tenant-operation-journal.md (atomic inventory, the ledger)",
                "docs/architecture/adr/0017-inventory-operation-authority.md (sell, receive, adjust and "
                "transfer are separate authorities; no direct stock-movement bypass)",
                "apps/frontend/e2e/spare-parts-flagship.spec.ts (install, search, receive, sell, sales "
                "document, files, restart, oversell refusal, with every non-local request blocked)",
                "apps/frontend/e2e/spare-parts-cashier.spec.ts (restricted cashier and receiver roles, "
                "enforced by the server)",
                "apps/frontend/e2e/spare-parts-accessibility.spec.ts (axe over every screen and state, "
                "keyboard-only paths)",
                "docs/implementation/SCALE_QUALIFICATION.md (5,000 products, 10,000 part numbers, "
                "10,000 movements)",
                "docs/operations/RECOVERY_DRILL.md (upgrade of an installed instance; destructive "
                "restore from backup files)",
                "Scope: the application on the supported Docker runtime. Windows installer, automatic "
                "startup and code signing are qualified separately.",
            ),
        ),
        BuiltInApp(
            key="pharmacy",
            label="Pharmacy",
            summary=(
                "Medicines and their stock: generic name, pack, manufacturer, prescription, shelf "
                "location, the shop's own price beside a supplier's reference price, pictures, labels, "
                "receiving and sales."
            ),
            highlights=(
                "Medicines with generic names",
                "Prescription flag and shelf location",
                "Import a medicines catalogue (CSV)",
                "Stock, receiving and sales",
                "Barcode labels",
            ),
            status=Status.PARTIALLY_QUALIFIED,
            evidence=(
                "The Spare Parts engine unchanged (same models, relationships, constraints and quantity "
                "ledger), so stock, receiving and selling are the qualified ones; the pharmacy adds product "
                "fields only.",
                "app_platform/tests/test_pharmacy_template.py (provisions; the medicine fields round-trip; "
                "the ledger still refuses overselling).",
                "Not yet run end to end through the UI with the shop's own staff; offered as a pilot "
                "preview (BUILT_IN_APP_PREVIEWS).",
            ),
        ),
        BuiltInApp(
            key="hr",
            label="Employee Management",
            summary=(
                "Employees, positions and departments, leave requests, timesheets, performance "
                "reviews and onboarding tasks."
            ),
            highlights=("Employees", "Departments and positions", "Leave", "Timesheets"),
            status=Status.EXPERIMENTAL,
            evidence=(
                "Provisions and passes its template tests; no end-to-end qualification has been run.",
                "The template also holds a plain Payroll Record table (pay-period dates, gross and net "
                "amounts, status). It has no calculation, tax or workflow, is not a payroll feature, and "
                "is not offered or advertised for Local Edition v1.0.",
            ),
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
            key="repair_shop",
            label="Repair Shop",
            summary=(
                "Job cards for a repair counter: customers and their devices, the fault, status and promised "
                "date, parts and labour, and payments."
            ),
            highlights=("Job cards", "Devices", "Parts and labour", "Payments"),
            status=Status.EXPERIMENTAL,
            evidence=(
                "app_platform/tests/test_repair_rentals_templates.py (validates, installs, provisions; a job "
                "with its parts, labour and payment through the record API; job numbers are unique).",
                "No end-to-end qualification with a shop's staff has been run.",
            ),
        ),
        BuiltInApp(
            key="rentals",
            label="Rentals",
            summary=(
                "Hire items out: items and their daily price, customers, bookings with dates, deposit and "
                "condition on return, and payments."
            ),
            highlights=("Items", "Bookings", "Deposits", "Payments"),
            status=Status.EXPERIMENTAL,
            evidence=(
                "app_platform/tests/test_repair_rentals_templates.py (validates, installs, provisions; a "
                "booking through the record API; one booking per item starting on the same day).",
                "Overlapping bookings of one item are not prevented; no end-to-end qualification has "
                "been run.",
            ),
        ),
        BuiltInApp(
            key="crm",
            label="Customer Pipeline",
            summary=("Accounts, contacts, leads, campaigns, opportunities, activities and notes."),
            highlights=("Accounts", "Leads", "Opportunities", "Activities"),
            status=Status.DEFERRED,
            evidence=("Reference application from an earlier phase; outside the Local Edition v1.0 scope.",),
        ),
        BuiltInApp(
            key="procurement",
            label="Procurement",
            summary=(
                "Vendors, purchase requisitions and orders, goods receipts, vendor invoices and approvals."
            ),
            highlights=("Vendors", "Requisitions", "Goods receipts", "Approvals"),
            status=Status.DEFERRED,
            evidence=("Reference application from an earlier phase; outside the Local Edition v1.0 scope.",),
        ),
        BuiltInApp(
            key="assets",
            label="Asset Register",
            summary=("Assets by category and location, assignments, maintenance, depreciation and disposal."),
            highlights=("Assets", "Assignments", "Maintenance", "Depreciation"),
            status=Status.DEFERRED,
            evidence=("Reference application from an earlier phase; outside the Local Edition v1.0 scope.",),
        ),
        BuiltInApp(
            key="projects",
            label="Projects",
            summary=("Clients, projects, milestones, tasks, time entries and risks."),
            highlights=("Projects", "Tasks", "Time entries", "Risks"),
            status=Status.DEFERRED,
            evidence=("Reference application from an earlier phase; outside the Local Edition v1.0 scope.",),
        ),
        BuiltInApp(
            key="documents",
            label="Document Library",
            summary=("Document categories and folders, documents with versions, tags and reviews."),
            highlights=("Documents", "Versions", "Reviews"),
            status=Status.DEFERRED,
            evidence=("Reference application from an earlier phase; outside the Local Edition v1.0 scope.",),
        ),
        BuiltInApp(
            key="warehouses",
            label="Warehouse Logistics",
            summary=(
                "Warehouses, zones and bin locations, items, stock levels, shipments and transfer orders."
            ),
            highlights=("Bins", "Stock levels", "Shipments", "Transfers"),
            status=Status.DEFERRED,
            evidence=("Reference application from an earlier phase; outside the Local Edition v1.0 scope.",),
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
    if app.status == Status.QUALIFIED:
        return True
    if app.status == Status.DEFERRED:
        return False  # outside v1.0: the preview flag must not be a way around that
    # One named preview (e.g. the Pharmacy for the own-shop pilot) without listing every experimental app.
    return settings.SHOW_UNQUALIFIED_BUILT_IN_APPS or app.key in settings.BUILT_IN_APP_PREVIEWS


def visible_apps() -> list[BuiltInApp]:
    return [app for app in CATALOG.values() if _shown_to_customers(app)]


def built_in_key(instance: AppInstance) -> str | None:
    """The catalog key an instance was installed from, or None for a hand-made app."""
    description = instance.source_version.template.description
    if not description.startswith(BUILT_IN_MARKER):
        return None
    return description.split("\n", 1)[0][len(BUILT_IN_MARKER) :]


def runtime_state(receipt: RuntimeProvision | None) -> str:
    """ready / failed / pending / not_provisioned -- what the gallery shows for an installed app."""
    if receipt is None:
        return "not_provisioned"
    if receipt.completed_at:
        return "ready"
    return "failed" if receipt.last_error else "pending"


def _installed_by_key(instances_qs) -> dict[str, list[dict]]:
    rows = list(
        instances_qs.filter(
            archived=False, source_version__template__description__startswith=BUILT_IN_MARKER
        ).select_related("source_version__template")
    )
    receipts = {r.instance_id: r for r in RuntimeProvision.objects.filter(instance__in=rows)}
    installed: dict[str, list[dict]] = {}
    for instance in rows:
        key = built_in_key(instance)
        if key is None:
            continue
        installed.setdefault(key, []).append(
            {
                "id": str(instance.id),
                "label": instance.label,
                "runtime": runtime_state(receipts.get(instance.id)),
            }
        )
    return installed


def listing(readable_instances=None) -> list[dict]:
    """What the application gallery shows: only what this deployment may offer.

    `readable_instances` is a queryset of the instances the caller may already read
    (authorization is the view's job); when given, each entry also reports which of
    them were installed from it and whether their runtime is ready."""
    installed = _installed_by_key(readable_instances) if readable_instances is not None else {}
    return [
        {
            "key": app.key,
            "label": app.label,
            "summary": app.summary,
            "highlights": list(app.highlights),
            "status": app.status.value,
            "status_label": STATUS_LABELS[app.status],
            "evidence": list(app.evidence),
            "installed": installed.get(app.key, []),
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


def retry_provisioning(actor, instance: AppInstance) -> AppInstance:
    """Finish preparing a built-in application whose setup did not complete.

    Safe to repeat: it is the same plan -> reserve -> execute sequence `install()` runs,
    each step of which is idempotent (a completed runtime is returned as-is, an
    unfinished one is reconciled and rebuilt). It never creates a second instance.
    Only instances installed from this catalog qualify; a hand-made app is 'not found'."""
    key = built_in_key(instance)
    if key is None or key not in CATALOG:
        raise NotFound("No such application.")
    try:
        plan = plan_runtime(actor, instance)
        provisioning.reserve(actor, instance, plan["fingerprint"])
        provisioning.execute(instance.id, actor)
    except APIException:
        raise
    except Exception as exc:  # noqa: BLE001 - never leak an infrastructure traceback to the customer
        raise InstallFailed() from exc
    return instance
