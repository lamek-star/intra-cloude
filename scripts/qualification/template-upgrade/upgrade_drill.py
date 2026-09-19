"""Installed-template upgrade drill -- run via `manage.py shell` against the DISPOSABLE qualification stack.

    DRILL_UI_STATE=<json written by e2e/spare-parts-recovery-prep.spec.ts>  python manage.py shell < upgrade_drill.py

Takes a business that was built through the browser (real records, a stored document, a restricted cashier
with real sharing grants, the quantity ledger and its triggers), lets the customer customise it locally, then
publishes a NEWER version of the same template and applies the upgrade through the real API. Everything is
measured before and after with the same function, and "survived" means measured equal -- never "the call
returned 201".

What v2 changes upstream: adds a field to Part and a whole new model (additions); relabels Supplier (safe
label sync: the customer never touched it); relabels Warehouse (which the customer also renamed locally -> a
conflict that must be left alone, never overwritten).
"""

import copy
import hashlib
import json
import os
import sys
import uuid

from django.contrib.auth import get_user_model
from django.db import connections
from rest_framework.test import APIClient

from app_platform import instances, quantity_ledger, templates
from app_platform.models import AppInstance, QuantityLedgerBinding, RuntimeProvision
from app_platform.reference_templates._helpers import _field, _model
from audit.models import AuditEvent
from sharing.models import ShareGrant

User = get_user_model()
state = json.load(open(os.environ["DRILL_UI_STATE"]))
instance = AppInstance.objects.get(pk=state["instanceId"])
owner = User.objects.get(email=state["owner"]["email"])
cashier = User.objects.get(email=state["cashier"]["email"])
failures, checks = [], 0


def check(name, ok, detail=""):
    global checks
    checks += 1
    print(("PASS  " if ok else "FAIL  ") + name + (f"  -- {detail}" if detail and not ok else ""), flush=True)
    if not ok:
        failures.append(name)


def api(user):
    client = APIClient()
    client.defaults["HTTP_X_FORWARDED_PROTO"] = "https"
    client.force_authenticate(user)
    return client


def model_map():
    return {m.key: m for m in instance.models.all()}


def field_id(model_key, key):
    model = model_map()[model_key]
    field = model.fields.filter(key=key).first()
    return str(field.id if field is not None else model.outgoing.get(key=key).id)


def payload(model_key, **values):
    return {field_id(model_key, k): v for k, v in values.items()}


def rows(client, model_key):
    response = client.get(f"/api/v1/app-models/{model_map()[model_key].id}/records/?limit=100")
    assert response.status_code == 200, (model_key, response.status_code, response.data)
    return sorted(response.data["results"], key=lambda r: r["id"])


def op(model_key, kind="create", ref=None, **values):
    item = {"op": kind, "model": str(model_map()[model_key].id), "data": payload(model_key, **values)}
    if ref:
        item["ref"] = ref
    return item


def transact(client, operations, key):
    return client.post(
        f"/api/v1/app-instances/{instance.id}/transactions/", {"operations": operations}, format="json",
        HTTP_IDEMPOTENCY_KEY=key,
    )


def measure(original_field_ids=None):
    client = api(owner)
    out = {"instance": str(instance.id), "receipt": str(RuntimeProvision.objects.get(instance=instance).pk),
           "source_version": str(instance.source_version_id), "tables": {}, "hashes": {}}
    models = model_map()
    out["definitions"] = {
        "models": {m.key: [str(m.id), m.label] for m in models.values()},
        "fields": {f"{m.key}.{f.key}": str(f.id) for m in models.values() for f in m.fields.all()},
        "relationships": {r.key: str(r.id) for r in instance.relationships.all()},
        "constraints": {c.key: str(c.id) for m in models.values() for c in m.constraints.all()},
    }
    for key in models:
        listing = rows(client, key)
        out["tables"][key] = [r["id"] for r in listing]
        if original_field_ids is not None:  # after the upgrade: compare only the columns that existed before
            listing = [{k: v for k, v in r.items() if k in original_field_ids or k == "id"} for r in listing]
        out["hashes"][key] = hashlib.sha256(json.dumps(listing, sort_keys=True, default=str).encode()).hexdigest()
    binding = QuantityLedgerBinding.objects.get(instance=instance)
    out["balances"] = {
        f"{r[field_id('inventory', 'part')]}|{r[field_id('inventory', 'warehouse')]}": r[field_id("inventory", "quantity_on_hand")]
        for r in rows(client, "inventory")
    }
    out["reconcile"] = quantity_ledger.reconcile(binding)
    out["grants"] = sorted(
        (g.resource_type, str(g.resource_id), g.level, str(g.user_id) if getattr(g, "user_id", None) else "")
        for g in ShareGrant.objects.filter(organization_id=instance.organization_id, revoked_at__isnull=True)
    )
    part = models["part"]
    files = {}
    for part_row in rows(client, "part"):
        listing = client.get(f"/api/v1/app-models/{part.id}/records/{part_row['id']}/attachments/")
        for attachment in listing.data:
            download = client.get(
                f"/api/v1/app-models/{part.id}/records/{part_row['id']}/attachments/{attachment['id']}/download/")
            body = b"".join(download.streaming_content) if getattr(download, "streaming", False) else download.content
            files[attachment["filename"]] = [len(body), hashlib.sha256(body).hexdigest()]
    out["files"] = files
    with connections["tenant"].cursor() as cursor:
        cursor.execute(
            "SELECT count(*) FROM pg_trigger t JOIN pg_class c ON c.oid = t.tgrelid WHERE NOT t.tgisinternal "
            "AND t.tgname LIKE 'trg_ledger_%'")
        out["ledger_triggers"] = cursor.fetchone()[0]
    out["memberships"] = instance.organization.memberships.count()
    out["audit_events"] = AuditEvent.objects.filter(organization_id=instance.organization_id).count()
    return json.loads(json.dumps(out, default=str))


print(f"=== upgrading instance {instance.id} of '{instance.organization.name}'", flush=True)
owner_client = api(owner)

# ------------------------------------------------------------------ 1. the customer customises locally
part_model = model_map()["part"]
instances.add_field(owner, part_model, {"key": "bin_location", "label": "Bin Location", "data_type": "text"})
local_model = instances.add_model(owner, instance, {"key": "notes", "label": "Notes"})
instances.update_definition(owner, model_map()["warehouse"], {"label": "Storeroom"})  # local rename
first_part = rows(owner_client, "part")[0]
patched = owner_client.patch(
    f"/api/v1/app-models/{part_model.id}/records/{first_part['id']}/",
    {field_id("part", "bin_location"): "A-12-3"}, format="json")
check("customer customisation: a local field holds a value on an existing record", patched.status_code == 200,
      str(patched.data))
before = measure()
original_field_ids = set(before["definitions"]["fields"].values()) | set(before["definitions"]["relationships"].values())
before_stock = sum(before["balances"].values())
check("baseline: the UI-built stock is what the flagship left", before_stock == state["onHand"], str(before_stock))

# ------------------------------------------------------------------ 2. publish a newer template version
base_version = instance.source_version
template = base_version.template
draft = copy.deepcopy(template.versions.order_by("-number").first().definition)
part_draft = next(m for m in draft["models"] if m["key"] == "part")
barcode_id, barcode_field = _field("barcode", "Barcode", "text")
part_draft["fields"].append(barcode_field)
next(m for m in draft["models"] if m["key"] == "supplier")["label"] = "Vendor"
next(m for m in draft["models"] if m["key"] == "warehouse")["label"] = "Location"
reason_name_id, reason_name = _field("name", "Name", "text", required=True)
draft["models"].append(_model(str(uuid.uuid4()), "return_reason", "Return Reason", [(reason_name_id, reason_name)]))
templates.update_template(owner, template, {"draft": draft})
v2 = templates.publish_template(owner, template)
print(f"published template version {v2.number} ({v2.id}) over installed version {base_version.id}", flush=True)

preview = owner_client.get(f"/api/v1/app-instances/{instance.id}/upgrade/{v2.id}/")
check("preview succeeds and changes nothing", preview.status_code == 200, str(preview.data))
text = json.dumps(preview.data, default=str)
check("preview reports the new field, the new model, and the safe label sync",
      "Barcode" in text and "Return Reason" in text and "Vendor" in text, text[:400])
check("preview reports the conflicting Warehouse rename as needing review, not as applicable",
      "Location" in text and "Storeroom" in text, text[:400])
check("previewing did not mutate the instance", measure()["definitions"] == before["definitions"])

# ------------------------------------------------------------------ 3. apply
applied = owner_client.post(f"/api/v1/app-instances/{instance.id}/upgrade/{v2.id}/", {}, format="json")
check("the upgrade is applied through the real API", applied.status_code == 201, str(applied.data))
instance.refresh_from_db()
after = measure(original_field_ids)

# identity
check("same application instance", before["instance"] == after["instance"])
check("same runtime provisioning receipt (no re-provision, no new tables)", before["receipt"] == after["receipt"])
check("permanent install provenance untouched (source_version)", before["source_version"] == after["source_version"])
# records
for key in sorted(before["tables"]):
    check(f"{key}: same record ids ({len(before['tables'][key])})", before["tables"][key] == after["tables"][key])
# the content of every pre-existing column of every record (the new columns are excluded from the hash)
for key in sorted(before["hashes"]):
    check(f"{key}: identical record content", before["hashes"][key] == after["hashes"][key])
client = api(owner)
check("balances identical", before["balances"] == after["balances"], f"{before['balances']} vs {after['balances']}")
check("ledger still reconciles", after["reconcile"] == [], str(after["reconcile"]))
check("ledger triggers present", before["ledger_triggers"] == after["ledger_triggers"] and after["ledger_triggers"] >= 4,
      f"{before['ledger_triggers']} -> {after['ledger_triggers']}")
check("stored file byte-identical", before["files"] == after["files"], f"{before['files']} vs {after['files']}")
check("sharing grants identical", before["grants"] == after["grants"])
check("memberships identical", before["memberships"] == after["memberships"])
check("audit trail preserved and extended", after["audit_events"] >= before["audit_events"])
# relationships, constraints, fields
for kind in ("relationships", "constraints"):
    check(f"every {kind[:-1]} still exists with the same id",
          all(after["definitions"][kind].get(k) == v for k, v in before["definitions"][kind].items()))
check("every original field still exists with the same id",
      all(after["definitions"]["fields"].get(k) == v for k, v in before["definitions"]["fields"].items()))
# what the upgrade added
check("the new Part field exists", "part.barcode" in after["definitions"]["fields"])
check("the new model exists", "return_reason" in after["definitions"]["models"])
check("safe label sync applied (Supplier -> Vendor)", after["definitions"]["models"]["supplier"][1] == "Vendor",
      str(after["definitions"]["models"]["supplier"]))
check("conflicting local rename left alone (Warehouse stays 'Storeroom')",
      after["definitions"]["models"]["warehouse"][1] == "Storeroom", str(after["definitions"]["models"]["warehouse"]))
# customisations
check("local field survived", "part.bin_location" in after["definitions"]["fields"])
check("local model survived", "notes" in after["definitions"]["models"])
survivor = next(r for r in rows(client, "part") if r["id"] == first_part["id"])
check("the local value on the existing record survived", survivor.get(field_id("part", "bin_location")) == "A-12-3",
      str(survivor))
check("the record's original data is unchanged (name, price)",
      survivor.get(field_id("part", "name")) == first_part.get(field_id("part", "name"))
      and survivor.get(field_id("part", "list_price")) == first_part.get(field_id("part", "list_price")))
# the new things really work against the provisioned tables
new_part = client.post(f"/api/v1/app-models/{model_map()['part'].id}/records/",
                       payload("part", name="Post-Upgrade Wiper", unit_of_measure="each", list_price="9.00",
                               barcode="5901234123457"), format="json")
check("a record using the NEW field is stored", new_part.status_code == 201, str(new_part.data))
reason = client.post(f"/api/v1/app-models/{model_map()['return_reason'].id}/records/",
                     payload("return_reason", name="Wrong size"), format="json")
check("a record in the NEW model is stored", reason.status_code == 201, str(reason.data))
again = owner_client.post(f"/api/v1/app-instances/{instance.id}/upgrade/{v2.id}/", {}, format="json")
check("re-applying the same version is refused", again.status_code == 400, f"status {again.status_code}")
history = owner_client.get(f"/api/v1/app-instances/{instance.id}/upgrades/")
check("the upgrade is recorded in the history", history.status_code == 200 and history.data["count"] == 1, str(history.data))

# ------------------------------------------------------------------ 4. permissions and ledger are alive
oil = next(r for r in rows(client, "part") if r[field_id("part", "name")] == "Demo Oil Filter")
main = next(r for r in rows(client, "warehouse") if r[field_id("warehouse", "code")] == "MAIN")
over = transact(client, [op("stock_movement", stock_movement_part=oil["id"], stock_movement_warehouse=main["id"],
                            quantity_delta=-100000, movement_type="sale")], "upg-over")
check("overselling is still refused", over.status_code == 400 and "negative" in str(over.data), str(over.data))
cashier_client = api(cashier)
denied = cashier_client.get(f"/api/v1/app-models/{model_map()['supplier'].id}/records/?limit=1")
check("the restricted cashier is still denied on Supplier", denied.status_code == 403, f"status {denied.status_code}")
denied_part = cashier_client.post(f"/api/v1/app-models/{model_map()['part'].id}/records/",
                                  payload("part", name="Intruder"), format="json")
check("the restricted cashier is still denied creating a Part", denied_part.status_code == 403)
customer = rows(client, "customer")[0]
sale = transact(cashier_client, [
    op("sales_order", ref="o", customer=customer["id"], status="confirmed"),
    op("sales_order_line", sales_order_line_sales_order={"$ref": "o"}, sales_order_line_part=oil["id"], quantity=2,
       unit_price="15.00", line_total="30.00"),
    op("stock_movement", stock_movement_part=oil["id"], stock_movement_warehouse=main["id"], quantity_delta=-2,
       movement_type="sale"),
    op("invoice", invoice_number="INV-POST-UPGRADE", invoice_sales_order={"$ref": "o"}, amount_due="30.00",
       status="unpaid")], "upg-cashier-sale")
check("the restricted cashier can still sell on the upgraded instance", sale.status_code == 201, str(sale.data))
receive = transact(client, [op("stock_movement", stock_movement_part=oil["id"], stock_movement_warehouse=main["id"],
                               quantity_delta=10, movement_type="receive")], "upg-receive")
check("a new receive works after the upgrade", receive.status_code == 201, str(receive.data))
now = sum(r[field_id("inventory", "quantity_on_hand")] for r in rows(client, "inventory"))
check(f"stock is exactly {before_stock} - 2 sold + 10 received = {before_stock + 8}", now == before_stock + 8, str(now))
check("ledger reconciles after post-upgrade activity",
      quantity_ledger.reconcile(QuantityLedgerBinding.objects.get(instance=instance)) == [])

print(f"\n{checks - len(failures)}/{checks} checks passed")
if failures:
    print("FAILED:", *failures, sep="\n  ")
    sys.exit(1)
