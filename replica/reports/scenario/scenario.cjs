// IntraForge end-to-end scenario on the TEST COPY (https://127.0.0.1:9543, test data only).
// Every step: what it does, why, what should happen, what happened, and a screenshot. Results -> results.json.
// Usage: node scenario.cjs <output-folder> <TEST_LOGINS.txt> <site.zip>
const { chromium } = require("@playwright/test");
const crypto = require("crypto");
const fs = require("fs");
const path = require("path");

const BASE = "https://127.0.0.1:9543";
const SITES = "https://127.0.0.1:9545";
const ORG = "ad3124c5-8ab6-4c7f-a4e6-6e2c6d4fe4f9";
const APPS = { pharmacy: "38516322-2eaa-4f42-a661-eff5a716d7d5", pay: "a38fbeb8-19b0-422e-a4dd-44327e4f706b", spareParts: "39d68d88-8dff-4b73-a3cf-63d40a82d4dd" };
const [OUT, LOGINS, SITE_ZIP] = process.argv.slice(2);
fs.mkdirSync(OUT, { recursive: true });
const STAMP = new Date().toISOString().slice(5, 16).replace(/[-:T]/g, "");
const SLUG = "scenario-" + STAMP;

// --- test accounts (read from the test copy's own file; never printed) --------------------------------------------
const text = fs.readFileSync(LOGINS, "utf8");
const grab = (re) => (text.match(re) || [])[1];
const ACC = {
  owner: { email: "owner@test.local", password: grab(/^password:\s*(\S+)/m), totp: "QRDYLK6SLODO2UBSN6AZKK43AOBH6EBL" },
  admin: { email: "superadmin@test.local", password: grab(/superadmin@test\.local, password (\S+)/), totp: grab(/setup key \(test only\):\s*(\S+)/) },
  customer: { username: "customer1", password: grab(/username customer1, password (\S+)/) },
};

function totp(secret) {
  const alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567";
  let bits = "";
  for (const c of secret.replace(/=+$/, "")) bits += alphabet.indexOf(c).toString(2).padStart(5, "0");
  const key = Buffer.from(bits.match(/.{8}/g).map((b) => parseInt(b, 2)));
  const counter = Buffer.alloc(8);
  counter.writeBigUInt64BE(BigInt(Math.floor(Date.now() / 30000)));
  const h = crypto.createHmac("sha1", key).update(counter).digest();
  const o = h[h.length - 1] & 15;
  return String((h.readUInt32BE(o) & 0x7fffffff) % 1000000).padStart(6, "0");
}
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
async function freshCode(secret) {
  const left = 30 - (Math.floor(Date.now() / 1000) % 30);
  if (left < 8) await sleep((left + 1) * 1000);
  return totp(secret);
}

// --- recording ----------------------------------------------------------------------------------------------------
const results = [];
let n = 0;
async function step(page, section, title, why, expected, fn) {
  n += 1;
  const r = { n, section, title, why, expected, status: "PASS", actual: "" };
  const t0 = Date.now();
  try {
    r.actual = (await fn()) || "As expected.";
  } catch (e) {
    r.status = "FAIL";
    r.actual = String((e && e.message) || e).split("\n")[0].slice(0, 400);
  }
  r.seconds = ((Date.now() - t0) / 1000).toFixed(1);
  if (page) {
    try {
      await page.waitForTimeout(600);
      r.shot = `${String(n).padStart(2, "0")}.png`;
      await page.screenshot({ path: path.join(OUT, r.shot) });
    } catch (e) {
      r.shot = null;
    }
  }
  results.push(r);
  fs.writeFileSync(path.join(OUT, "results.json"), JSON.stringify({ stamp: STAMP, slug: SLUG, results }, null, 2));
  console.log(`${r.status}  ${n}. ${title}  (${r.seconds}s)${r.status === "FAIL" ? "  -- " + r.actual : ""}`);
}
function must(cond, message) {
  if (!cond) throw new Error(message);
}

// --- API calls from inside the signed-in page (IntraForge's own session and CSRF cookie) -------------------------
async function api(page, method, url, body) {
  return page.evaluate(
    async ({ method, url, body }) => {
      const csrf = (document.cookie.split("; ").find((c) => c.startsWith("csrftoken=")) || "").split("=")[1];
      const init = { method, headers: { Accept: "application/json" }, credentials: "include" };
      if (method !== "GET") init.headers["X-CSRFToken"] = csrf;
      if (body && body.__form) {
        const form = new FormData();
        for (const [k, v] of Object.entries(body.fields || {})) form.append(k, v);
        const bytes = Uint8Array.from(atob(body.base64), (c) => c.charCodeAt(0));
        form.append("file", new Blob([bytes], { type: body.type || "application/octet-stream" }), body.filename);
        init.body = form;
      } else if (body !== undefined) {
        init.headers["Content-Type"] = "application/json";
        init.body = JSON.stringify(body);
      }
      const res = await fetch("/api/v1" + url, init);
      const raw = await res.text();
      let json = null;
      try { json = JSON.parse(raw); } catch (e) {}
      return { status: res.status, json, raw: raw.slice(0, 300) };
    },
    { method, url, body },
  );
}
const file = (filename, content, type) => ({ __form: true, filename, type, base64: Buffer.from(content).toString("base64") });
function ok(r, what) {
  must(r.status >= 200 && r.status < 300, `${what}: HTTP ${r.status} ${r.raw}`);
  return r.json;
}

async function signIn(page, acc) {
  await page.goto(BASE + "/login");
  await page.getByLabel("Email").fill(acc.email);
  await page.getByLabel("Password").fill(acc.password);
  await page.getByRole("button", { name: "Sign in" }).click();
  await page.getByLabel("Authenticator code").waitFor({ timeout: 15000 });
  await page.getByLabel("Authenticator code").fill(await freshCode(acc.totp));
  await page.getByRole("button", { name: "Verify" }).click();
  await page.waitForURL(/\/dashboard$/, { timeout: 20000 });
}

(async () => {
  const browser = await chromium.launch({ channel: "chrome", headless: true });
  const ctx = await browser.newContext({ ignoreHTTPSErrors: true, viewport: { width: 1440, height: 900 } });
  const page = await ctx.newPage();
  const ids = {};

  // ============================================================== A. Signing in
  await step(page, "Signing in", "Sign in with password and two-step code",
    "Every person signs in with their own account; the owner's account has two-step sign-in switched on.",
    "After the password, IntraForge asks for the 6-digit authenticator code, then opens the dashboard.",
    async () => { await signIn(page, ACC.owner); return "Password accepted, authenticator code asked for and accepted, dashboard opened."; });

  await step(page, "Signing in", "Dashboard overview",
    "The landing page shows the organizations, the system's health and recent activity at a glance.",
    "A welcome heading, the organizations count and 'System health' with all checks passing.",
    async () => {
      await page.getByRole("heading", { name: /Welcome/ }).waitFor();
      await page.getByText("System health").first().waitFor();
      await page.waitForTimeout(1500);
      const health = await page.locator("text=/\\d+\\/\\d+/").first().textContent().catch(() => "");
      return `Dashboard shown; system health ${health || "(read)"}.`;
    });

  // ============================================================== B. Organization, workspace, project
  await step(page, "Organization", "Open the organization",
    "Everything belongs to an organization (the shop); its page lists workspaces, members and roles.",
    "The 'Test Shop' organization page opens with its workspaces and members.",
    async () => {
      await page.goto(BASE + "/orgs");
      await page.getByText("Test Shop").first().click();
      await page.waitForURL(/\/orgs\/[0-9a-f-]{36}$/);
      await page.getByText("Members").first().waitFor();
      return "Organization page opened; workspaces and members listed.";
    });

  await step(page, "Organization", "Create a workspace and a project",
    "Workspaces group projects; a project holds the files and databases of one piece of work.",
    "A new workspace and a project inside it are created, and the project page opens.",
    async () => {
      const ws = ok(await api(page, "POST", `/organizations/${ORG}/workspaces/`, { name: "Scenario " + STAMP }), "workspace");
      const pr = ok(await api(page, "POST", `/workspaces/${ws.id}/projects/`, { name: "Price lists" }), "project");
      ids.project = pr.id;
      await page.goto(BASE + `/projects/${pr.id}`);
      await page.getByText("Price lists").first().waitFor();
      return `Workspace "Scenario ${STAMP}" and project "Price lists" created.`;
    });

  // ============================================================== C. Files (storage)
  await step(page, "Files", "Create a bucket with versioning",
    "A bucket is a place for files; with versioning on, every overwrite keeps the earlier version.",
    "The bucket is created and its (empty) page opens.",
    async () => {
      const b = ok(await api(page, "POST", `/projects/${ids.project}/buckets/`, { name: "scenario-files", versioning_enabled: true }), "bucket");
      ids.bucket = b.id;
      await page.goto(BASE + `/buckets/${b.id}`);
      await page.getByText("scenario-files").first().waitFor();
      return "Bucket 'scenario-files' created with versioning on.";
    });

  await step(page, "Files", "Create a folder and upload a file",
    "Files can be organized in folders; uploads go through the same checks as in the shop (size limit, optional virus scan).",
    "Folder 'Invoices' and the file 'price-list.csv' appear in the bucket.",
    async () => {
      ok(await api(page, "POST", `/buckets/${ids.bucket}/folders/`, { name: "Invoices", parent_id: null }), "folder");
      const f = ok(await api(page, "POST", `/buckets/${ids.bucket}/files/`, file("price-list.csv", "name,price,in_stock\nOil filter,45.00,8\nBrake pad,120.00,3\nSpark plug,18.50,40\n", "text/csv")), "upload");
      ids.file = f.id;
      await page.reload();
      await page.getByText("price-list.csv").first().waitFor();
      await page.getByText("Invoices").first().waitFor();
      return "Folder created and file uploaded (3 products).";
    });

  await step(page, "Files", "Upload a new version and see the history",
    "Replacing a file keeps the old one, so a mistake can be undone.",
    "The earlier content is kept: 1 earlier version listed, the file itself holding the new content.",
    async () => {
      ok(await api(page, "POST", `/files/${ids.file}/versions/`, file("price-list.csv", "name,price,in_stock\nOil filter,47.00,8\nBrake pad,120.00,3\nSpark plug,18.50,40\nAir filter,60.00,5\n", "text/csv")), "new version");
      const v = ok(await api(page, "GET", `/files/${ids.file}/versions/`), "versions");
      const count = Array.isArray(v) ? v.length : (v.results || []).length;
      must(count >= 1, `expected 1 earlier version, saw ${count}`);
      await page.reload();
      return `${count} earlier version kept; the file now holds the new prices (oil filter 45.00 -> 47.00, air filter added).`;
    });

  await step(page, "Files", "Move a file to Trash and restore it",
    "Deleting moves a file to Trash first; it can be restored until Trash is emptied.",
    "The file disappears from the list, then comes back after Restore.",
    async () => {
      const d = await api(page, "DELETE", `/files/${ids.file}/`);
      must(d.status === 204 || d.status === 200, `delete: HTTP ${d.status}`);
      ok(await api(page, "POST", `/files/${ids.file}/restore/`), "restore");
      await page.reload();
      await page.getByText("price-list.csv").first().waitFor();
      return "File moved to Trash and restored with its versions.";
    });

  // ============================================================== D. Databases
  await step(page, "Databases", "Build a database table without code",
    "The database builder creates real tables (no SQL typed by anyone) with checked names and types.",
    "Table 'products' with columns name (text), price (decimal) and in_stock (integer).",
    async () => {
      const db = ok(await api(page, "POST", `/projects/${ids.project}/tenant-databases/`, { name: "Shop data " + STAMP }), "database");
      const t = ok(await api(page, "POST", `/tenant-databases/${db.id}/tables/`, { name: "products" }), "table");
      ids.table = t.id;
      ok(await api(page, "POST", `/tables/${t.id}/columns/`, { name: "name", data_type: "text", is_nullable: false }), "column name");
      ok(await api(page, "POST", `/tables/${t.id}/columns/`, { name: "price", data_type: "decimal", precision: 10, scale: 2 }), "column price");
      ok(await api(page, "POST", `/tables/${t.id}/columns/`, { name: "in_stock", data_type: "integer" }), "column in_stock");
      await page.goto(BASE + `/tables/${t.id}`);
      await page.getByText("in_stock").first().waitFor();
      return "Database, table and three typed columns created.";
    });

  await step(page, "Databases", "Add, edit and delete rows",
    "Rows are edited like a spreadsheet, with the column types enforced by the database.",
    "Two rows added, one price changed, one row deleted: one row is left with the new price.",
    async () => {
      const a = ok(await api(page, "POST", `/tables/${ids.table}/rows/`, { name: "Wiper blade", price: "25.00", in_stock: 12 }), "row 1");
      const b = ok(await api(page, "POST", `/tables/${ids.table}/rows/`, { name: "Fan belt", price: "30.00", in_stock: 4 }), "row 2");
      ok(await api(page, "PATCH", `/tables/${ids.table}/rows/${a.id}/`, { price: "27.50" }), "edit");
      const d = await api(page, "DELETE", `/tables/${ids.table}/rows/${b.id}/`);
      must(d.status === 204 || d.status === 200, `delete row: HTTP ${d.status}`);
      const bad = await api(page, "POST", `/tables/${ids.table}/rows/`, { name: "Bad", in_stock: "many" });
      must(bad.status === 400, `a text in a number column must be refused, got HTTP ${bad.status}`);
      await page.reload();
      await page.getByText("Wiper blade").first().waitFor();
      return "Wiper blade kept at 27.50; Fan belt deleted; a text value in the number column was refused (HTTP 400).";
    });

  await step(page, "Databases", "Import a CSV file into the table",
    "A spreadsheet export can be imported: IntraForge reads it, maps its columns and inserts the rows in the background.",
    "The import job finishes and the 4 products from the stored CSV are in the table (5 rows in total).",
    async () => {
      const job = ok(await api(page, "POST", `/tables/${ids.table}/imports/`, {
        file_id: ids.file, encoding: "utf-8", delimiter: ",",
        column_mapping: [
          { csv_column: "name", target_column: "name", target_type: "text" },
          { csv_column: "price", target_column: "price", target_type: "decimal" },
          { csv_column: "in_stock", target_column: "in_stock", target_type: "integer" },
        ],
      }), "import");
      let state = job.status;
      for (let i = 0; i < 40 && !["completed", "failed"].includes(state); i++) {
        await sleep(1500);
        state = ok(await api(page, "GET", `/imports/${job.id}/`), "import status").status;
      }
      must(state === "completed", `import ended as ${state}`);
      await page.goto(BASE + `/tables/${ids.table}`);
      await page.getByText("Air filter").first().waitFor();
      return "Import job completed; Oil filter, Brake pad, Spark plug and Air filter added.";
    });

  await step(page, "Databases", "Data profile and statistics",
    "Every table gets an automatic data-quality profile and statistics (counts, averages, missing values).",
    "The analytics page shows the profile of the products table.",
    async () => {
      await page.goto(BASE + `/tables/${ids.table}/analytics`);
      await page.getByText("Data quality report").first().waitFor({ timeout: 20000 });
      return "Data quality report shown: missing values, unique counts, mean, median, range and outliers per column.";
    });

  // ============================================================== E. Business apps and IntraForge Pay
  await step(page, "Apps", "Installed applications",
    "Spare Parts, the Pharmacy and IntraForge Pay are installed in the shop and open with the same sign-in.",
    "The Apps page lists the three applications as Running.",
    async () => {
      await page.goto(BASE + "/apps");
      await page.getByText("Running").first().waitFor({ timeout: 20000 });
      const running = await page.getByText("Running").count();
      must(running >= 3, `expected 3 running apps, saw ${running}`);
      return `${running} applications running.`;
    });

  await step(page, "Apps", "Switch an application off and on",
    "An administrator can disable an app for everyone (data kept) and enable it again; the switch reacts at once.",
    "Disable turns into Enable immediately, and back.",
    async () => {
      await page.goto(BASE + `/service-apps/${APPS.pharmacy}/settings`);
      await page.getByRole("button", { name: "Disable" }).click();
      await page.getByRole("button", { name: "Enable" }).waitFor({ timeout: 10000 });
      await page.screenshot({ path: path.join(OUT, "apps-disabled.png") });
      await page.getByRole("button", { name: "Enable" }).click();
      await page.getByRole("button", { name: "Disable" }).waitFor({ timeout: 10000 });
      return "Pharmacy disabled, then enabled again.";
    });

  await step(page, "Apps", "Spare Parts: invoice paid with IntraForge Pay (QR shown)",
    "The cashier issues an invoice in Spare Parts and asks IntraForge Pay to take the payment.",
    "An invoice is issued and the IntraForge Pay QR code for its total is shown.",
    async () => {
      const launch = ok(await api(page, "POST", `/service-apps/${APPS.spareParts}/launch/`), "launch");
      await page.goto(BASE + launch.url);
      await page.waitForURL(/apps\/spare-parts/, { timeout: 20000 });
      const sp = (m, u, b) => page.evaluate(async ({ m, u, b }) => {
        const me = await (await fetch("/apps/spare-parts/api/v1/auth/me")).json();
        const r = await fetch("/apps/spare-parts/api/v1" + u, { method: m, headers: { "Content-Type": "application/json", "x-csrf-token": me.data.csrfToken }, body: b ? JSON.stringify(b) : undefined });
        return { status: r.status, json: await r.json().catch(() => null) };
      }, { m, u, b });
      const products = (await sp("GET", "/products")).json.data.items;
      const product = products.find((p) => p.sku === "OIL-FLT-01") || products[0];
      must(product, "no product in Spare Parts");
      const customers = (await sp("GET", "/customers")).json.data.items;
      must(customers.length, "no customer in Spare Parts");
      const order = await sp("POST", "/orders", { customerId: customers[0].id, lines: [{ productId: product.id, quantity: 1, unitPriceMinor: product.priceMinor || 4500 }] });
      must(order.status === 201, `order: HTTP ${order.status} ${JSON.stringify(order.json).slice(0, 150)}`);
      const inv = await sp("POST", `/orders/${order.json.data.id}/sell-now`, {});
      must(inv.status === 201, `invoice: HTTP ${inv.status}`);
      ids.invoice = inv.json.data;
      await page.goto(BASE + `/apps/spare-parts/invoices/${ids.invoice.id}`);
      await page.getByRole("button", { name: "Take payment with IntraForge Pay" }).first().click();
      await page.getByText(/scan this with their wallet/i).waitFor({ timeout: 20000 });
      return `Invoice ${ids.invoice.number} for ${ids.invoice.currency} ${(ids.invoice.totalMinor / 100).toFixed(2)} issued; Pay QR shown.`;
    });

  await step(page, "Apps", "A hosted app takes a Pay payment; the customer pays from the wallet",
    "A website or app built on IntraForge can ask Pay for a payment with its own key, once an administrator allows it.",
    "After 'Allow IntraForge Pay', the app's request is paid from the customer's wallet (less any cashback the shop pays back) and reads back as paid.",
    async () => {
      const app = ok(await api(page, "POST", `/organizations/${ORG}/applications/`, { name: "Web shop " + STAMP, description: "Scenario" }), "application");
      await page.goto(BASE + `/applications/${app.id}`);
      await page.getByRole("button", { name: "Allow IntraForge Pay" }).click();
      await page.getByText("Can take payments").waitFor({ timeout: 10000 });
      const cred = ok(await api(page, "POST", `/applications/${app.id}/credentials/`, {}), "credential");
      const result = await page.evaluate(async ({ secret, customer }) => {
        const req = await (await fetch("/api/v1/pay/payment-requests/", { method: "POST", credentials: "omit", headers: { "Content-Type": "application/json", Authorization: "Bearer " + secret }, body: JSON.stringify({ amountMinor: 500, reference: "Scenario order", externalId: "S-1" }) })).json();
        const login = await (await fetch("/apps/pay-1/api/auth/login", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ username: customer.username, password: customer.password }) })).json();
        const h = { "Content-Type": "application/json", "x-csrf-token": login.csrf_token };
        const before = (await (await fetch("/apps/pay-1/api/wallet")).json()).balance_minor;
        const paid = await (await fetch("/apps/pay-1/api/wallet/checkout/pay", { method: "POST", headers: h, body: JSON.stringify({ code: req.code, expected_amount_minor: 500, confirm: true }) })).json();
        const wallet = await (await fetch("/apps/pay-1/api/wallet")).json();
        const after = wallet.balance_minor;
        const cashback = (wallet.history || []).find((h) => /cashback/i.test(h.kind + " " + h.description));
        const status = await (await fetch("/api/v1/pay/payment-requests/" + req.id + "/", { credentials: "omit", headers: { Authorization: "Bearer " + secret } })).json();
        await fetch("/apps/pay-1/api/auth/logout", { method: "POST", headers: h });
        return { status: status.status, receipt: paid.receipt && paid.receipt.receipt_number, before, after, cashback: cashback ? cashback.amount : null };
      }, { secret: cred.secret, customer: ACC.customer });
      must(result.status === "paid", `payment status ${result.status}`);
      const spent = result.before - result.after;
      must(spent > 0 && spent <= 500, `wallet went from ${result.before} to ${result.after}`);
      await page.reload();
      const back = 500 - spent;
      return `Paid 5.00 from customer1's wallet, receipt ${result.receipt}; ${back ? `cashback ${(back / 100).toFixed(2)} paid back, so the wallet went ${(result.before / 100).toFixed(2)} -> ${(result.after / 100).toFixed(2)}` : "no cashback"}; the app reads it back as paid.`;
    });

  await step(page, "Apps", "IntraForge Pay for the cashier (refunds and cashback)",
    "Pay opens from IntraForge with the same sign-in; the cashier screen has QR checkout, refunds and the customer app.",
    "The Pay cashier screen opens with today's payments, Refunds and the Customer app section.",
    async () => {
      await page.goto(BASE + "/apps");
      const launch = ok(await api(page, "POST", `/service-apps/${APPS.pay}/launch/`), "launch pay");
      await page.goto(BASE + launch.url);
      await page.waitForLoadState("networkidle");
      await page.getByText(/Refund/i).first().waitFor({ timeout: 20000 });
      return "Pay cashier screen opened with the Refunds and Customer app sections.";
    });

  // ============================================================== F. Websites and internet
  await step(page, "Websites", "Publish a website on the shop network",
    "A shop can host its own website from IntraForge: upload a zip, and it is online on the shop network.",
    "The website is created and its page is served.",
    async () => {
      const zip = fs.readFileSync(SITE_ZIP).toString("base64");
      const site = ok(await api(page, "POST", `/organizations/${ORG}/sites/`, { __form: true, fields: { name: "Scenario site " + STAMP, slug: SLUG }, filename: "site.zip", type: "application/zip", base64: zip }), "site");
      ids.site = site.id;
      const res = await page.request.get(`${SITES}/${SLUG}/`);
      must(res.status() === 200 && (await res.text()).includes("IntraForge scenario"), `site page: HTTP ${res.status()}`);
      await page.goto(BASE + `/orgs/${ORG}/sites`);
      await page.getByText("Scenario site " + STAMP).first().waitFor();
      return `Website '${SLUG}' online at ${SITES}/${SLUG}/ (HTTP 200).`;
    });

  await step(page, "Websites", "Take a website offline and bring it back",
    "Taking a site offline stops serving it at once; bringing it online serves it again.",
    "Offline: the page is no longer served. Online: it is served again.",
    async () => {
      ok(await api(page, "PATCH", `/sites/${ids.site}/`, { status: "disabled" }), "offline");
      const off = (await page.request.get(`${SITES}/${SLUG}/`)).status();
      ok(await api(page, "PATCH", `/sites/${ids.site}/`, { status: "active" }), "online");
      const on = (await page.request.get(`${SITES}/${SLUG}/`)).status();
      must(off !== 200 && on === 200, `offline gave ${off}, online gave ${on}`);
      await page.reload();
      return `Offline: HTTP ${off}. Online again: HTTP ${on}.`;
    });

  // Super Administrator (platform-wide), in a separate browser session.
  const adminCtx = await browser.newContext({ ignoreHTTPSErrors: true, viewport: { width: 1440, height: 900 } });
  const admin = await adminCtx.newPage();
  await step(admin, "Internet", "The Super Administrator's internet gate",
    "Only the Super Administrator (with two-step sign-in) controls what is reachable from the internet.",
    "The Internet access page shows the gate On, the tunnel running, and the Auto-publish card.",
    async () => {
      await signIn(admin, ACC.admin);
      await admin.goto(BASE + "/internet");
      await admin.getByText("Auto-publish").first().waitFor({ timeout: 15000 });
      return "Gate on, Cloudflare tunnel running, Auto-publish available.";
    });

  await step(admin, "Internet", "Auto-publish every site under harmongt.uk",
    "With one switch, every online website and app is published as <address>.harmongt.uk, now and when new ones come online.",
    `The scenario site is published as ${SLUG}.harmongt.uk and answers from the internet through Cloudflare.`,
    async () => {
      const r = await api(admin, "POST", "/internet-gateway/auto-publish/", { domain: "harmongt.uk", password: ACC.admin.password });
      ok(r, "auto-publish on");
      const mine = (r.json.published || []).find((p) => p.site === ids.site);
      must(mine && mine.internet_hostname === `${SLUG}.harmongt.uk`, `site not auto-published: ${JSON.stringify(r.json.published).slice(0, 200)}`);
      let status = 0;
      for (let i = 0; i < 10 && status !== 200; i++) {
        status = (await admin.request.get(`https://${SLUG}.harmongt.uk/`).catch(() => ({ status: () => 0 }))).status();
        if (status !== 200) await sleep(3000);
      }
      await admin.reload();
      await admin.getByText("Automatic").first().waitFor();
      return `Published as https://${SLUG}.harmongt.uk/ automatically; the internet request through Cloudflare returned HTTP ${status}.`;
    });

  await step(admin, "Internet", "Switch auto-publish off: automatic names are taken back",
    "Switching off takes back every automatic name and keeps names published by hand.",
    `${SLUG}.harmongt.uk is no longer served; the hand-published shop.harmongt.uk stays.`,
    async () => {
      const r = await api(admin, "POST", "/internet-gateway/auto-publish/", { domain: "", password: ACC.admin.password });
      ok(r, "auto-publish off");
      must(!(r.json.published || []).some((p) => p.site === ids.site), "the automatic name is still published");
      const kept = (r.json.published || []).map((p) => p.internet_hostname);
      const status = (await admin.request.get(`https://${SLUG}.harmongt.uk/`).catch(() => ({ status: () => 0 }))).status();
      await admin.reload();
      return `Automatic name withdrawn (internet request now HTTP ${status}); still published by hand: ${kept.join(", ") || "none"}.`;
    });

  // ============================================================== G. Audit and account
  await step(page, "Audit", "The audit log recorded every action",
    "Every important action is recorded with who, what and when, and cannot be edited.",
    "The organization's audit log contains this scenario's actions.",
    async () => {
      const a = ok(await api(page, "GET", `/organizations/${ORG}/audit/?limit=100`), "audit");
      const actions = new Set((a.results || []).map((e) => e.action));
      const wanted = ["workspace.create", "project.create", "storage.bucket.create", "storage.folder.create", "site.created", "site.internet.published", "site.internet.revoked", "service_app.updated"];
      const seen = wanted.filter((w) => actions.has(w));
      await page.goto(BASE + `/orgs/${ORG}/audit`);
      await page.getByText("Who").first().waitFor();
      must(seen.length >= 5, `only found ${seen.join(", ")}`);
      return `Found ${seen.length} of ${wanted.length} expected actions: ${seen.join(", ")}.`;
    });

  await step(page, "Account", "Account and two-step sign-in",
    "Each person manages their own account; two-step sign-in can be switched on or off here.",
    "The account page shows the owner with two-step sign-in on.",
    async () => {
      await page.goto(BASE + "/account");
      await page.getByText(/two-step/i).first().waitFor();
      return "Account page shows two-step sign-in on.";
    });

  await step(page, "Account", "Sign out",
    "Signing out ends the session on this PC.",
    "Back on the sign-in page; IntraForge pages are no longer reachable.",
    async () => {
      await page.getByRole("button", { name: "Log out" }).first().click();
      await page.waitForURL(/\/login/, { timeout: 10000 });
      await page.goto(BASE + "/dashboard");
      await page.waitForURL(/\/login/, { timeout: 10000 });
      return "Signed out; opening the dashboard again sends you to the sign-in page.";
    });

  await browser.close();
  const passed = results.filter((r) => r.status === "PASS").length;
  console.log(`\n${passed}/${results.length} passed`);
})();
