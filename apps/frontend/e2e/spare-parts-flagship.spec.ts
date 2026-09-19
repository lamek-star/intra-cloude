import { test, expect, type Page } from "@playwright/test";
import { createOrganization, register, uniqueEmail } from "./helpers";

// The Local Edition flagship journey, through the normal UI against the real backend and database:
// gallery -> install -> supplier, warehouse, product, part number -> normalized search -> receive 100
// -> inventory 100 -> customer -> sell 5 -> inventory 95 -> sales document -> movement -> files ->
// persistence -> an oversell the database refuses. Nothing is mocked; requests to anything but the
// local stack are aborted, so the whole journey also proves it needs no internet.
//
// Requires the qualification stack with SHOW_UNQUALIFIED_BUILT_IN_APPS=1 (the pilot preview mode):
// no application is QUALIFIED yet, so the default gallery is empty by design.

const nav = (page: Page) => page.getByRole("navigation", { name: "Application sections" });
// The Stock page has two labelled regions; look inside the right one, never at the whole page.
const stockRegion = (page: Page) => page.getByRole("region", { name: "Stock", exact: true });
const movementsRegion = (page: Page) => page.getByRole("region", { name: "Recent stock movements", exact: true });
// One stock row: product, warehouse, and EXACTLY this on-hand quantity as its own cell.
const stockRow = (page: Page, onHand: string) =>
  stockRegion(page)
    .getByRole("row")
    .filter({ has: page.getByRole("cell", { name: "Demo Oil Filter", exact: true }) })
    .filter({ has: page.getByRole("cell", { name: "Main Warehouse", exact: true }) })
    .filter({ has: page.getByRole("cell", { name: onHand, exact: true }) });

async function addRecord(page: Page, addButton: string, fields: Record<string, string>) {
  await page.getByRole("button", { name: addButton }).first().click();
  const dialog = page.getByRole("dialog");
  for (const [label, value] of Object.entries(fields)) {
    await dialog.getByLabel(label).fill(value);
  }
  await dialog.getByRole("button", { name: "Add", exact: true }).click();
  await expect(dialog).toBeHidden();
}

test("Spare Parts flagship: install, search, receive 100, sell 5, sales document, files, persistence", async ({ page }) => {
  test.setTimeout(240_000);

  const externalRequests: string[] = [];
  await page.route("**/*", async (route) => {
    const url = new URL(route.request().url());
    if (!["localhost", "127.0.0.1"].includes(url.hostname)) {
      externalRequests.push(url.origin);
      await route.abort();
    } else {
      await route.continue();
    }
  });

  // --- account, organization, project -----------------------------------------------------
  await register(page, uniqueEmail("flagship"));
  const orgId = await createOrganization(page, "Harmoney Auto Parts LLC — DEMO");
  await page.getByRole("button", { name: "New workspace" }).first().click();
  await page.getByLabel("Name", { exact: true }).fill("Company");
  await page.getByRole("dialog").getByRole("button", { name: "Create", exact: true }).click();
  await page.getByRole("link", { name: /Company/ }).click();
  await page.getByRole("button", { name: "New project" }).first().click();
  await page.getByLabel("Name", { exact: true }).fill("Shop");
  await page.getByRole("dialog").getByRole("button", { name: "Create", exact: true }).click();
  await page.getByRole("link", { name: /Shop/ }).click();
  await expect(page).toHaveURL(/\/projects\/[0-9a-f-]+$/);
  expect(orgId).toBeTruthy();

  // --- application gallery -> install Spare Parts -----------------------------------------
  await page.locator('a[href$="/apps"]').first().click();
  await expect(page).toHaveURL(/\/projects\/[0-9a-f-]+\/apps$/);
  const card = page.getByRole("article", { name: "Spare Parts" });
  // Honestly labelled, never "ready for use": the status BADGE (exact text) and, separately, the warning.
  await expect(card.getByText("Pilot preview", { exact: true })).toBeVisible();
  await expect(card.getByText(/has not completed production qualification/)).toBeVisible();
  await expect(card.getByText("Ready for use")).toHaveCount(0);
  await expect(page.getByRole("article", { name: /Customer Pipeline|Procurement|Asset Register/ })).toHaveCount(0); // deferred apps are not offered
  await card.getByRole("button", { name: "Install" }).click();
  const install = page.getByRole("dialog", { name: "Install Spare Parts" });
  await expect(install.getByRole("button", { name: "Install", exact: true })).toBeDisabled(); // preview needs acknowledging
  await install.getByRole("checkbox", { name: "I understand this is a preview" }).check();
  await install.getByRole("button", { name: "Install", exact: true }).click();
  await expect(install.getByText(/Spare Parts is ready/)).toBeVisible({ timeout: 90_000 });
  await install.getByRole("link", { name: "Open application" }).click();
  await expect(page).toHaveURL(/\/apps\/[0-9a-f-]+$/);
  const appHome = page.url();

  // --- supplier, warehouse, product, part number ------------------------------------------
  await nav(page).getByRole("link", { name: "Suppliers" }).click();
  await addRecord(page, "Add supplier", { Name: "Demo Supplier A" });
  await expect(page.getByRole("cell", { name: "Demo Supplier A" })).toBeVisible();

  await nav(page).getByRole("link", { name: "Warehouses" }).click();
  await addRecord(page, "Add warehouse", { Name: "Main Warehouse", Code: "MAIN" });
  await expect(page.getByRole("cell", { name: "Main Warehouse" })).toBeVisible();

  await nav(page).getByRole("link", { name: "Products" }).click();
  await addRecord(page, "Add product", { Name: "Demo Oil Filter", "List price": "15.00" });
  await expect(page.getByRole("link", { name: "Demo Oil Filter" })).toBeVisible();

  await nav(page).getByRole("link", { name: "Part numbers" }).click();
  await page.getByRole("button", { name: "Add part number" }).first().click();
  const numberDialog = page.getByRole("dialog");
  await numberDialog.getByRole("combobox", { name: "Product", exact: true }).fill("Oil");
  await numberDialog.getByRole("option", { name: /Demo Oil Filter/ }).click();
  await numberDialog.getByLabel("Part number").fill("04465-0K290");
  await numberDialog.getByLabel("Source").fill("OEM (demo)");
  await numberDialog.getByRole("button", { name: "Add", exact: true }).click();
  await expect(numberDialog).toBeHidden();

  // --- normalized search: a different written form finds the same part, original preserved ---
  const headerSearch = page.getByLabel("Search part numbers").first();
  await headerSearch.fill("044650K290");
  await headerSearch.press("Enter");
  await expect(page).toHaveURL(/part-numbers\?q=044650K290/);
  await expect(page.getByRole("cell", { name: /04465-0K290/ })).toBeVisible(); // display value preserved
  await expect(page.getByRole("link", { name: "Demo Oil Filter" })).toBeVisible();
  await expect(page.getByText("Exact", { exact: true })).toBeVisible();
  await headerSearch.fill("04465 0k290");
  await headerSearch.press("Enter");
  await expect(page.getByRole("cell", { name: /04465-0K290/ })).toBeVisible(); // spaces and case don't matter

  // --- receive 100 -> inventory 100 -------------------------------------------------------
  await nav(page).getByRole("link", { name: "Receive stock" }).click();
  await page.getByRole("combobox", { name: "Product", exact: true }).fill("044650K290"); // find the product BY PART NUMBER
  await page.getByRole("option", { name: /Demo Oil Filter/ }).click();
  await page.getByLabel("Warehouse").selectOption({ label: "Main Warehouse" });
  await page.getByLabel("Quantity").fill("100");
  await page.getByLabel("Supplier").selectOption({ label: "Demo Supplier A" });
  await page.getByLabel("Unit cost").fill("9.50");
  await page.getByLabel("Reference").fill("DN-1001 (demo)");
  await page.getByRole("button", { name: "Confirm receive" }).click();
  await expect(page.getByText("Stock received")).toBeVisible();
  await expect(page.getByTestId("on-hand-now")).toHaveText("100");

  await nav(page).getByRole("link", { name: "Stock", exact: true }).click();
  await expect(stockRow(page, "100")).toBeVisible();

  // --- customer, sell 5 -> inventory 95 ---------------------------------------------------
  await nav(page).getByRole("link", { name: "Customers" }).click();
  await addRecord(page, "Add customer", { Name: "Demo Retail Customer" });
  await expect(page.getByRole("cell", { name: "Demo Retail Customer" })).toBeVisible();

  await nav(page).getByRole("link", { name: "New sale" }).click();
  await page.getByLabel("Customer", { exact: true }).selectOption({ label: "Demo Retail Customer" });
  await page.getByRole("combobox", { name: "Product (item 1)", exact: true }).fill("04465 0K290"); // yet another written form of the number
  await page.getByRole("option", { name: /Demo Oil Filter/ }).click();
  await page.getByLabel("Warehouse").selectOption({ label: "Main Warehouse" });
  await page.getByLabel("Quantity").fill("5");
  await expect(page.getByLabel("Unit price")).toHaveValue("15.00"); // prefilled from the product's list price
  await expect(page.getByText("75.00")).toBeVisible();
  await page.getByRole("button", { name: "Confirm sale" }).click();
  await expect(page.getByText("Sale complete")).toBeVisible();
  await expect(page.getByTestId("on-hand-after-sale")).toHaveText("95");

  // --- sales document and the movement it created -----------------------------------------
  await page.getByRole("link", { name: "Open sales document" }).click();
  await expect(page.getByRole("heading", { name: /Invoice INV-\d{8}-[0-9A-Z]{5}/ })).toBeVisible();
  await expect(page.getByTestId("amount-due")).toHaveText("75.00");
  await expect(page.getByText("Demo Retail Customer", { exact: true })).toBeVisible();
  await expect(page.getByTestId("movement-change")).toHaveText("-5");

  // --- inventory 95, persisted across a reload --------------------------------------------
  await nav(page).getByRole("link", { name: "Stock", exact: true }).click();
  await expect(stockRow(page, "95")).toBeVisible();
  await page.reload();
  await expect(stockRow(page, "95")).toBeVisible();
  // history shows the receipt and the sale, newest first
  await expect(movementsRegion(page).getByRole("cell", { name: "+100", exact: true })).toBeVisible();
  await expect(movementsRegion(page).getByRole("cell", { name: "-5", exact: true })).toBeVisible();
  await expect(movementsRegion(page).locator("tbody tr")).toHaveCount(2); // exactly the receipt and the sale

  // --- files: attach a real document to the product ---------------------------------------
  await nav(page).getByRole("link", { name: "Products" }).click();
  await page.getByRole("link", { name: "Demo Oil Filter" }).click();
  await page.getByRole("tab", { name: "Files" }).click();
  await page.getByLabel("Add an image or document").setInputFiles({
    name: "oil-filter-datasheet-demo.txt",
    mimeType: "text/plain",
    buffer: Buffer.from("DEMO data sheet: fictional document for the flagship journey.\n"),
  });
  await expect(page.getByRole("link", { name: "oil-filter-datasheet-demo.txt" })).toBeVisible({ timeout: 30_000 });
  await page.reload();
  await page.getByRole("tab", { name: "Files" }).click();
  const datasheet = page.getByRole("link", { name: "oil-filter-datasheet-demo.txt" });
  await expect(datasheet).toBeVisible();
  // Opening it really downloads the stored bytes back from object storage.
  const [download] = await Promise.all([page.waitForEvent("download"), datasheet.click()]);
  const chunks: Buffer[] = [];
  for await (const chunk of await download.createReadStream()) chunks.push(Buffer.from(chunk));
  expect(Buffer.concat(chunks).toString("utf-8")).toContain("fictional document for the flagship journey");

  // --- the database still refuses an oversell, through the UI ------------------------------
  await nav(page).getByRole("link", { name: "New sale" }).click();
  await page.getByLabel("Customer", { exact: true }).selectOption({ label: "Demo Retail Customer" });
  await page.getByRole("combobox", { name: "Product (item 1)", exact: true }).fill("Demo Oil");
  await page.getByRole("option", { name: /Demo Oil Filter/ }).click();
  await page.getByLabel("Warehouse").selectOption({ label: "Main Warehouse" });
  await page.getByLabel("Quantity").fill("96");
  await page.getByRole("button", { name: "Confirm sale" }).click();
  // (Next.js keeps its own global role=alert route announcer, so pick the error by its content.)
  const refusal = page.getByRole("alert").filter({ hasText: "not enough stock" });
  await expect(refusal).toBeVisible();
  await expect(refusal).toContainText("Nothing was changed");
  await expect(page.getByText("Sale complete")).toHaveCount(0);
  await nav(page).getByRole("link", { name: "Stock", exact: true }).click();
  await expect(stockRow(page, "95")).toBeVisible(); // unchanged
  await expect(movementsRegion(page).locator("tbody tr")).toHaveCount(2); // no movement was left behind
  await nav(page).getByRole("link", { name: "Sales", exact: true }).click();
  await expect(page.getByRole("link", { name: "Open sale" })).toHaveCount(1); // no ghost order was left behind

  // --- the app is still reachable from the gallery, and nothing needed the internet -------
  await page.goto(appHome);
  await expect(page.getByText("At a glance")).toBeVisible();
  // The app's own totals agree: exactly one sale exists (the refused one left nothing behind).
  await expect(page.getByRole("link", { name: "Sales 1", exact: true })).toBeVisible();
  expect(externalRequests).toEqual([]);
});
