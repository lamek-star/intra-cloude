"""Real end-to-end latency of the endpoints the screens use: host -> Caddy (TLS) -> gunicorn -> PostgreSQL.

    python http_latency.py <base-url> <email> <password> <instance-id>

Uses ONE real login and a real session cookie, and stays under the configured per-user rate limit
(300/min) on purpose -- nothing is bypassed here. Prints one JSON line per endpoint.
"""

import http.client
import json
import socket
import ssl
import statistics
import sys
import time
import urllib.parse

base, email, password, instance = sys.argv[1:5]
parsed = urllib.parse.urlparse(base)
context = ssl.create_default_context()
context.check_hostname = False
context.verify_mode = ssl.CERT_NONE  # Caddy's internal CA (local-first appliance)
cookies: dict[str, str] = {}


class KeepAliveConnection(http.client.HTTPSConnection):
    """One persistent TLS connection, like a browser's. It dials 127.0.0.1 directly: Python has no
    'happy eyeballs', so `localhost` costs ~2 s per new connection on Windows while it tries ::1 first --
    a client artefact, not the server (curl, which does have it, sees ~0.2 s). SNI stays 'localhost'."""

    def connect(self):
        raw = socket.create_connection(("127.0.0.1", parsed.port or 443), timeout=30)
        self.sock = context.wrap_socket(raw, server_hostname=parsed.hostname)


connection = KeepAliveConnection(parsed.hostname, parsed.port or 443, context=context)


def csrf():
    return cookies.get("csrftoken", "")


def call(method, path, body=None, headers=None):
    data = None if body is None else json.dumps(body).encode()
    request_headers = {"Content-Type": "application/json", "X-CSRFToken": csrf(), "Referer": base + "/",
                       "Origin": base, "Cookie": "; ".join(f"{k}={v}" for k, v in cookies.items()), **(headers or {})}
    connection.request(method, "/api/v1" + urllib.parse.quote(path, safe="/?&=:%"), body=data, headers=request_headers)
    response = connection.getresponse()
    payload = response.read()
    for header, value in response.getheaders():
        if header.lower() == "set-cookie":
            name, _, rest = value.partition("=")
            cookies[name] = rest.split(";")[0]
    return response.status, payload


call("GET", "/auth/csrf/")
status, _ = call("POST", "/auth/login/", {"email": email, "password": password})
assert status == 200, status

schema = json.loads(call("GET", f"/app-instances/{instance}/schema/")[1])
models = {m["key"]: m for m in schema["models"]}
rels = {(r["source_model"], r["key"]): r["id"] for r in schema["relationships"]}


def fid(model, key):
    found = next((f["id"] for f in models[model]["fields"] if f["key"] == key), None)
    return found or rels[(models[model]["id"], key)]


def records(model):
    return f"/app-models/{models[model]['id']}/records/"


def first(model, offset=0):
    return json.loads(call("GET", records(model) + f"?limit=1&offset={offset}")[1])["results"][0]


part = first("part", 2500)
number = first("part_number", 5000)[fid("part_number", "number")]
variant = number.replace("-", "").replace(" ", "").lower()
warehouse = first("warehouse")["id"]
customer = first("customer")["id"]


def measure(label, fn, n=12):
    fn()  # warm-up
    times, size = [], 0
    for _ in range(n):
        started = time.perf_counter()
        status, payload = fn()
        times.append((time.perf_counter() - started) * 1000)
        size = len(payload)
        assert status in (200, 201), (label, status)
    times.sort()
    print(json.dumps({"kind": "http", "label": label, "n": n, "p50_ms": round(statistics.median(times), 1),
                      "p95_ms": round(times[min(n - 1, int(round(0.95 * (n - 1))))], 1), "max_ms": round(times[-1], 1),
                      "bytes": size}), flush=True)
    time.sleep(1.5)  # stay far under the per-user limit


measure("product list (50)", lambda: call("GET", records("part") + "?limit=50"))
measure("product search by name", lambda: call("GET", records("part") + "?search=Oil%20Filter%20025&limit=8"))
measure("part-number search, normalized", lambda: call("GET", records("part_number") + f"?search={variant}&limit=8"))
measure("inventory list (50)", lambda: call("GET", records("inventory") + "?limit=50"))
measure("stock lookup, one product", lambda: call("GET", records("inventory") + f"?{fid('inventory', 'part')}={part['id']}&limit=50"))
measure("movement history, one product", lambda: call(
    "GET", records("stock_movement") + f"?{fid('stock_movement', 'stock_movement_part')}={part['id']}&ordering=-{fid('stock_movement', 'occurred_at')}&limit=25"))
measure("application schema", lambda: call("GET", f"/app-instances/{instance}/schema/"))


def stamp():
    return time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime())


def receive():
    body = {"part": part["id"], "warehouse": warehouse, "quantity": 1, "occurred_at": stamp()}
    return call("POST", f"/app-instances/{instance}/operations/receive/", body,
                {"Idempotency-Key": f"http-receive-{time.time_ns()}"})


def sale(line_count=1):
    body = {
        "customer": customer,
        "invoice_number": f"INV-HTTP-{time.time_ns()}",
        "occurred_at": stamp(),
        "lines": [{"part": part["id"], "warehouse": warehouse, "quantity": 1, "unit_price": "15.50"}] * line_count,
    }
    return call("POST", f"/app-instances/{instance}/operations/sell/", body,
                {"Idempotency-Key": f"http-sale-{time.time_ns()}"})


measure("RECEIVE (controlled operation)", receive, n=15)
# Sales consume stock and the ledger (correctly) refuses an oversell, so top the part up before measuring them.
status_, _payload = call("POST", f"/app-instances/{instance}/operations/receive/",
                         {"part": part["id"], "warehouse": warehouse, "quantity": 500, "occurred_at": stamp()},
                         {"Idempotency-Key": f"http-topup-{time.time_ns()}"})
assert status_ == 201, status_
measure("SALE (controlled operation, 1 line)", sale, n=15)
measure("SALE (controlled operation, 5 lines)", lambda: sale(5), n=10)
