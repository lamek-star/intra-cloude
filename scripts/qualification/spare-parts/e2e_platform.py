"""End-to-end check of the Spare Parts service application through the real proxy (qualification stack)."""
import json
import sys
import time
import uuid

from e2e_http import BASE, Browser, check


owner = Browser()
email = f"owner-{uuid.uuid4().hex[:8]}@example.test"
owner.req("GET", "/api/v1/auth/csrf/")
s, b, _ = owner.req("POST", "/api/v1/auth/register/", {"email": email, "password": "Pw-Owner-" + uuid.uuid4().hex[:10], "first_name": "Olivia", "last_name": "Owner"})
check("register owner", s in (200, 201), f"{s} {b}")
s, b, _ = owner.req("GET", "/api/v1/auth/me/")
check("signed in after register", s == 200, f"{s} {b}")
s, org, _ = owner.req("POST", "/api/v1/organizations/", {"name": "Harbour Motors LLC " + uuid.uuid4().hex[:4]})
check("create organization", s == 201, f"{s} {org}")

# --- before install
s, b, _ = owner.req("GET", "/apps/spare-parts/api/v1/health")
check("Spare Parts health through the proxy", s == 200 and b.get("data", {}).get("status") == "ok", f"{s} {b}")
s, b, _ = owner.req("GET", "/apps/spare-parts/api/v1/auth/status")
check("before install the app says it is not installed", s == 503 and b["error"]["code"] == "NOT_INSTALLED", f"{s} {b}")
s, b, _ = owner.req("GET", "/api/v1/internal/service-apps/self/")
check("internal API is not reachable from outside", s == 404, f"{s}")
s, b, _ = owner.req("GET", "/api/v1/internal/service-apps/self/", headers={"X-IntraForge-Service-Token": "x" * 50})
check("internal API not reachable from outside even with a token header", s == 404, f"{s}")
s, lst, _ = owner.req("GET", "/api/v1/service-apps/")
check("Spare Parts is offered for installation", s == 200 and any(a["deployment"] == "spare-parts" for a in lst["available"]), f"{s} {lst}")

# --- install
s, app, _ = owner.req("POST", "/api/v1/service-apps/", {"deployment": "spare-parts", "organization": org["id"], "display_name": "Harbour Motors", "config": {"currency": "AED"}})
check("install", s == 201, f"{s} {app}")
app_id = app["id"]
deadline = time.time() + 60
state = None
while time.time() < deadline:
    s, a, _ = owner.req("GET", f"/api/v1/service-apps/{app_id}/")
    state = a["health"]["state"]
    if state == "running":
        break
    time.sleep(3)
check("status becomes Running (live probe)", state == "running", state)

# --- no second login: Open
s, b, hdrs = owner.req("GET", "/apps/spare-parts/api/v1/auth/me")
check("without Open there is no app session", s == 401, f"{s}")
s, b, hdrs = owner.req("POST", f"/api/v1/service-apps/{app_id}/launch/")
check("Open returns the launch path", s == 200 and b["url"] == "/apps/spare-parts/", f"{s} {b}")
setcookie = hdrs.get("Set-Cookie", "")
check("app cookie is HttpOnly, Secure, SameSite=Strict, path-scoped", all(x in setcookie for x in ["ifapp_spare_parts=", "HttpOnly", "Secure", "SameSite=Strict", "Path=/apps/spare-parts/"]), setcookie)
s, me, _ = owner.req("GET", "/apps/spare-parts/api/v1/auth/me")
check("the app knows the IntraForge user", s == 200 and me["data"]["user"]["email"] == email, f"{s} {me}")
check("organization administrator gets full app permissions", s == 200 and "payments.record" in me["data"]["permissions"] and "products.cost.read" in me["data"]["permissions"])
check("shop name comes from IntraForge", me["data"].get("shopName") == "Harbour Motors", str(me["data"].get("shopName")))
csrf = me["data"]["csrfToken"]

# --- business writes go to IntraForge PostgreSQL, audit relays to IntraForge
app_post = lambda path, body: owner.req("POST", "/apps/spare-parts/api/v1" + path, body, headers={"X-CSRF-Token": csrf})
s, b, _ = owner.req("POST", "/apps/spare-parts/api/v1/customers", {"name": "Walk-in"})
check("state change without the app CSRF token is refused", s == 403, f"{s} {b}")
s, cust, _ = app_post("/customers", {"name": "Al Noor Garage", "phone": "04 555 0101"})
check("create a customer", s == 201, f"{s} {cust}")
s, wh, _ = app_post("/warehouses", {"name": "Main store"})
check("create a warehouse", s == 201, f"{s} {wh}")
time.sleep(3)
s, events, _ = owner.req("GET", f"/api/v1/organizations/{org['id']}/audit/?action=spareparts.customer.create")
if s == 404:
    s, events, _ = owner.req("GET", f"/api/v1/audit/?organization={org['id']}&action=spareparts.customer.create")
found = (events.get("results") if isinstance(events, dict) else events) or []
check("the app's audit event reached IntraForge's audit log", s == 200 and len(found) >= 1, f"{s} {str(events)[:300]}")

# --- logout of IntraForge ends the app session
s, b, _ = owner.req("POST", "/api/v1/auth/logout/")
check("IntraForge logout", s in (200, 204), f"{s} {b}")
time.sleep(6)  # the app caches an introspection for up to 5 s
s, b, _ = owner.req("GET", "/apps/spare-parts/api/v1/auth/me")
check("after IntraForge logout the app session is gone", s == 401, f"{s} {b}")

print(f"\n{check.failed} failed")
print(json.dumps({"org": org["id"], "app": app_id, "owner": email}))
sys.exit(1 if check.failed else 0)
