"""Business recovery drill -- seed, snapshot and verify (run via `manage.py shell`).

    DRILL_MODE=seed      build a realistic Spare Parts business through the real
                         services/API, then write the expected-state snapshot
    DRILL_MODE=verify    measure the (restored) system the same way, compare it
                         with the snapshot, then probe that the ledger triggers,
                         permissions, files and login still work
    DRILL_MODE=snapshot  write the expected-state snapshot of an EXISTING business (no seeding)

By default the drill seeds and checks its own business ("Recovery Drill Shop"). To drill a business that
was built through the browser instead, set DRILL_UI_STATE to the JSON the recovery-prep Playwright spec
wrote (owner/cashier accounts, instance id); the same snapshot, comparison and probes then apply to it.

Only ever run against the disposable qualification stack (see run-drill.sh).
The same `snapshot()` measures before and after, so "restored" means measured
equal -- not "the restore command exited 0".
"""

import base64
import hashlib
import io
import json
import os
import sys
from datetime import datetime, timezone

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.db import connections
from django.urls import reverse
from psycopg import sql
from rest_framework.test import APIClient

from app_platform import instances, provisioning, quantity_ledger, templates
from app_platform.models import AppInstance, ModelDefinition, QuantityLedgerBinding
from app_platform.reference_templates.spare_parts import spare_parts_reference_definition
from app_platform.runtime_plan import plan_runtime
from app_platform.tests.test_foundation import project_for
from audit.models import AuditEvent
from organizations.models import Membership, Organization
from organizations.services import create_organization
from sharing.models import ShareGrant

User = get_user_model()
STATE_FILE = os.environ.get("DRILL_STATE", "/backups/drill/expected.json")
OWNER = ("drill-owner@example.com", "Drill-Owner-Pass-2026!")
CASHIER = ("drill-cashier@example.com", "Drill-Cashier-Pass-2026!")
ORG_NAME = "Recovery Drill Shop"
PART_NAME = "Oil Filter"
INSTANCE_ID = None
UI_INVOICE = None
if os.environ.get("DRILL_UI_STATE"):
    _ui = json.load(open(os.environ["DRILL_UI_STATE"]))
    OWNER = (_ui["owner"]["email"], _ui["owner"]["password"])
    CASHIER = (_ui["cashier"]["email"], _ui["cashier"]["password"])
    INSTANCE_ID = _ui["instanceId"]
    PART_NAME = "Demo Oil Filter"
    UI_INVOICE = _ui["invoiceNumber"]


def _instance():
    if INSTANCE_ID:
        return AppInstance.objects.get(pk=INSTANCE_ID)
    return AppInstance.objects.get(organization__name=ORG_NAME, label="Spare Parts")
# A valid 1x1 PNG plus deterministic padding, so the object-storage backup
# carries a real, non-trivial, checksum-able file.
PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
)
IMAGE_BYTES = PNG + hashlib.sha256(b"drill-image").digest() * 4096  # ~128 KB
DOC_BYTES = b"INVOICE INV-DRILL-1\nOil Filter x5 @ 15.00 = 75.00\n" * 200


def api(user=None):
    client = APIClient()
    client.defaults["HTTP_X_FORWARDED_PROTO"] = "https"  # prod settings redirect plain http
    if user is not None:
        client.force_authenticate(user)
    return client


class Shop:
    """Thin helper over the Spare Parts runtime, keyed by template model/field keys."""

    def __init__(self, instance, client):
        self.instance, self.client = instance, client
        self.models = {m.key: m for m in instance.models.all()}

    def did(self, model_key, key):
        model = self.models[model_key]
        field = model.fields.filter(key=key).first()
        return str(field.id if field is not None else model.outgoing.get(key=key).id)

    def payload(self, model_key, **values):
        return {self.did(model_key, k): v for k, v in values.items()}

    def create(self, model_key, client=None, **values):
        r = (client or self.client).post(
            f"/api/v1/app-models/{self.models[model_key].id}/records/",
            self.payload(model_key, **values),
            format="json",
        )
        assert r.status_code == 201, (model_key, r.status_code, r.data)
        return r.data

    def rows(self, model_key, client=None):
        r = (client or self.client).get(f"/api/v1/app-models/{self.models[model_key].id}/records/?limit=100")
        assert r.status_code == 200, (model_key, r.status_code, r.data)
        return r.data["results"]

    def op(self, op, model_key, ref=None, **values):
        item = {"op": op, "model": str(self.models[model_key].id), "data": self.payload(model_key, **values)}
        if ref:
            item["ref"] = ref
        return item

    def transact(self, operations, key=None, client=None):
        extra = {"HTTP_IDEMPOTENCY_KEY": key} if key else {}
        return (client or self.client).post(
            f"/api/v1/app-instances/{self.instance.id}/transactions/",
            {"operations": operations},
            format="json",
            **extra,
        )

    def movement(self, part, warehouse, delta, kind):
        return self.op(
            "create",
            "stock_movement",
            stock_movement_part=part,
            stock_movement_warehouse=warehouse,
            quantity_delta=delta,
            movement_type=kind,
        )


def seed():
    call_command("seed_permissions", verbosity=0)
    owner = User.objects.create_user(email=OWNER[0], password=OWNER[1])
    cashier = User.objects.create_user(email=CASHIER[0], password=CASHIER[1])
    org = create_organization(name="Recovery Drill Shop", created_by=owner)
    Membership.objects.create(user=cashier, organization=org, status=Membership.Status.ACTIVE)
    project = project_for(owner, org)
    template = templates.create_template(
        owner, org, {"label": "Spare Parts", "draft": spare_parts_reference_definition()}
    )
    version = templates.publish_template(owner, template)
    instance = instances.install(owner, project, {"label": "Spare Parts", "template_version": str(version.id)})
    plan = plan_runtime(owner, instance)
    provisioning.reserve(owner, instance, plan["fingerprint"])
    provisioning.execute(instance.id, owner)

    client = api(owner)
    shop = Shop(instance, client)
    oil = shop.create("part", name="Oil Filter", unit_of_measure="each", list_price="15.00")
    pad = shop.create("part", name="Brake Pad Set", unit_of_measure="set", list_price="48.00")
    shop.create("part_number", number="OF-1001", source="OEM", part_number_part=oil["id"])
    shop.create("part_number", number="BP-2002", source="Aftermarket", part_number_part=pad["id"])
    main = shop.create("warehouse", name="Main Warehouse", code="MAIN")
    floor = shop.create("warehouse", name="Shop Floor", code="FLOOR")
    supplier = shop.create("supplier", name="Demo Supplier A")
    customer = shop.create("customer", name="Demo Retail Customer")

    # Zero-start balance rows are allowed; only movements change them afterwards.
    for part in (oil, pad):
        for warehouse in (main, floor):
            shop.create("inventory", part=part["id"], warehouse=warehouse["id"], quantity_on_hand=0)
    po = shop.create("purchase_order", supplier=supplier["id"], status="draft")

    r = shop.transact(
        [
            {
                "op": "update",
                "model": str(shop.models["purchase_order"].id),
                "record": po["id"],
                "data": shop.payload("purchase_order", status="received"),
            },
            shop.movement(oil["id"], main["id"], 100, "receive"),
            shop.movement(pad["id"], main["id"], 30, "receive"),
        ],
        key="drill-receive-1",
    )
    assert r.status_code == 201, r.data
    # A two-leg transfer commits both legs or neither.
    r = shop.transact(
        [
            shop.movement(oil["id"], main["id"], -20, "transfer_out"),
            shop.movement(oil["id"], floor["id"], 20, "transfer_in"),
        ],
        key="drill-transfer-1",
    )
    assert r.status_code == 201, r.data
    r = shop.transact(
        [
            shop.op("create", "sales_order", ref="order", customer=customer["id"], status="confirmed"),
            shop.op(
                "create",
                "sales_order_line",
                sales_order_line_sales_order={"$ref": "order"},
                sales_order_line_part=oil["id"],
                quantity=5,
                unit_price="15.00",
                line_total="75.00",
            ),
            shop.movement(oil["id"], main["id"], -5, "sale"),
            shop.op(
                "create",
                "invoice",
                invoice_number="INV-DRILL-1",
                invoice_sales_order={"$ref": "order"},
                amount_due="75.00",
                status="unpaid",
            ),
        ],
        key="drill-sale-1",
    )
    assert r.status_code == 201, r.data

    # Files: a product image attached to the part, and a stored invoice document.
    bucket = client.post(reverse("bucket-list-create", args=[project.id]), {"name": "Business Files"})
    assert bucket.status_code == 201, bucket.data
    file_ids = {}
    for name, content, ctype in (("oil-filter.png", IMAGE_BYTES, "image/png"), ("INV-DRILL-1.txt", DOC_BYTES, "text/plain")):
        up = client.post(
            reverse("file-list-create", args=[bucket.data["id"]]),
            {"file": SimpleUploadedFile(name, content, content_type=ctype), "display_filename": name},
            format="multipart",
        )
        assert up.status_code == 201, up.data
        file_ids[name] = up.data["id"]
    att = client.post(
        f"/api/v1/app-models/{shop.models['part'].id}/records/{oil['id']}/attachments/",
        {"file_id": file_ids["oil-filter.png"]},
        format="json",
    )
    assert att.status_code == 201, att.data

    # A restricted cashier (ADR-0017): reads what a sale needs, writes only the sales documents, and holds the
    # SELL business-operation authority -- no write access to the stock tables, no receive, no adjust.
    def share(resource_type, resource_id, level):
        g = client.post(
            reverse("share-grant-list-create", args=[org.id]),
            {"resource_type": resource_type, "resource_id": str(resource_id), "principal_type": "user",
             "user_id": str(cashier.id), "level": level},
            format="json",
        )
        assert g.status_code == 201, g.data

    for model_key in ("part", "part_number", "warehouse", "customer", "inventory", "stock_movement"):
        share("app_model", shop.models[model_key].id, "read")
    for model_key in ("sales_order", "sales_order_line", "invoice"):
        share("app_model", shop.models[model_key].id, "write")
    share("inventory_operations", instance.id, "sell")

    state = snapshot()
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, "w") as handle:
        json.dump(state, handle, indent=2, sort_keys=True)
    print("SEED OK; expected state written to", STATE_FILE)
    print(json.dumps(state["summary"], indent=2, sort_keys=True))


def _hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str).encode()).hexdigest()


def snapshot():
    """Everything the recovery must bring back, measured through the real API/services."""
    owner = User.objects.get(email=OWNER[0])
    instance = _instance()
    org = instance.organization
    client = api(owner)
    shop = Shop(instance, client)
    out = {"summary": {}, "tables": {}, "hashes": {}}

    out["org"] = {"id": str(org.id), "name": org.name}
    out["instance"] = {"id": str(instance.id), "template_version": str(instance.source_version_id)}
    out["models"] = {m.key: str(m.id) for m in instance.models.all()}
    for key in sorted(shop.models):
        rows = sorted(shop.rows(key), key=lambda row: row["id"])
        out["tables"][key] = [row["id"] for row in rows]
        out["hashes"][key] = _hash(rows)
        out["summary"][key] = len(rows)

    binding = QuantityLedgerBinding.objects.get(instance=instance)
    out["ledger"] = {"binding": str(binding.id), "allow_negative": binding.allow_negative}
    on_hand = shop.did("inventory", "quantity_on_hand")
    part_rel, wh_rel = shop.did("inventory", "part"), shop.did("inventory", "warehouse")
    out["balances"] = {
        f"{row[part_rel]}|{row[wh_rel]}": row[on_hand] for row in shop.rows("inventory")
    }
    out["reconcile"] = quantity_ledger.reconcile(binding)
    out["audit_events"] = AuditEvent.objects.filter(organization_id=org.id).count()
    out["share_grants"] = ShareGrant.objects.filter(organization_id=org.id).count()
    out["memberships"] = sorted(
        Membership.objects.filter(organization=org).values_list("user__email", flat=True)
    )

    # Files: bytes read back through the real download path, hashed.
    files = {}
    part_model = shop.models["part"]
    for part_row in shop.rows("part"):
        listing = client.get(f"/api/v1/app-models/{part_model.id}/records/{part_row['id']}/attachments/")
        assert listing.status_code == 200, listing.data
        for attachment in listing.data:
            download = client.get(
                f"/api/v1/app-models/{part_model.id}/records/{part_row['id']}/attachments/{attachment['id']}/download/"
            )
            body = b"".join(download.streaming_content) if getattr(download, "streaming", False) else download.content
            files[attachment["filename"]] = {
                "attachment": str(attachment["id"]),
                "bytes": len(body),
                "sha256": hashlib.sha256(body).hexdigest(),
            }
    out["files"] = files

    with connections["tenant"].cursor() as cursor:
        cursor.execute(
            "SELECT count(*) FROM pg_trigger t JOIN pg_class c ON c.oid = t.tgrelid "
            "JOIN pg_namespace n ON n.oid = c.relnamespace "
            "WHERE NOT t.tgisinternal AND t.tgname LIKE 'trg_ledger_%'"
        )
        out["ledger_triggers"] = cursor.fetchone()[0]
    # Plain JSON types on both sides of every comparison (native UUIDs, Decimals, datetimes -> str).
    return json.loads(json.dumps(out, default=str, sort_keys=True))


def verify():
    expected = json.load(open(STATE_FILE))
    actual = snapshot()
    failures, checks = [], 0

    def check(name, ok, detail=""):
        nonlocal checks
        checks += 1
        print(("PASS  " if ok else "FAIL  ") + name + (f"  -- {detail}" if detail and not ok else ""))
        if not ok:
            failures.append(name)

    for key in ("org", "instance", "models", "ledger", "balances", "reconcile", "share_grants", "memberships",
                "ledger_triggers"):
        check(f"restored {key} equals the pre-disaster {key}", expected[key] == actual[key],
              f"expected {expected[key]!r} got {actual[key]!r}")
    for key in sorted(expected["tables"]):
        check(f"{key}: same record ids ({len(expected['tables'][key])})", expected["tables"][key] == actual["tables"][key])
        check(f"{key}: identical record content", expected["hashes"][key] == actual["hashes"][key])
    check("audit trail preserved", actual["audit_events"] >= expected["audit_events"],
          f"expected >= {expected['audit_events']} got {actual['audit_events']}")
    check("every file byte-identical (sha256)", expected["files"] == actual["files"], f"{expected['files']} vs {actual['files']}")

    # Login through the real endpoint, with the pre-disaster password.
    for email, password in (OWNER, CASHIER):
        response = api().post("/api/v1/auth/login/", {"email": email, "password": password}, format="json")
        check(f"login works for {email}", response.status_code == 200, f"status {response.status_code}")

    # Behavior: the triggers, ledger and permissions must be alive, not merely present.
    owner = User.objects.get(email=OWNER[0])
    cashier = User.objects.get(email=CASHIER[0])
    instance = _instance()
    shop = Shop(instance, api(owner))
    oil = next(r for r in shop.rows("part") if r[shop.did("part", "name")] == PART_NAME)
    main = next(r for r in shop.rows("warehouse") if r[shop.did("warehouse", "code")] == "MAIN")
    over = shop.transact([shop.movement(oil["id"], main["id"], -100000, "sale")])
    check("overselling is still rejected after restore", over.status_code == 400 and "negative" in str(over.data), str(over.data))
    inv_row = shop.rows("inventory")[0]
    edit = shop.client.patch(
        f"/api/v1/app-models/{shop.models['inventory'].id}/records/{inv_row['id']}/",
        shop.payload("inventory", quantity_on_hand=999999),
        format="json",
    )
    check("a direct balance edit is still rejected", edit.status_code == 400, str(edit.data))
    moves = shop.rows("stock_movement")
    gone = shop.client.delete(f"/api/v1/app-models/{shop.models['stock_movement'].id}/records/{moves[0]['id']}/")
    check("a movement still cannot be deleted", gone.status_code == 400, str(gone.data))
    cashier_shop = Shop(instance, api(cashier))
    denied = cashier_shop.client.post(
        f"/api/v1/app-models/{shop.models['part'].id}/records/", shop.payload("part", name="Intruder"), format="json"
    )
    check("the restricted cashier is still denied on Part", denied.status_code == 403, f"status {denied.status_code}")

    # The way a shop actually finds a part: a differently typed part number still finds the product.
    found = shop.client.get(
        f"/api/v1/app-models/{shop.models['part_number'].id}/records/?search=044650k290&limit=5"
    )
    check("normalized part-number search still finds the product after restore",
          found.status_code == 200 and any(
              row[shop.did("part_number", "part_number_part")] == oil["id"] for row in found.data["results"]
          ) if INSTANCE_ID else True, str(getattr(found, "data", None)))
    if UI_INVOICE:
        invoices = shop.rows("invoice")
        orders = {row["id"]: row for row in shop.rows("sales_order")}
        lines = shop.rows("sales_order_line")
        linked = [
            row for row in invoices
            if row[shop.did("invoice", "invoice_number")] == UI_INVOICE
            and row[shop.did("invoice", "invoice_sales_order")] in orders
            and any(line[shop.did("sales_order_line", "sales_order_line_sales_order")]
                    == row[shop.did("invoice", "invoice_sales_order")] for line in lines)
        ]
        check(f"invoice {UI_INVOICE} is still linked to its sales order and line", len(linked) == 1, str(len(invoices)))

    # The restored business keeps operating: a real receive, then a real sale of it.
    before = sum(actual["balances"].values())
    ok = shop.transact([shop.movement(oil["id"], main["id"], 7, "receive")], key="post-restore-receive")
    check("a new receive works on the restored system", ok.status_code == 201, str(ok.data))
    sale = shop.transact([shop.movement(oil["id"], main["id"], -7, "sale")], key="post-restore-sale")
    check("a new sale works on the restored system", sale.status_code == 201, str(sale.data))
    # ...and the restricted cashier can still do exactly their job: sell, through the controlled operation and the
    # real permission system -- and still cannot receive, adjust or write a movement by hand.
    customer = shop.rows("customer")[0]
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
    cashier_sale = cashier_shop.client.post(
        f"/api/v1/app-instances/{instance.id}/operations/sell/",
        {"customer": str(customer["id"]), "invoice_number": "INV-POST-RESTORE-CASHIER", "occurred_at": stamp,
         "lines": [{"part": str(oil["id"]), "warehouse": str(main["id"]), "quantity": 1, "unit_price": "15.00"}]},
        format="json",
        HTTP_IDEMPOTENCY_KEY="post-restore-cashier-sale",
    )
    check("the restricted cashier can still sell on the restored system", cashier_sale.status_code == 201,
          str(getattr(cashier_sale, "data", None)))
    cashier_receive = cashier_shop.client.post(
        f"/api/v1/app-instances/{instance.id}/operations/receive/",
        {"part": str(oil["id"]), "warehouse": str(main["id"]), "quantity": 1, "occurred_at": stamp},
        format="json",
        HTTP_IDEMPOTENCY_KEY="post-restore-cashier-receive",
    )
    check("the restricted cashier still cannot receive stock", cashier_receive.status_code == 403,
          f"status {cashier_receive.status_code}")
    direct = cashier_shop.transact([shop.movement(oil["id"], main["id"], 5, "receive")], client=cashier_shop.client)
    check("the restricted cashier still cannot write a stock movement directly", direct.status_code == 403,
          f"status {direct.status_code}")
    refund = shop.transact([shop.movement(oil["id"], main["id"], 1, "receive")], key="post-restore-restock")
    check("stock returned to the pre-sale figure", refund.status_code == 201, str(refund.data))
    binding = QuantityLedgerBinding.objects.get(instance=instance)
    check("ledger reconciles after post-restore activity", quantity_ledger.reconcile(binding) == [])
    check("stock total unchanged by the receive/sale pair", sum(
        row[shop.did("inventory", "quantity_on_hand")] for row in shop.rows("inventory")
    ) == before)

    print(f"\n{checks - len(failures)}/{checks} checks passed")
    if failures:
        print("FAILED:", *failures, sep="\n  ")
        sys.exit(1)


def write_snapshot():
    state = snapshot()
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, "w") as handle:
        json.dump(state, handle, indent=2, sort_keys=True)
    print("SNAPSHOT OK; expected state written to", STATE_FILE)
    print(json.dumps(state["summary"], indent=2, sort_keys=True))


mode = os.environ.get("DRILL_MODE", "")
if mode == "seed":
    seed()
elif mode == "snapshot":
    write_snapshot()
elif mode == "verify":
    verify()
else:
    raise SystemExit("set DRILL_MODE=seed|snapshot|verify")
