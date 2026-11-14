"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const { createFake } = require("./fake-intraforge");
const { createStore } = require("../lib/store");
const { createOrders, normalizePhone, normalizeOrderNumber } = require("../lib/orders");

function setup({ vouchers = 2, minutes = 60, fakeOptions = {} } = {}) {
  const fake = createFake(fakeOptions);
  const pkg = fake.add("cafe_packages", { name: "One hour", minutes, price: "25.00", active: true });
  fake.add("cafe_packages", { name: "Hidden", minutes: 30, price: "10.00", active: false });
  for (let i = 0; i < vouchers; i++) {
    fake.add("cafe_vouchers", { code: `CODE-${i}`, minutes, status: "available", order_number: "" });
  }
  let clock = Date.now();
  const store = createStore(fake.client, { cacheMs: 0 });
  const orders = createOrders({ store, client: fake.client, now: () => clock });
  return { fake, store, orders, pkg, advance: (ms) => (clock += ms) };
}

test("phone numbers and order numbers are checked and normalised", () => {
  assert.equal(normalizePhone("0912 345 678"), "0912345678");
  assert.equal(normalizePhone("+251 (91) 234-5678"), "+251912345678");
  assert.equal(normalizePhone("12"), null);
  assert.equal(normalizePhone("<script>"), null);
  assert.equal(normalizeOrderNumber("ic-k7mq-x2vd"), "IC-K7MQ-X2VD");
  assert.equal(normalizeOrderNumber("IC-K7MQ-X2V0"), null); // 0 is not in the alphabet
  assert.equal(normalizeOrderNumber("../../etc"), null);
});

test("the setup check names every missing table, column and unique rule", async () => {
  const fake = createFake({
    tables: { cafe_settings: { key: ["varchar"], value: ["text"] }, cafe_vouchers: { code: ["varchar"] } },
    unique: {},
  });
  const status = await createStore(fake.client).setupStatus();
  assert.equal(status.ready, false);
  const text = status.problems.join("\n");
  assert.match(text, /Table "cafe_packages" is missing/);
  assert.match(text, /Table "cafe_orders" is missing/);
  assert.match(text, /needs a column "minutes"/);
  assert.match(text, /"cafe_vouchers.code" must be unique/);
  assert.match(text, /"cafe_settings.key" must be unique/);
});

test("a complete database is ready, and only active packages are offered", async () => {
  const { store } = setup();
  assert.deepEqual((await store.setupStatus()).ready, true);
  const { packages, settings } = await store.load();
  assert.deepEqual(packages.map((p) => [p.name, p.minutes, p.priceMinor]), [["One hour", 60, 2500]]);
  assert.equal(settings.currency, "IF Credits");
});

test("buying reserves a code, asks IF Pay for the package's price and shows the code only once paid", async () => {
  const { fake, orders, pkg, advance } = setup();
  const order = await orders.create({ packageId: pkg.id, phone: "0912 345 678", amount: 1 });
  assert.match(order.number, /^IC-[0-9A-Z]{4}-[0-9A-Z]{4}$/);
  assert.equal(order.amount, "25.00 IF Credits");
  assert.ok(order.payCode.startsWith("IFPAY1."));
  assert.match(order.qrImage, /^data:image\/svg\+xml;base64,/);
  const payCall = fake.calls.find((c) => c.path === "pay/payment-requests/");
  assert.equal(payCall.body.amountMinor, 2500); // from the package, never the browser
  assert.equal(payCall.body.externalId, order.number);
  const reserved = fake.rows("cafe_vouchers").filter((v) => v.status === "reserved");
  assert.equal(reserved.length, 1);
  assert.equal(reserved[0].order_number, order.number);

  const waiting = await orders.get(order.number);
  assert.equal(waiting.status, "pending");
  assert.equal(waiting.voucher, undefined, "no code before payment");

  fake.markPaid(order.number, "R-77");
  advance(3000); // the page asks every 2.5 s; IF Pay is asked at most every 2 s per order
  const paid = await orders.get(order.number);
  assert.equal(paid.status, "paid");
  assert.equal(paid.voucher, reserved[0].code);
  assert.equal(paid.receipt, "R-77");
  assert.equal(fake.rows("cafe_vouchers").find((v) => v.code === paid.voucher).status, "sold");
  // Asking again changes nothing.
  assert.deepEqual(await orders.get(order.number), paid);
});

test("an expired payment gives the code back", async () => {
  const { fake, orders, pkg, advance } = setup({ vouchers: 1 });
  const order = await orders.create({ packageId: pkg.id, phone: "0912345678" });
  fake.expire(order.number);
  advance(5000);
  const ended = await orders.get(order.number);
  assert.equal(ended.status, "expired");
  assert.equal(ended.voucher, undefined);
  const v = fake.rows("cafe_vouchers")[0];
  assert.equal(v.status, "available");
  assert.equal(fake.rows("cafe_orders")[0].voucher, null);
  // The code can be bought again.
  const again = await orders.create({ packageId: pkg.id, phone: "0912345678" });
  assert.equal(again.status, "pending");
});

test("sold out: no payment is ever asked for", async () => {
  const { fake, orders, pkg } = setup({ vouchers: 0 });
  await assert.rejects(orders.create({ packageId: pkg.id, phone: "0912345678" }), { status: 409, code: "sold_out" });
  assert.equal(fake.calls.filter((c) => c.path === "pay/payment-requests/").length, 0);
});

test("many buyers at once: never more sales than codes, never one code twice", async () => {
  const { fake, orders, pkg } = setup({ vouchers: 2 });
  fake.delayMs = 2;
  const results = await Promise.allSettled(
    Array.from({ length: 6 }, (_, i) => orders.create({ packageId: pkg.id, phone: `091234567${i}` })),
  );
  const ok = results.filter((r) => r.status === "fulfilled");
  assert.equal(ok.length, 2);
  for (const r of results.filter((x) => x.status === "rejected")) assert.equal(r.reason.code, "sold_out");
  const codes = fake.rows("cafe_orders").map((o) => o.voucher).filter(Boolean);
  assert.equal(new Set(codes).size, codes.length);
  assert.equal(fake.calls.filter((c) => c.path === "pay/payment-requests/").length, 2);
});

test("IF Pay not switched on for the website: a clear message and the code goes back", async () => {
  const { fake, orders, pkg } = setup({ vouchers: 1, fakeOptions: {} });
  fake.failPayWith = 403;
  await assert.rejects(orders.create({ packageId: pkg.id, phone: "0912345678" }), { code: "pay_off" });
  assert.equal(fake.rows("cafe_vouchers")[0].status, "available");
  assert.equal(fake.rows("cafe_orders")[0].status, "failed");
  fake.failPayWith = 503;
  await assert.rejects(orders.create({ packageId: pkg.id, phone: "0912345678" }), { code: "pay_down" });
  assert.equal(fake.rows("cafe_vouchers")[0].status, "available");
});

test("the browser cannot choose the price or a package that is not offered", async () => {
  const { orders, fake } = setup();
  const hidden = fake.rows("cafe_packages").find((p) => p.active === false);
  await assert.rejects(orders.create({ packageId: hidden.id, phone: "0912345678" }), { code: "package" });
  await assert.rejects(orders.create({ packageId: "nope", phone: "0912345678" }), { code: "package" });
  await assert.rejects(orders.create({ packageId: fake.rows("cafe_packages")[0].id, phone: "x" }), { code: "phone" });
});

test("finding a code needs the right order number AND phone", async () => {
  const { fake, orders, pkg } = setup();
  const order = await orders.create({ packageId: pkg.id, phone: "0912 345 678" });
  fake.markPaid(order.number);
  await assert.rejects(orders.lookup({ number: order.number, phone: "0999999999" }), { status: 404 });
  await assert.rejects(orders.lookup({ number: "IC-2222-2222", phone: "0912345678" }), { status: 404 });
  const found = await orders.lookup({ number: order.number.toLowerCase(), phone: "0912345678" });
  assert.equal(found.status, "paid");
  assert.ok(found.voucher);
});

test("the sweep frees codes held by orders that will never be paid", async () => {
  const { fake, orders, store, pkg, advance } = setup({ vouchers: 3 });
  // 1. A code marked reserved with no order at all (a restart in the middle).
  fake.rows("cafe_vouchers")[0].status = "reserved";
  fake.rows("cafe_vouchers")[0].order_number = "IC-AAAA-AAAA";
  // 2. An order stuck in "new" that holds a code in its unique column.
  const stuck = fake.add("cafe_orders", {
    number: "IC-BBBB-BBBB", phone: "0912345678", package_name: "One hour", minutes: 60, amount: "25.00",
    status: "new", pay_request: "", receipt: "", voucher: "CODE-1", created_at: new Date().toISOString(),
  });
  fake.rows("cafe_vouchers")[1].status = "reserved";
  fake.rows("cafe_vouchers")[1].order_number = stuck.number;
  // 3. A waiting order whose payment expired.
  const waiting = await orders.create({ packageId: pkg.id, phone: "0912345678" });
  fake.expire(waiting.number);

  advance(6 * 60_000);
  await orders.sweep();
  assert.deepEqual(fake.rows("cafe_vouchers").map((v) => v.status), ["available", "available", "available"]);
  assert.equal(fake.rows("cafe_orders").find((o) => o.number === stuck.number).voucher, null);
  assert.equal(fake.rows("cafe_orders").find((o) => o.number === waiting.number).status, "expired");
  assert.equal(await store.availableCount(60), 3);
});

test("the sweep never takes back a code that was paid for", async () => {
  const { fake, orders, pkg, advance } = setup({ vouchers: 1 });
  const order = await orders.create({ packageId: pkg.id, phone: "0912345678" });
  fake.markPaid(order.number);
  advance(10 * 60_000);
  await orders.sweep();
  const voucher = fake.rows("cafe_vouchers")[0];
  assert.equal(voucher.status, "sold");
  assert.equal((await orders.get(order.number)).voucher, voucher.code);
});

test("only an image address ever reaches the page as the QR", () => {
  const { qrImage } = require("../lib/orders");
  assert.equal(qrImage("data:image/svg+xml;base64,PHN2Zy8+"), "data:image/svg+xml;base64,PHN2Zy8+");
  assert.match(qrImage("<svg xmlns='http://www.w3.org/2000/svg'/>"), /^data:image\/svg\+xml;base64,/);
  assert.equal(qrImage("javascript:alert(1)"), null);
  assert.equal(qrImage("data:text/html;base64,PHNjcmlwdD4="), null);
  assert.equal(qrImage("data:image/svg+xml;base64,PHN2Zy8+\" onerror=\"x"), null);
  assert.equal(qrImage(undefined), null);
});
