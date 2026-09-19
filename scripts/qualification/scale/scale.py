"""Scale qualification -- generate a large Spare Parts business, then measure it (via `manage.py shell`).

    SCALE_MODE=generate   ~5,000 products, 10,000 part numbers, 10,000 stock movements, plus suppliers,
                          customers and warehouses, built through the SAME services the API uses
                          (validation, unique/composite constraints, quantity-ledger triggers, audit) --
                          never raw INSERTs and never through a browser
    SCALE_MODE=measure    latency (p50/p95/max), query counts and payload sizes of the endpoints the
                          screens use, table/index facts, and EXPLAIN (ANALYZE, BUFFERS) of the slow ones

Only ever run against the disposable qualification stack (see run-scale.sh).
"""

import json
import os
import random
import statistics
import time
from datetime import datetime, timedelta

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.db import connections
from django.test.utils import CaptureQueriesContext
from rest_framework.test import APIClient

from app_platform import instances, provisioning, records, templates, transactions
from app_platform.models import AppInstance
from app_platform.reference_templates.spare_parts import spare_parts_reference_definition
from app_platform.runtime_plan import plan_runtime
from app_platform.tests.test_foundation import project_for
from organizations.models import Organization
from organizations.services import create_organization

User = get_user_model()
MODE = os.environ.get("SCALE_MODE", "measure")
TAG = os.environ.get("SCALE_TAG", "")  # a smoke run uses its own tag so it never collides with the real dataset
OWNER = (f"scale-owner{TAG}@example.com", "Scale-Owner-Pass-2026!")
ORG = f"Scale Qualification Shop{TAG}"
PRODUCTS = int(os.environ.get("SCALE_PRODUCTS", "5000"))
SUPPLIERS, CUSTOMERS = 50, 500
WAREHOUSES = [("Main Warehouse", "MAIN"), ("Shop Floor", "FLOOR"), ("Yard", "YARD"), ("Depot", "DEPOT")]
KINDS = ["Oil Filter", "Air Filter", "Brake Pad Set", "Spark Plug", "Wiper Blade", "Timing Belt", "Fuel Pump",
         "Water Pump", "Alternator", "Battery", "Shock Absorber", "Clutch Kit", "Radiator Hose", "Wheel Bearing"]
NOW = datetime(2026, 9, 19, 12, 0, 0)


def out(kind, **data):
    print(json.dumps({"kind": kind, **data}, default=str), flush=True)


def api(user):
    client = APIClient()
    client.defaults["HTTP_X_FORWARDED_PROTO"] = "https"
    client.force_authenticate(user)
    return client


class Fields:
    def __init__(self, instance):
        self.instance = instance
        self.models = {m.key: m for m in instance.models.all()}
        self._cache = {}

    def did(self, model_key, key):
        if (model_key, key) not in self._cache:
            model = self.models[model_key]
            field = model.fields.filter(key=key).first()
            self._cache[(model_key, key)] = str(field.id if field is not None else model.outgoing.get(key=key).id)
        return self._cache[(model_key, key)]

    def payload(self, model_key, **values):
        return {self.did(model_key, k): v for k, v in values.items()}

    def op(self, model_key, ref=None, **values):
        item = {"op": "create", "model": str(self.models[model_key].id), "data": self.payload(model_key, **values)}
        if ref:
            item["ref"] = ref
        return item


def stamp(days_ago, minute=0):
    return (NOW - timedelta(days=days_ago, minutes=minute)).strftime("%Y-%m-%dT%H:%M:%S")


def get_instance():
    org = Organization.objects.get(name=ORG)
    return org, AppInstance.objects.filter(organization=org).first()


def generate():
    random.seed(20260919)
    call_command("seed_permissions", verbosity=0)
    owner = User.objects.create_user(email=OWNER[0], password=OWNER[1])
    org = create_organization(name=ORG, created_by=owner)
    project = project_for(owner, org)
    template = templates.create_template(owner, org, {"label": "Spare Parts", "draft": spare_parts_reference_definition()})
    version = templates.publish_template(owner, template)
    instance = instances.install(owner, project, {"label": "Spare Parts", "template_version": str(version.id)})
    plan = plan_runtime(owner, instance)
    provisioning.reserve(owner, instance, plan["fingerprint"])
    provisioning.execute(instance.id, owner)
    f = Fields(instance)

    def create(model_key, **values):
        return records.create_record(owner, f.models[model_key], f.payload(model_key, **values))

    t0 = time.time()
    warehouses = [create("warehouse", name=n, code=c)["id"] for n, c in WAREHOUSES]
    for i in range(SUPPLIERS):
        create("supplier", name=f"Supplier {i:03d}")
    customers = [create("customer", name=f"Customer {i:04d}")["id"] for i in range(CUSTOMERS)]
    out("phase", name="reference data", seconds=round(time.time() - t0, 1))

    t0 = time.time()
    parts = []
    for i in range(PRODUCTS):
        row = create("part", name=f"{KINDS[i % len(KINDS)]} {i:05d}", unit_of_measure="each",
                     list_price=f"{10 + (i % 90)}.50", standard_cost=f"{5 + (i % 40)}.25")
        parts.append((row["id"], 10 + (i % 90)))
        if (i + 1) % 1000 == 0:
            out("progress", what="products", done=i + 1, seconds=round(time.time() - t0, 1))
    out("phase", name="products", count=len(parts), seconds=round(time.time() - t0, 1))

    t0 = time.time()
    numbers = 0
    for i, (part_id, _) in enumerate(parts):
        create("part_number", number=f"{10000 + (i * 7) % 89999:05d}-{i:05d}", source="OEM", part_number_part=part_id)
        create("part_number", number=f"AM {i:05d} {KINDS[i % len(KINDS)][:3].upper()}", source="Aftermarket",
               part_number_part=part_id)
        numbers += 2
        if numbers % 2000 == 0:
            out("progress", what="part numbers", done=numbers, seconds=round(time.time() - t0, 1))
    out("phase", name="part numbers", count=numbers, seconds=round(time.time() - t0, 1))

    # 5,000 receives (one per product, in batched atomic transactions) ...
    t0 = time.time()
    received = {}
    for start in range(0, len(parts), 25):
        ops = []
        for i in range(start, min(start + 25, len(parts))):
            qty = 60 + (i % 140)
            received[parts[i][0]] = qty
            ops.append(f.op("stock_movement", stock_movement_part=parts[i][0], stock_movement_warehouse=warehouses[0],
                            quantity_delta=qty, movement_type="receive", reference=f"DN-{i:05d}",
                            occurred_at=stamp(60 + i % 30, i % 600)))
        transactions.run(owner, instance, {"operations": ops}, idempotency_key=f"scale-receive-{start}")
        if (start + 25) % 1000 == 0:
            out("progress", what="receive movements", done=start + 25, seconds=round(time.time() - t0, 1))
    out("phase", name="receives", count=len(parts), seconds=round(time.time() - t0, 1))

    # ... and 5,000 sale movements (2,500 sales of two lines each: order + lines + movements + invoice).
    t0 = time.time()
    sales = len(parts) // 2
    for j in range(sales):
        pair = (parts[2 * j], parts[2 * j + 1])
        qty = [1 + (j % 5), 1 + ((j + 2) % 5)]
        total = sum(q * p[1] for q, p in zip(qty, pair))
        ops = [f.op("sales_order", ref="order", customer=customers[j % CUSTOMERS], status="confirmed",
                    order_date=stamp(30 - j % 30)[:10], total_amount=f"{total}.50")]
        for line, (part_id, price), q in zip(range(2), pair, qty):
            ops.append(f.op("sales_order_line", sales_order_line_sales_order={"$ref": "order"},
                            sales_order_line_part=part_id, quantity=q, unit_price=f"{price}.50",
                            line_total=f"{q * price}.50"))
            ops.append(f.op("stock_movement", stock_movement_part=part_id, stock_movement_warehouse=warehouses[0],
                            quantity_delta=-q, movement_type="sale", reference=f"INV-SCALE-{j:05d}",
                            occurred_at=stamp(30 - j % 30, j % 600)))
        ops.append(f.op("invoice", invoice_number=f"INV-SCALE-{j:05d}", invoice_sales_order={"$ref": "order"},
                        amount_due=f"{total}.50", status="unpaid"))
        transactions.run(owner, instance, {"operations": ops}, idempotency_key=f"scale-sale-{j}")
        if (j + 1) % 250 == 0:
            out("progress", what="sales", done=j + 1, seconds=round(time.time() - t0, 1))
    out("phase", name="sales", count=sales, movements=sales * 2, seconds=round(time.time() - t0, 1))
    out("done", instance=str(instance.id), org=str(org.id))


# ------------------------------------------------------------------ measurement


def percentile(values, p):
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int(round(p / 100 * (len(ordered) - 1))))]


def timed(label, call, n=15, warm=2, note=""):
    """Runs `call` warm+n times; the timed runs also count queries on both databases and response bytes."""
    for _ in range(warm):
        call()
    durations, queries, sizes = [], [], []
    for _ in range(n):
        with CaptureQueriesContext(connections["default"]) as control, CaptureQueriesContext(connections["tenant"]) as tenant:
            started = time.perf_counter()
            response = call()
            durations.append((time.perf_counter() - started) * 1000)
        queries.append((len(control), len(tenant)))
        sizes.append(len(response.content) if hasattr(response, "content") else 0)
        assert response.status_code in (200, 201), (label, response.status_code, getattr(response, "data", None))
    out("measure", label=label, n=n, p50_ms=round(statistics.median(durations), 1),
        p95_ms=round(percentile(durations, 95), 1), max_ms=round(max(durations), 1),
        queries_control=queries[-1][0], queries_tenant=queries[-1][1], bytes=sizes[-1], note=note)
    return response


def explain(label, sql_text):
    with connections["tenant"].cursor() as cursor:
        cursor.execute("EXPLAIN (ANALYZE, BUFFERS, COSTS OFF, TIMING OFF) " + sql_text)
        plan = [row[0] for row in cursor.fetchall()]
    out("plan", label=label, plan=plan)


def measure():
    # Measures endpoint COST, not rate limiting: in THIS shell process only, the per-user throttle is
    # bypassed so a few hundred timed requests are not answered with 429. Deployed settings are untouched
    # (the qualification stack keeps its configured limits; the real-HTTP run in http_latency.py obeys them).
    from rest_framework.throttling import SimpleRateThrottle

    SimpleRateThrottle.allow_request = lambda self, request, view: True
    org, instance = get_instance()
    owner = User.objects.get(email=OWNER[0])
    client = api(owner)
    f = Fields(instance)
    model = {k: str(m.id) for k, m in f.models.items()}
    base = "/api/v1/app-models"

    with connections["tenant"].cursor() as cursor:
        cursor.execute("SELECT version()")
        out("environment", postgres=cursor.fetchone()[0])
        cursor.execute(
            "SELECT schemaname, relname, n_live_tup, pg_total_relation_size(relid) "
            "FROM pg_stat_user_tables ORDER BY n_live_tup DESC LIMIT 20"
        )
        out("tables", rows=[[str(c) for c in r] for r in cursor.fetchall()])
        cursor.execute("SELECT count(*) FROM pg_stat_user_tables")
        cursor.execute(
            "SELECT tablename, indexname, indexdef FROM pg_indexes "
            "WHERE schemaname NOT IN ('pg_catalog','information_schema') ORDER BY tablename, indexname"
        )
        out("indexes", rows=[list(r) for r in cursor.fetchall()])

    part_count = client.get(f"{base}/{model['part']}/records/?limit=1").data["count"]
    number_count = client.get(f"{base}/{model['part_number']}/records/?limit=1").data["count"]
    movement_count = client.get(f"{base}/{model['stock_movement']}/records/?limit=1").data["count"]
    out("dataset", products=part_count, part_numbers=number_count, movements=movement_count)
    part_sample = client.get(f"{base}/{model['part']}/records/?limit=1&offset={part_count // 2}").data["results"][0]
    part_id = part_sample["id"]
    part_name = part_sample[f.did("part", "name")]
    oem = client.get(f"{base}/{model['part_number']}/records/?limit=1&offset={number_count // 2}").data["results"][0]
    oem_number = oem[f.did("part_number", "number")]
    variant = oem_number.replace("-", "").lower()  # 04465-0K290 typed as 044650k290

    timed("product list, first page (50)", lambda: client.get(f"{base}/{model['part']}/records/?limit=50"))
    timed(f"product list, deep page (offset {max(0, part_count - 50)})", lambda: client.get(f"{base}/{model['part']}/records/?limit=50&offset={max(0, part_count - 50)}"))
    timed("product search by name (`Oil Filter 025`)", lambda: client.get(f"{base}/{model['part']}/records/?search=Oil%20Filter%20025&limit=8"))
    timed("part-number search, exact (`%s`)" % oem_number, lambda: client.get(f"{base}/{model['part_number']}/records/?search={oem_number}&limit=8"))
    timed("part-number search, normalized (`%s`)" % variant, lambda: client.get(f"{base}/{model['part_number']}/records/?search={variant}&limit=8"))
    timed("part-number search, no match", lambda: client.get(f"{base}/{model['part_number']}/records/?search=ZZZ99999&limit=8"))
    timed("part numbers of one product", lambda: client.get(f"{base}/{model['part_number']}/records/?{f.did('part_number', 'part_number_part')}={part_id}&limit=25"))
    timed("inventory list, first page (50)", lambda: client.get(f"{base}/{model['inventory']}/records/?limit=50"))
    timed("stock lookup for one product", lambda: client.get(f"{base}/{model['inventory']}/records/?{f.did('inventory', 'part')}={part_id}&limit=50"))
    timed("movement history of one product", lambda: client.get(
        f"{base}/{model['stock_movement']}/records/?{f.did('stock_movement', 'stock_movement_part')}={part_id}&ordering=-{f.did('stock_movement', 'occurred_at')}&limit=25"))
    timed("recent movements, all products (25)", lambda: client.get(f"{base}/{model['stock_movement']}/records/?ordering=-{f.did('stock_movement', 'occurred_at')}&limit=25"))
    timed("sales list, first page", lambda: client.get(f"{base}/{model['sales_order']}/records/?ordering=-{f.did('sales_order', 'order_date')}&limit=25"))
    timed("invoice lookup by number", lambda: client.get(f"{base}/{model['invoice']}/records/?search=INV-SCALE-01234&limit=5"))
    timed("home dashboard: six counts", lambda: [client.get(f"{base}/{model[k]}/records/?limit=1") for k in
          ("part", "part_number", "warehouse", "supplier", "customer", "sales_order")][-1], note="six requests, one shown")
    timed("application schema (one request)", lambda: client.get(f"/api/v1/app-instances/{instance.id}/schema/"))

    warehouse_id = client.get(f"{base}/{model['warehouse']}/records/?limit=1").data["results"][0]["id"]
    customer_id = client.get(f"{base}/{model['customer']}/records/?limit=1").data["results"][0]["id"]
    counter = {"n": 0}

    def receive():
        counter["n"] += 1
        return client.post(
            f"/api/v1/app-instances/{instance.id}/transactions/",
            {"operations": [f.op("stock_movement", stock_movement_part=part_id, stock_movement_warehouse=warehouse_id,
                                 quantity_delta=2, movement_type="receive", reference=f"MEASURE-R-{counter['n']}",
                                 occurred_at=stamp(0))]},
            format="json", HTTP_IDEMPOTENCY_KEY=f"measure-receive-{time.time_ns()}")

    def sale():
        counter["n"] += 1
        ops = [f.op("sales_order", ref="o", customer=customer_id, status="confirmed", order_date="2026-09-19", total_amount="15.50"),
               f.op("sales_order_line", sales_order_line_sales_order={"$ref": "o"}, sales_order_line_part=part_id,
                    quantity=1, unit_price="15.50", line_total="15.50"),
               f.op("stock_movement", stock_movement_part=part_id, stock_movement_warehouse=warehouse_id,
                    quantity_delta=-1, movement_type="sale", reference=f"MEASURE-S-{counter['n']}", occurred_at=stamp(0)),
               f.op("invoice", invoice_number=f"INV-MEASURE-{time.time_ns()}", invoice_sales_order={"$ref": "o"},
                    amount_due="15.50", status="unpaid")]
        return client.post(f"/api/v1/app-instances/{instance.id}/transactions/", {"operations": ops}, format="json",
                           HTTP_IDEMPOTENCY_KEY=f"measure-sale-{time.time_ns()}")

    timed("RECEIVE (1 movement, atomic transaction)", receive, n=25)
    timed("SALE (order + line + movement + invoice, atomic)", sale, n=25)

    # Query plans for the statements the screens depend on (captured from the real code path).
    plans = {
        "name search": f"{base}/{model['part']}/records/?search=Oil%20Filter%20025&limit=8",
        "normalized part-number search": f"{base}/{model['part_number']}/records/?search={variant}&limit=8",
        "movement history of one product": f"{base}/{model['stock_movement']}/records/?{f.did('stock_movement', 'stock_movement_part')}={part_id}&ordering=-{f.did('stock_movement', 'occurred_at')}&limit=25",
        "stock lookup for one product": f"{base}/{model['inventory']}/records/?{f.did('inventory', 'part')}={part_id}&limit=50",
        "recent movements": f"{base}/{model['stock_movement']}/records/?ordering=-{f.did('stock_movement', 'occurred_at')}&limit=25",
    }
    for label, url in plans.items():
        with CaptureQueriesContext(connections["tenant"]) as captured:
            client.get(url)
        for entry in captured.captured_queries:
            statement = entry["sql"]
            if statement.lstrip().upper().startswith("SELECT") and "COUNT(*)" not in statement.upper():
                explain(label, statement)


if MODE == "generate":
    generate()
elif MODE == "measure":
    measure()
else:
    raise SystemExit(f"unknown SCALE_MODE {MODE!r}")
