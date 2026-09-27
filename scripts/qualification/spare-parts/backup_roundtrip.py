"""Backup -> modify -> restore -> verify, for the Spare Parts service application on the qualification stack.

Runs the same commands, in the same order, as the shop kit's Backup and Restore scripts (run_backup; then
sync_service_apps, restore_backup_file --replace for both databases, the stored files, migrate, sync_service_apps) and
checks the application's state through its own API, opened from IntraForge exactly as a user would.
"""
import hashlib
import json
import os
import re
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from e2e_http import Browser, check  # noqa: E402

BACKEND = "intraforge-local-qualification-backend-1"
APP = "/apps/spare-parts/api/v1"
# Written by the Playwright journey (apps/frontend/e2e/spare-parts-service-app.spec.ts).
RESULTS = sys.argv[1] if len(sys.argv) > 1 else "apps/frontend/e2e-results-spare-parts-service-app.json"
run = json.load(open(RESULTS))


def manage(*args, timeout=600):
    out = subprocess.run(["docker", "exec", BACKEND, "python", "manage.py", *args], capture_output=True, text=True, timeout=timeout)
    return out.returncode, out.stdout + out.stderr


def backup(kind):
    code, out = manage("run_backup", kind)
    m = re.search(r"Backup [0-9a-f-]{36} succeeded: (\S+)", out)
    check(f"backup {kind}", code == 0 and m is not None, out[-300:])
    return m.group(1) if m else None


def open_app(b):
    s, _, _ = b.req("GET", "/api/v1/auth/csrf/")
    s, body, _ = b.req("POST", "/api/v1/auth/login/", {"email": run["email"], "password": "correct-horse-battery-9"})
    check("sign in to IntraForge", s == 200, f"{s} {body}")
    s, apps, _ = b.req("GET", "/api/v1/service-apps/")
    app_id = apps["results"][0]["id"]
    s, body, _ = b.req("POST", f"/api/v1/service-apps/{app_id}/launch/")
    check("open Spare Parts", s == 200, f"{s} {body}")
    s, me, _ = b.req("GET", APP + "/auth/me")
    return me["data"]["csrfToken"]


def state(b):
    pid = run["productId"]
    _, product, _ = b.req("GET", f"{APP}/products/{pid}")
    _, stock, _ = b.req("GET", f"{APP}/products/{pid}/stock")
    _, customers, _ = b.req("GET", f"{APP}/customers")
    _, invoices, _ = b.req("GET", f"{APP}/invoices")
    images = product["data"]["images"]
    photo = None
    if images:
        s, raw, _ = b.req("GET", images[0]["url"], raw=True)
        photo = hashlib.sha256(raw).hexdigest() if s == 200 else f"http {s}"
    return {
        "on_hand": sum(x["onHand"] for x in (stock["data"] if isinstance(stock["data"], list) else stock["data"].get("balances", []))),
        "customers": sorted(c["name"] for c in customers["data"]["items"]),
        "invoices": [(i["number"], i["status"]) for i in invoices["data"]["items"]],
        "photos": len(images),
        "photo_sha": photo,
        "price": product["data"]["product"]["priceMinor"],
    }


b = Browser()
csrf = open_app(b)
before = state(b)
print("before:", before)
check("the journey's state is there", before["on_hand"] == 9 and before["photos"] == 1 and before["invoices"], str(before))

# --- back up (control database last: it holds the backup records of the other two)
ids = {k: backup(k) for k in ("tenant_db", "object_storage", "control_db")}

# --- modify: new customer, more stock, the photo removed, a price change
post = lambda method, path, body=None: b.req(method, APP + path, body, headers={"X-CSRF-Token": csrf})
s, _, _ = post("POST", "/customers", {"name": "Should Not Survive Ltd"})
check("modify: add a customer", s == 201)
_, wh, _ = b.req("GET", APP + "/warehouses")
s, _, _ = post("POST", "/inventory/receive", {"productId": run["productId"], "locationId": wh["data"]["locations"][0]["id"], "quantity": 5})
check("modify: receive 5 more", s in (200, 201))
_, product, _ = b.req("GET", f"{APP}/products/{run['productId']}")
s, _, _ = post("DELETE", f"/products/{run['productId']}/images/{product['data']['images'][0]['id']}")
check("modify: delete the photo", s in (200, 204))
s, _, _ = post("PATCH", f"/products/{run['productId']}", {"priceMinor": 99900})
check("modify: change the price", s == 200)
time.sleep(1)
changed = state(b)
print("changed:", changed)
check("the changes are visible before restoring", changed != before, str(changed))

# --- restore exactly as the shop kit's Restore-IntraForgeShop.ps1 does, then let the application reconnect
manage("sync_service_apps")
for kind in ("control_db", "tenant_db", "object_storage"):
    mode = [] if kind == "object_storage" else ["--replace"]
    code, out = manage("restore_backup_file", ids[kind], "--type", kind, *mode, "--yes", timeout=900)
    check(f"restore {kind}", code == 0, out[-400:])
for step in (("migrate", "--noinput"), ("sync_service_apps",)):
    code, out = manage(*step)
    check(" ".join(step) + " after restoring", code == 0, out[-300:])
time.sleep(12)  # introspection (5 s) and configuration (10 s) caches

b2 = Browser()
csrf = open_app(b2)
after = state(b2)
print("after:", after)
for key in ("on_hand", "customers", "invoices", "photos", "photo_sha", "price"):
    check(f"restored: {key}", after[key] == before[key], f"{after[key]} != {before[key]}")
_, integrity, _ = b2.req("GET", APP + "/inventory/integrity")
check("stock ledger integrity after restore", "expected" not in json.dumps(integrity), str(integrity)[:300])

print(f"\n{check.failed} failed")
sys.exit(1 if check.failed else 0)
