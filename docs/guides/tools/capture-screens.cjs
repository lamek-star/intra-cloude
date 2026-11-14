// Captures the screenshots the guides use, from a TEST installation (never a real shop's data):
//   PW_PATH=<frontend>/node_modules/playwright  node capture-screens.cjs <out-folder> <test-logins-file>
// The test copy is https://localhost:9543 (see docs/guides/README.md). Each screen is independent: one that cannot be
// reached is reported and the others are still taken. The owner's password and two-step key are read from the logins
// file and never printed.
const { chromium } = require(process.env.PW_PATH);
const fs = require("fs");
const crypto = require("crypto");

const out = process.argv[2];
const logins = fs.readFileSync(process.argv[3], "utf8");
const BASE = process.env.BASE || "https://localhost:9543";
const PASS = (logins.match(/email:\s*owner@test\.local\s*\r?\npassword:?\s*(\S+)/i) || [])[1];
const KEY = (logins.match(/^Owner two-step[^\n]*?([A-Z2-7]{16,})/im) || [])[1];
const results = [];

function totp(b32) {
  const a = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567";
  let bits = "";
  for (const c of b32.replace(/=+$/, "")) bits += a.indexOf(c).toString(2).padStart(5, "0");
  const key = Buffer.from(bits.match(/.{8}/g).map((b) => parseInt(b, 2)));
  const ctr = Buffer.alloc(8);
  ctr.writeBigUInt64BE(BigInt(Math.floor(Date.now() / 30000)));
  const h = crypto.createHmac("sha1", key).update(ctr).digest();
  const o = h[h.length - 1] & 15;
  return String((h.readUInt32BE(o) & 0x7fffffff) % 1000000).padStart(6, "0");
}

(async () => {
  fs.mkdirSync(`${out}/web`, { recursive: true });
  const browser = await chromium.launch({ channel: "msedge" });
  const ctx = await browser.newContext({ ignoreHTTPSErrors: true, viewport: { width: 1440, height: 900 } });
  await ctx.addInitScript(() => { try { localStorage.setItem("intraforge-theme", "light"); } catch (_) {} });
  const page = await ctx.newPage();
  const settle = async (p = page, ms = 1800) => { await p.waitForLoadState("networkidle").catch(() => {}); await p.waitForTimeout(ms); await p.keyboard.press("Escape").catch(() => {}); await p.waitForTimeout(200); };
  const snap = async (name, p = page, full = false) => p.screenshot({ path: `${out}/web/${name}.png`, fullPage: full });
  async function shot(name, url, opts = {}) {
    try {
      await page.goto(url.startsWith("http") ? url : BASE + url, { waitUntil: "domcontentloaded" });
      await settle(page, opts.wait || 1800);
      if (opts.then) await opts.then(page);
      await snap(name, page, opts.full);
      results.push(`ok   ${name}`);
    } catch (e) { results.push(`FAIL ${name}: ${String(e.message).split("\n")[0].slice(0, 160)}`); }
  }
  const api = async (p) => (await page.request.get(`${BASE}/api/v1${p}`)).json();

  // Sign-in screens first, then sign in.
  await shot("01-login", "/login");
  await page.fill('input[type="email"]', "owner@test.local");
  await page.fill('input[type="password"]', PASS);
  await page.keyboard.press("Enter");
  await page.waitForFunction(() => document.querySelector('input[placeholder="123456"]') || !location.pathname.startsWith("/login"), null, { timeout: 45000 });
  if (await page.locator('input[placeholder="123456"]').count()) {
    await snap("02-login-two-step");
    if (30 - (Math.floor(Date.now() / 1000) % 30) < 5) await page.waitForTimeout(6000);
    await page.fill('input[placeholder="123456"]', totp(KEY));
    await page.keyboard.press("Enter");
  }
  await page.waitForFunction(() => !location.pathname.startsWith("/login"), null, { timeout: 45000 });

  const orgs = await api("/organizations/"); const org = (orgs.results || orgs)[0];
  const ws = await api(`/organizations/${org.id}/workspaces/`); const workspace = (ws.results || ws)[0];
  const buckets = await api(`/organizations/${org.id}/buckets/`);
  const bucket = buckets.find((b) => b.name === "documents") || buckets.find((b) => b.files > 0) || buckets[0];
  const dbs = await api(`/organizations/${org.id}/tenant-databases/`); const db = dbs[0];
  const tables = db ? await api(`/tenant-databases/${db.id}/tables/`) : []; const table = (tables.results || tables)[0];
  const apps = await api(`/organizations/${org.id}/applications/`).catch(() => []); const application = (apps.results || apps)[0];
  const shopUrl = fs.existsSync(`${out}/shop-url.txt`) ? fs.readFileSync(`${out}/shop-url.txt`, "utf8").trim() : null;

  // IntraForge itself
  await shot("03-dashboard", "/dashboard", { full: true });
  await shot("04-command-palette", "/dashboard", { then: async (p) => { await p.keyboard.press("Control+K"); await p.waitForTimeout(600); await p.keyboard.type("stor"); await p.waitForTimeout(600); } });
  await shot("05-apps", "/apps", { full: true });
  await shot("06-organizations", "/orgs");
  await shot("07-organization", `/orgs/${org.id}`, { full: true });
  await shot("08-workspace", `/orgs/${org.id}/workspaces/${workspace.id}`);
  await shot("09-project", `/projects/${bucket.project}`, { full: true });
  await shot("10-connect-database", `/projects/${bucket.project}`, { then: async (p) => { await p.getByRole("button", { name: /connect a database|connect database/i }).first().click(); await p.waitForTimeout(700); } });
  await shot("11-org-storage", `/orgs/${org.id}/storage`, { full: true });
  await shot("12-org-databases", `/orgs/${org.id}/databases`);
  await shot("13-bucket", `/buckets/${bucket.id}?name=${encodeURIComponent(bucket.name)}&project=${bucket.project}`);
  await shot("14-file-versions", `/buckets/${bucket.id}?name=${encodeURIComponent(bucket.name)}&project=${bucket.project}`, { then: async (p) => { await p.getByRole("button", { name: /^versions$/i }).first().click(); await p.waitForTimeout(1200); } });
  await shot("15-share-link", `/buckets/${bucket.id}?name=${encodeURIComponent(bucket.name)}&project=${bucket.project}`, { then: async (p) => { await p.getByRole("button", { name: /^share link$/i }).first().click(); await p.waitForTimeout(900); } });
  await shot("16-cleanup", `/buckets/${bucket.id}?name=${encodeURIComponent(bucket.name)}&project=${bucket.project}`, { then: async (p) => { await p.getByRole("button", { name: /^cleanup$/i }).click(); await p.waitForTimeout(600); } });
  if (db) await shot("17-database", `/tenant-databases/${db.id}`);
  if (table) {
    await shot("18-table-data", `/tables/${table.id}`, { full: true });
    await shot("19-csv-import", `/tables/${table.id}/import`);
    await shot("20-analytics", `/tables/${table.id}/analytics`, { full: true });
  }
  await shot("21-app-gallery", `/projects/${bucket.project}/apps`, { full: true });
  await shot("22-members-teams", `/orgs/${org.id}/teams`);
  await shot("23-units", `/orgs/${org.id}/units`);
  await shot("24-audit-log", `/orgs/${org.id}/audit`, { full: true });
  await shot("25-websites", `/orgs/${org.id}/sites`, { full: true });
  await shot("26-developer", `/orgs/${org.id}/developer`);
  await shot("27-developer-applications", `/orgs/${org.id}/developer/applications`);
  if (application) await shot("28-application", `/applications/${application.id}`, { full: true });
  await shot("29-account", "/account", { full: true });
  await shot("30-backups", "/backups", { full: true });
  await shot("31-health", "/health", { full: true });
  await shot("32-licence", "/license");
  await shot("33-internet-access", "/internet");
  await shot("34-dashboard-dark", "/dashboard", { then: async (p) => { await p.evaluate(() => { document.documentElement.dataset.theme = "dark"; }); await p.waitForTimeout(400); } });

  // Movie Shop
  await shot("40-movie-shops", "/movies");
  if (shopUrl) {
    const path = shopUrl.replace(BASE, "");
    await shot("41-movie-catalogue", path, { wait: 3000 });
    await shot("42-movie-edit-title", path, { wait: 3000, then: async (p) => { const c = p.locator("div.group.relative").first(); await c.hover(); await p.waitForTimeout(300); await c.getByRole("button", { name: /^edit /i }).click(); await p.waitForTimeout(800); } });
    await shot("43-movie-cart", path, { wait: 3000, then: async (p) => { const c = p.locator("div.group.relative").nth(1); await c.hover(); await p.waitForTimeout(300); await c.getByRole("button", { name: /^add$/i }).click(); await p.waitForTimeout(800); } });
    for (const [name, button] of [["44-movie-prices", /^prices$/i], ["45-movie-sales", /^sales$/i], ["46-movie-customers", /^customers/i], ["47-movie-ads", /^ads$/i], ["48-movie-add-storage", /^add storage$/i]]) {
      await shot(name, path, { wait: 3000, then: async (p) => { await p.getByRole("button", { name: button }).first().click(); await p.waitForTimeout(1500); } });
    }
    // The customer portal, on a phone
    const shopId = path.split("/").pop();
    const phone = await browser.newContext({ ignoreHTTPSErrors: true, viewport: { width: 390, height: 844 }, deviceScaleFactor: 2, isMobile: true });
    const pp = await phone.newPage();
    for (const [name, then] of [
      ["50-portal-home", null],
      ["51-portal-sign-in", async () => { await pp.getByRole("tab", { name: /sign in/i }).click(); await pp.waitForTimeout(500); }],
      ["52-portal-sign-up", async () => { await pp.getByRole("tab", { name: /sign up|join|create/i }).first().click(); await pp.waitForTimeout(500); }],
    ]) {
      try {
        await pp.goto(`${BASE}/portal/${shopId}`, { waitUntil: "domcontentloaded" });
        await settle(pp, 3000);
        if (then) await then();
        await snap(name, pp);
        results.push(`ok   ${name}`);
      } catch (e) { results.push(`FAIL ${name}: ${String(e.message).split("\n")[0].slice(0, 160)}`); }
    }
    await phone.close();
  }

  // Service applications, opened the way staff open them: Apps > Open.
  async function openApp(title) {
    await page.goto(`${BASE}/apps`, { waitUntil: "domcontentloaded" });
    await settle(page, 2000);
    const card = page.locator("div", { has: page.getByText(title, { exact: true }) }).filter({ has: page.getByRole("link", { name: /^open$/i }).or(page.getByRole("button", { name: /^open$/i })) }).last();
    const opener = card.getByRole("link", { name: /^open$/i }).or(card.getByRole("button", { name: /^open$/i })).first();
    const [popup] = await Promise.all([ctx.waitForEvent("page", { timeout: 8000 }).catch(() => null), opener.click()]);
    const p = popup || page;
    await settle(p, 3000);
    return p;
  }
  async function appShots(title, list) {
    let p;
    try { p = await openApp(title); } catch (e) { results.push(`FAIL ${title}: ${String(e.message).split("\n")[0]}`); return; }
    const base = new URL(p.url());
    const root = base.pathname.split("/").slice(0, 3).join("/");
    for (const [name, sub, then] of list) {
      try {
        if (sub !== null) { await p.goto(`${base.origin}${root}${sub}`, { waitUntil: "domcontentloaded" }); await settle(p, 2500); }
        if (then) await then(p);
        await snap(name, p, true);
        results.push(`ok   ${name}`);
      } catch (e) { results.push(`FAIL ${name}: ${String(e.message).split("\n")[0].slice(0, 160)}`); }
    }
  }
  await appShots("Test Shop", [["60-pay-checkout", null, null], ["61-pay-office", "/admin", null]]);
  await appShots("Test Spare Parts", [
    ["70-spareparts-dashboard", "", null],
    ["71-spareparts-products", "/products", null],
    ["72-spareparts-product", null, async (p) => { await p.locator('a[href*="/products/"]').filter({ hasNotText: /new/i }).first().click(); await settle(p, 2500); }],
    ["73-spareparts-label", null, async (p) => { await p.getByRole("button", { name: /print label/i }).first().click(); await p.waitForTimeout(2000); }],
    ["74-spareparts-sell", "/sell", null],
    ["75-spareparts-stock", "/inventory", null],
    ["76-spareparts-purchasing", "/purchasing", null],
    ["77-spareparts-invoices", "/invoices", null],
    ["78-spareparts-customers", "/customers", null],
    ["79-spareparts-reports", "/reports", null],
    ["80-spareparts-scan", "/scan", null],
    ["81-spareparts-catalogue", "/catalogue", null],
    ["82-spareparts-admin", "/admin", null],
  ]);
  await appShots("Test Pharmacy", [["85-pharmacy-dashboard", "", null], ["86-pharmacy-medicines", "/products", null]]);

  fs.writeFileSync(`${out}/web/capture-results.txt`, results.join("\n") + "\n");
  console.log(results.join("\n"));
  await browser.close();
})().catch((e) => { console.error("FATAL", String(e.message).slice(0, 300)); console.log(results.join("\n")); process.exit(1); });
