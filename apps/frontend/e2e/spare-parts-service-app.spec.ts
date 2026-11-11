import { expect, test, type Page } from "@playwright/test";
import { readFileSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { createOrganization, register, uniqueEmail } from "./helpers";

// The separately developed Spare Parts application as an IntraForge service application (ADR-0018), end to end
// against the real stack: one IntraForge sign-in, Apps -> Open with no second login, and a whole business day in the
// application -- catalogue import, IMPORT TO MY PRODUCTS, a product photo, supplier, cost and price, stock received,
// customer, enquiry -> quotation -> order -> delivery -> invoice -> payment -- then stock, reports and IntraForge's
// audit log checked. Registers ONE account (the auth endpoints are rate limited to 10/minute on purpose).
//
// Needs a stack with the spareparts service running and nothing installed in its deployment slot yet
// (scripts/qualification/compose.yaml; E2E_BASE_URL=https://localhost:8444).
// Writes e2e-results/spare-parts-service-app.json for the backup/restore round trip that follows it.

test.describe.configure({ mode: "serial" });
test.setTimeout(300_000);

const PASSWORD = "correct-horse-battery-9";
const SHOP = `Harbour Motors ${Date.now().toString(36).slice(-4)}`;
const APP = "/apps/spare-parts";
const PNG = Buffer.from(
  "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==",
  "base64",
);

/** The application's own API, called from the signed-in page: same proxy, same application session, same CSRF
 * rule as the application's screens. */
async function appApi(page: Page, method: string, path: string, body?: unknown) {
  const me = await page.request.get(`${APP}/api/v1/auth/me`);
  expect(me.status(), "the application session is live").toBe(200);
  const csrf = (await me.json()).data.csrfToken as string;
  const origin = new URL(page.url()).origin;
  const res = await page.request.fetch(`${APP}/api/v1${path}`, {
    method,
    headers: { "x-csrf-token": csrf, origin, "content-type": "application/json" },
    data: body === undefined ? undefined : JSON.stringify(body),
  });
  const json = res.status() === 204 ? null : await res.json();
  expect(res.ok(), `${method} ${path} -> ${res.status()} ${JSON.stringify(json)}`).toBeTruthy();
  return json?.data;
}

test("a shop's day in Spare Parts, opened from IntraForge with one sign-in", async ({ page }) => {
  const email = uniqueEmail("sp-service");
  let orgId = "";
  let productId = "";

  await test.step("sign in to IntraForge and create the shop's organization", async () => {
    await register(page, email, PASSWORD);
    orgId = await createOrganization(page, "Harbour Motors Trading LLC");
  });

  await test.step("Apps: install Spare Parts with the shop's own name", async () => {
    await page.goto("/apps");
    await expect(page.getByRole("heading", { name: "Apps" })).toBeVisible();
    await page.getByRole("button", { name: "Install" }).click();
    const dialog = page.getByRole("dialog", { name: "Install Spare Parts" });
    await dialog.getByLabel("Shop name").fill(SHOP);
    await dialog.getByRole("button", { name: "Install" }).click();
    await expect(page.getByRole("heading", { name: SHOP })).toBeVisible();
    await expect(async () => {
      await page.reload();
      await expect(page.getByText("Running")).toBeVisible({ timeout: 2000 });
    }).toPass({ timeout: 60_000 });
  });

  await test.step("Open: straight into the application, no second sign-in", async () => {
    await page.getByRole("button", { name: /Open/ }).click();
    await expect(page).toHaveURL(/\/apps\/spare-parts\/?$/);
    await expect(page.getByRole("heading", { name: "Business overview" })).toBeVisible();
    await expect(page.getByRole("button", { name: "Sign in" })).toHaveCount(0);
    await expect(page.locator(".sidebar")).toContainText(SHOP);
  });

  await test.step("catalogue: import a CSV file (map, preview, import)", async () => {
    await page.goto(`${APP}/catalogue/import`);
    const csv = readFileSync(join(__dirname, "fixtures", "intraforge_reference_catalogue_batch_001.csv"));
    await page.locator('input[type="file"]').first().setInputFiles({ name: "batch.csv", mimeType: "text/csv", buffer: csv });
    await expect(page.getByText("Match your columns")).toBeVisible();
    await page.getByLabel(/I confirm that my organisation/).check();
    await page.getByRole("button", { name: "Validate and preview" }).click();
    await expect(page.getByText("Rows detected")).toBeVisible();
    await page.getByRole("button", { name: /^Import \d+ valid row/ }).click();
    await expect(page.locator(".badge", { hasText: /^Completed/ }).first()).toBeVisible({ timeout: 60_000 });
  });

  await test.step("reference catalogue: find the part in any number format", async () => {
    await page.goto(`${APP}/catalogue`);
    await page.getByLabel("Search the reference catalogue").fill("1111036F00");
    await page.getByRole("button", { name: "Search", exact: true }).click();
    await page.getByRole("link", { name: "11110-36F00" }).first().click();
    await expect(page.getByRole("heading", { name: "11110-36F00" })).toBeVisible();
  });

  await test.step("IMPORT TO MY PRODUCTS: the shop's product, linked to the reference", async () => {
    await page.getByRole("button", { name: "IMPORT TO MY PRODUCTS" }).click();
    const dialog = page.getByRole("dialog");
    await dialog.getByLabel("Your SKU").fill("OILPAN-RS13");
    await dialog.getByLabel("Selling price").fill("250.00");
    await dialog.getByRole("button", { name: "IMPORT TO MY PRODUCTS" }).click();
    await expect(page.getByRole("heading", { name: /Oil Pan Assembly/ })).toBeVisible();
    await expect(page.getByText("Linked to the Reference Catalogue")).toBeVisible();
    productId = new URL(page.url()).pathname.split("/products/")[1];
    expect(productId).toMatch(/^[0-9a-f-]{36}$/);
  });

  await test.step("product photo: stored in IntraForge, shown in the application", async () => {
    await page.locator('input[type="file"]').setInputFiles({ name: "front.png", mimeType: "image/png", buffer: PNG });
    await expect(page.getByText("Uploaded front.png")).toBeVisible();
    const product = await appApi(page, "GET", `/products/${productId}`);
    const url = product.images[0].url as string;
    expect(url.startsWith(`${APP}/api/v1/files/`)).toBeTruthy();
    const img = await page.request.get(url);
    expect(img.status()).toBe(200);
    expect(Buffer.compare(await img.body(), PNG)).toBe(0);
  });

  await test.step("supplier, cost and selling price; stock received", async () => {
    await appApi(page, "POST", "/warehouses", { name: "Main store" });
    const { locations } = await appApi(page, "GET", "/warehouses");
    const supplier = await appApi(page, "POST", "/suppliers", { name: "Gulf Parts Trading" });
    await appApi(page, "PUT", `/products/${productId}/suppliers`, { supplierId: supplier.id, costMinor: 12000, isDefault: true });
    await appApi(page, "PATCH", `/products/${productId}`, { costMinor: 12000, priceMinor: 25000 });
    await appApi(page, "POST", "/inventory/receive", { productId, locationId: locations[0].id, quantity: 10 });
    const stock = await appApi(page, "GET", `/products/${productId}/stock`);
    expect(JSON.stringify(stock)).toContain('"onHand":10');
  });

  await test.step("customer, enquiry, quotation, order, delivery, invoice, payment", async () => {
    await page.goto(`${APP}/customers`);
    await page.getByRole("button", { name: "New customer" }).click();
    await page.getByRole("dialog").getByLabel("Name", { exact: true }).fill("Al Noor Garage");
    await page.getByRole("dialog").getByRole("button", { name: "Save" }).click();
    await expect(page.getByRole("link", { name: "Al Noor Garage" })).toBeVisible();

    await page.goto(`${APP}/catalogue?q=11110-36F00`);
    await page.getByRole("button", { name: "Add to enquiry" }).first().click();
    await expect(page.getByText(/added to the enquiry cart/)).toBeVisible();
    await page.goto(`${APP}/enquiries/cart`);
    await page.getByLabel("Existing customer (optional)").selectOption({ label: "Al Noor Garage" });
    await page.getByLabel("Contact name").fill("Rashid");
    await page.getByRole("button", { name: "Submit enquiry" }).click();
    await expect(page.getByRole("heading", { name: /^ENQ-/ })).toBeVisible();
    await page.getByRole("button", { name: "Create quotation" }).click();
    await expect(page.getByRole("heading", { name: /^QUO-/ })).toBeVisible();
    await page.getByRole("button", { name: "Issue to customer" }).click();
    await expect(page.getByText("Quotation issued")).toBeVisible();
    const quotationId = new URL(page.url()).pathname.split("/quotations/")[1];
    const pdf = await page.request.get(`${APP}/api/v1/quotations/${quotationId}/pdf`);
    expect(pdf.status()).toBe(200);
    expect((await pdf.body()).subarray(0, 5).toString()).toBe("%PDF-");
    await page.getByRole("button", { name: "Customer accepted" }).click();
    await page.getByRole("button", { name: "Create order" }).click();
    await page.getByRole("dialog").getByRole("button", { name: "Create order" }).click();
    await expect(page.getByRole("heading", { name: /^SO-|^ORD-/ })).toBeVisible();
    await page.getByRole("button", { name: "Record delivery" }).click();
    await page.getByRole("dialog").getByRole("button", { name: "Save delivery" }).click();
    await expect(page.getByText("Delivery recorded")).toBeVisible();
    await page.getByRole("button", { name: "Invoice delivered items" }).click();
    await expect(page.getByRole("heading", { name: /^INV-/ })).toBeVisible();
    await page.getByRole("button", { name: "Record payment" }).click();
    await page.getByRole("dialog").getByRole("button", { name: "Record payment" }).click();
    await expect(page.locator(".badge", { hasText: "Paid" }).first()).toBeVisible();
  });

  await test.step("stock, reports and the ledger agree", async () => {
    const stock = await appApi(page, "GET", `/products/${productId}/stock`);
    expect(JSON.stringify(stock)).toContain('"onHand":9');
    const integrity = await appApi(page, "GET", "/inventory/integrity");
    expect(JSON.stringify(integrity)).not.toMatch(/"expected"/);
    const dash = await appApi(page, "GET", "/reports/dashboard");
    expect(dash.salesThisMonthMinor).toBeGreaterThan(0);
    expect(dash.paymentsThisMonthMinor).toBe(dash.salesThisMonthMinor);
  });

  await test.step("IntraForge's audit log records what happened in the application", async () => {
    await expect(async () => {
      const res = await page.request.get(`/api/v1/organizations/${orgId}/audit/?limit=200`);
      expect(res.status()).toBe(200);
      const body = await res.json();
      const actions: string[] = (body.results ?? body).map((e: { action: string }) => e.action);
      for (const a of ["service_app.install", "spareparts.product.", "spareparts.stock.receive", "spareparts.invoice.issue", "spareparts.payment.record"])
        expect(actions.some((x) => x.startsWith(a)), `${a} in ${actions.join(",")}`).toBeTruthy();
    }).toPass({ timeout: 60_000 });
    await page.goto(`/orgs/${orgId}/audit`);
    await expect(page.getByText(/spareparts\./).first()).toBeVisible();
  });

  writeFileSync(
    join(__dirname, "..", "e2e-results-spare-parts-service-app.json"),
    JSON.stringify({ email, password: "(test run)", orgId, productId, shop: SHOP }, null, 2),
  );
});
