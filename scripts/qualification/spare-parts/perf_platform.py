"""Performance of the Spare Parts service application through IntraForge (qualification stack, real proxy, PostgreSQL).

    PERF_ROWS=20000 python perf_platform.py [base-url]   (run reset_slot.sh first; it installs a fresh Spare Parts)

Measures: a reference-catalogue CSV import of <rows> rows (detect, stage, commit, until COMPLETED), then search latency
through the proxy for exact, differently-formatted and text queries, and a few list/report pages. Prints JSON.
"""

import json
import os
import statistics
import sys
import time
import urllib.request
import uuid

from e2e_http import BASE, Browser, check

ROWS = int(os.environ.get("PERF_ROWS", "20000"))
APP = "/apps/spare-parts/api/v1"


def multipart(fields: dict[str, str], file_field: str, filename: str, content: bytes) -> tuple[bytes, str]:
    boundary = "----perf" + uuid.uuid4().hex
    parts = []
    for k, v in fields.items():
        parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode())
    parts.append(
        f'--{boundary}\r\nContent-Disposition: form-data; name="{file_field}"; filename="{filename}"\r\n'
        f"Content-Type: text/csv\r\n\r\n".encode()
        + content
        + b"\r\n"
    )
    parts.append(f"--{boundary}--\r\n".encode())
    return b"".join(parts), f"multipart/form-data; boundary={boundary}"


def post_form(browser: Browser, path: str, fields: dict[str, str], content: bytes, csrf: str):
    body, ctype = multipart(fields, "file", "catalogue.csv", content)
    r = urllib.request.Request(
        BASE + path,
        data=body,
        method="POST",
        headers={"Content-Type": ctype, "X-CSRF-Token": csrf, "Origin": BASE, "Referer": BASE + "/"},
    )
    with browser.opener.open(r, timeout=600) as resp:
        return resp.status, json.loads(resp.read())


def catalogue_csv(n: int) -> bytes:
    makers = ["Toyota", "Nissan", "Honda", "Mitsubishi", "Mazda", "Subaru", "Suzuki", "Isuzu"]
    things = ["Oil Pan Assembly", "Filter Sub-Assy Oil", "Pump Assy Water", "Gasket Cylinder Head", "Bearing Hub Rear",
              "Pad Kit Disc Brake", "Belt V-Ribbed", "Sensor Oxygen", "Mount Engine Front", "Seal Oil Crankshaft"]
    lines = ["oem_number,description,manufacturer,category,market,source"]
    for i in range(n):
        lines.append(f"{10000 + i // 97:05d}-{i % 97:02d}{i % 10}{(i * 7) % 10}0,{things[i % 10]} {i},{makers[i % 8]},Engine,JP,perf")
    return ("\n".join(lines) + "\n").encode()


def timed(fn, repeat: int = 1):
    samples = []
    result = None
    for _ in range(repeat):
        t = time.perf_counter()
        result = fn()
        samples.append((time.perf_counter() - t) * 1000)
    return result, samples


owner = Browser()
owner.req("GET", "/api/v1/auth/csrf/")
s, _, _ = owner.req("POST", "/api/v1/auth/register/", {"email": f"perf-{uuid.uuid4().hex[:8]}@example.test", "password": "Pw-Perf-" + uuid.uuid4().hex[:10], "first_name": "P", "last_name": "Erf"})
check("register", s in (200, 201))
s, org, _ = owner.req("POST", "/api/v1/organizations/", {"name": "Perf Motors " + uuid.uuid4().hex[:4]})
s, app, _ = owner.req("POST", "/api/v1/service-apps/", {"deployment": "spare-parts", "organization": org["id"], "display_name": "Perf Motors", "config": {"currency": "AED"}})
check("install", s == 201, f"{s} {app}")
time.sleep(5)
owner.req("POST", f"/api/v1/service-apps/{app['id']}/launch/")
s, me, _ = owner.req("GET", APP + "/auth/me")
csrf = me["data"]["csrfToken"]

content = catalogue_csv(ROWS)
t0 = time.perf_counter()
s, det = post_form(owner, APP + "/catalogue/import/detect", {}, content, csrf)
detect_ms = (time.perf_counter() - t0) * 1000
check("detect", s == 200 and det["data"]["rowCount"] == ROWS, str(det)[:300])
t1 = time.perf_counter()
s, staged = post_form(owner, APP + "/catalogue/import/jobs", {"mapping": json.dumps(det["data"]["suggestedMapping"]), "attested": "true"}, content, csrf)
stage_ms = (time.perf_counter() - t1) * 1000
check("stage", s == 201, str(staged)[:300])
job_id = staged["data"]["id"]
t2 = time.perf_counter()
s, done, _ = owner.req("POST", f"{APP}/catalogue/import/jobs/{job_id}/commit", {}, headers={"X-CSRF-Token": csrf})
status = done.get("data", {}).get("status") if isinstance(done, dict) else None
deadline = time.time() + 3600
while status not in ("COMPLETED", "COMPLETED_WITH_WARNINGS", "FAILED") and time.time() < deadline:
    time.sleep(5)
    s, job, _ = owner.req("GET", f"{APP}/catalogue/import/jobs/{job_id}")
    status = job["data"]["status"]
commit_s = time.perf_counter() - t2
check("import completed", status in ("COMPLETED", "COMPLETED_WITH_WARNINGS"), str(status))

queries = {
    "exact number": "10050-4",
    "number without dash": "100504",
    "lower-case text": "oil pan assembly 12345",
    "one word": "gasket",
    "maker + word": "toyota pump",
}
search = {}
for label, q in queries.items():
    (res, samples) = timed(lambda q=q: owner.req("GET", f"{APP}/catalogue/search?q={urllib.request.quote(q)}"), repeat=7)
    samples = samples[1:]  # the first request warms the statement cache
    search[label] = {"query": q, "hits": res[1]["data"]["total"] if res[0] == 200 else f"HTTP {res[0]}", "median_ms": round(statistics.median(samples), 1), "max_ms": round(max(samples), 1)}
pages = {}
for label, path in {"products list": "/products?pageSize=50", "dashboard": "/reports/dashboard", "catalogue page 200": "/catalogue/search?q=&page=200"}.items():
    (res, samples) = timed(lambda path=path: owner.req("GET", APP + path), repeat=5)
    pages[label] = {"status": res[0], "median_ms": round(statistics.median(samples[1:]), 1)}

print(json.dumps({
    "rows": ROWS, "csv_bytes": len(content),
    "detect_ms": round(detect_ms), "stage_ms": round(stage_ms), "commit_seconds": round(commit_s, 1),
    "rows_per_second_commit": round(ROWS / commit_s, 1) if commit_s else None,
    "search": search, "pages": pages,
}, indent=2))
sys.exit(1 if check.failed else 0)
