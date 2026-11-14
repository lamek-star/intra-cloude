"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const http = require("node:http");
const { createFake } = require("./fake-intraforge");
const { createStore } = require("../lib/store");
const { createOrders } = require("../lib/orders");
const { createApp, walletUrl } = require("../server");

const TOKEN = "pdc_sk_TEST_TOKEN_THAT_MUST_NEVER_LEAK";

async function start(fake) {
  // The token is only inside the client; wrap the fake so every IntraForge call "carries" it like the real one.
  const store = createStore(fake.client, { cacheMs: 0 });
  const orders = createOrders({ store, client: fake.client });
  const server = http.createServer(createApp({ store, orders }));
  await new Promise((r) => server.listen(0, "127.0.0.1", r));
  const base = `http://127.0.0.1:${server.address().port}`;
  return { server, base };
}

function seeded() {
  const fake = createFake();
  const pkg = fake.add("cafe_packages", { name: "One hour", minutes: 60, price: "25.00", active: true });
  fake.add("cafe_vouchers", { code: "SECRET-CODE-1", minutes: 60, status: "available", order_number: "" });
  fake.add("cafe_settings", { key: "cafe_name", value: "Test Café" });
  fake.add("cafe_settings", { key: "wallet_url", value: "https://cafe.lan:8443/apps/pay-1/wallet" });
  return { fake, pkg };
}

test("pages carry strict security headers and the site's files only", async (t) => {
  const { fake } = seeded();
  const { server, base } = await start(fake);
  t.after(() => server.close());
  const home = await fetch(`${base}/`);
  assert.equal(home.status, 200);
  assert.match(home.headers.get("content-security-policy"), /default-src 'self'/);
  assert.match(home.headers.get("content-security-policy"), /frame-ancestors 'none'/);
  assert.equal(home.headers.get("x-content-type-options"), "nosniff");
  assert.match(await home.text(), /<title>/);
  for (const path of ["/../server.js", "/%2e%2e/server.js", "/..%2flib/intraforge.js", "/lib/intraforge.js", "/%E0%A4%A"]) {
    const res = await fetch(`${base}${path}`);
    const body = await res.text();
    assert.ok(!body.includes("IF_API_TOKEN") && !body.includes("require("), `${path} must not reveal server code`);
  }
  const css = await fetch(`${base}/styles.css`);
  assert.equal(css.headers.get("content-type"), "text/css; charset=utf-8");
  assert.equal((await fetch(`${base}/`, { method: "DELETE" })).status, 405);
});

test("info shows the café and prices, never the wallet setting row or a code", async (t) => {
  const { fake } = seeded();
  const { server, base } = await start(fake);
  t.after(() => server.close());
  const res = await fetch(`${base}/api/info`, { headers: { host: "cafe.lan:8445" } });
  const text = await res.text();
  const info = JSON.parse(text);
  assert.equal(info.cafe.cafe_name, "Test Café");
  assert.equal(info.cafe.wallet_url, undefined);
  assert.equal(info.walletUrl, "https://cafe.lan:8443/apps/pay-1/wallet");
  assert.deepEqual(info.packages.map((p) => [p.name, p.price, p.available]), [["One hour", "25.00", true]]);
  assert.ok(!text.includes("SECRET-CODE-1"));
  assert.ok(!text.includes(TOKEN));
});

test("the default wallet address is IntraForge's port on the same host, and odd hosts give none", () => {
  assert.equal(walletUrl({ wallet_url: "" }, { headers: { host: "192.168.8.63:8445" } }), "https://192.168.8.63:8443/apps/pay-1/wallet");
  assert.equal(walletUrl({ wallet_url: "" }, { headers: { host: "evil.com/x?:8445" } }), "");
});

test("buying over HTTP: JSON only, small bodies, then the code once paid", async (t) => {
  const { fake, pkg } = seeded();
  const { server, base } = await start(fake);
  t.after(() => server.close());
  assert.equal((await fetch(`${base}/api/orders`, { method: "POST", body: "packageId=1" })).status, 415);
  const big = JSON.stringify({ packageId: pkg.id, phone: "0912345678", pad: "x".repeat(20000) });
  const tooBig = await fetch(`${base}/api/orders`, { method: "POST", headers: { "Content-Type": "application/json" }, body: big }).catch(() => null);
  assert.ok(!tooBig || tooBig.status === 413);
  const created = await fetch(`${base}/api/orders`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ packageId: pkg.id, phone: "0912345678", amountMinor: 1 }),
  });
  assert.equal(created.status, 201);
  const order = await created.json();
  assert.equal(order.amount, "25.00 IF Credits");
  assert.ok(!JSON.stringify(order).includes("SECRET-CODE-1"), "no code before payment");
  fake.markPaid(order.number);
  await new Promise((r) => setTimeout(r, 2100));
  const paid = await (await fetch(`${base}/api/orders/${order.number}`)).json();
  assert.equal(paid.status, "paid");
  assert.equal(paid.voucher, "SECRET-CODE-1");
  assert.equal((await fetch(`${base}/api/orders/IC-2222-2222`)).status, 404);
  assert.equal((await fetch(`${base}/api/nothing`)).status, 404);
});

test("lookups are rate limited per address", async (t) => {
  const { fake } = seeded();
  const { server, base } = await start(fake);
  t.after(() => server.close());
  const statuses = [];
  for (let i = 0; i < 12; i++) {
    const res = await fetch(`${base}/api/lookup`, {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-Forwarded-For": "10.0.0.9" },
      body: JSON.stringify({ number: "IC-2222-2222", phone: "0912345678" }),
    });
    statuses.push(res.status);
  }
  assert.deepEqual(statuses.slice(0, 10), Array(10).fill(404));
  assert.equal(statuses[10], 429);
  // Another address is not affected.
  const other = await fetch(`${base}/api/lookup`, {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-Forwarded-For": "10.0.0.10" },
    body: JSON.stringify({ number: "IC-2222-2222", phone: "0912345678" }),
  });
  assert.equal(other.status, 404);
});

test("not set up yet: a plain setup answer instead of an error", async (t) => {
  const fake = createFake({ tables: { cafe_settings: { key: ["varchar"], value: ["text"] } }, unique: {} });
  const { server, base } = await start(fake);
  t.after(() => server.close());
  const res = await fetch(`${base}/api/info`);
  assert.equal(res.status, 503);
  const body = await res.json();
  assert.equal(body.error, "setup");
  assert.ok(body.problems.some((p) => p.includes("cafe_orders")));
});

test("the IntraForge client takes the API address with or without /api/v1 and sends the token only there", async () => {
  const { createClient } = require("../lib/intraforge");
  for (const baseUrl of ["http://backend:8000/api/v1", "http://backend:8000/api/v1/", "http://backend:8000"]) {
    const seen = [];
    const client = createClient({
      baseUrl,
      token: TOKEN,
      fetchImpl: async (url, init) => {
        seen.push([url, init.headers.Authorization]);
        return new Response("{}", { status: 200 });
      },
    });
    await client.get("organizations/");
    assert.deepEqual(seen, [["http://backend:8000/api/v1/organizations/", `Bearer ${TOKEN}`]]);
  }
});
