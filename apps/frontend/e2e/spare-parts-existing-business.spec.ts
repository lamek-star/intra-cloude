import { test, expect, type Page } from "@playwright/test";
import { readFileSync } from "node:fs";
import { nav } from "./flagship-setup";
import { login } from "./helpers";

// Checks, THROUGH THE BROWSER, that a business built earlier through the UI (see
// spare-parts-recovery-prep.spec.ts) is intact and usable -- after a template upgrade, or after a
// destructive restore into a freshly initialized installation. Real logins with the original passwords,
// no fixtures created here. Read-only unless UI_OPERATE=1, which also records one real sale (as the
// restricted cashier) and one real receive (as the owner) so the restored/upgraded system is shown to
// keep working, not merely to hold old data.
//
//   UI_STATE_FILE      the JSON the prep spec wrote (required)
//   EXPECT_STOCK       on-hand quantity that must be shown (default: the prepared 95)
//   EXPECT_MOVEMENTS   number of stock movements that must be listed (default 2: the receive and the sale)
//   UI_OPERATE=1       additionally sell 1 (cashier) and receive 1 (owner) through the UI

const STATE_FILE = process.env.UI_STATE_FILE;
type State = {
  owner: { email: string; password: string };
  cashier: { email: string; password: string };
  appHome: string;
  productUrl: string;
  invoiceNumber: string;
  salesDocumentUrl: string;
  onHand: number;
};
const state: State | null = STATE_FILE ? (JSON.parse(readFileSync(STATE_FILE, "utf-8")) as State) : null;
const expectStock = process.env.EXPECT_STOCK ?? String(state?.onHand ?? 95);
const expectMovements = Number(process.env.EXPECT_MOVEMENTS ?? "2");
const operate = process.env.UI_OPERATE === "1";

const stockRegion = (page: Page) => page.getByRole("region", { name: "Stock", exact: true });
const movementsRegion = (page: Page) => page.getByRole("region", { name: "Recent stock movements", exact: true });
const stockRow = (page: Page, onHand: string) =>
  stockRegion(page)
    .getByRole("row")
    .filter({ has: page.getByRole("cell", { name: "Demo Oil Filter", exact: true }) })
    .filter({ has: page.getByRole("cell", { name: "Main Warehouse", exact: true }) })
    .filter({ has: page.getByRole("cell", { name: onHand, exact: true }) });

test.describe("an existing UI-built business", () => {
  test.skip(!state, "set UI_STATE_FILE");

  test("the owner logs in and finds everything, byte for byte", async ({ page }) => {
    test.setTimeout(120_000);
    await login(page, state!.owner.email, state!.owner.password);
    await page.goto(state!.appHome);
    await expect(nav(page)).toBeVisible();

    // A differently written part number still finds the product, with the original number preserved.
    const headerSearch = page.getByLabel("Find a part number");
    await headerSearch.fill("044650K290");
    await headerSearch.press("Enter");
    await expect(page.getByRole("cell", { name: /04465-0K290/ })).toBeVisible();
    await expect(page.getByRole("link", { name: "Demo Oil Filter" })).toBeVisible();

    await nav(page).getByRole("link", { name: "Suppliers" }).click();
    await expect(page.getByRole("cell", { name: "Demo Supplier A" })).toBeVisible();
    await nav(page).getByRole("link", { name: "Warehouses" }).click();
    await expect(page.getByRole("cell", { name: "Main Warehouse" })).toBeVisible();
    await nav(page).getByRole("link", { name: "Customers" }).click();
    await expect(page.getByRole("cell", { name: "Demo Retail Customer" })).toBeVisible();

    await nav(page).getByRole("link", { name: "Stock", exact: true }).click();
    await expect(stockRow(page, expectStock)).toBeVisible();
    await expect(movementsRegion(page).locator("tbody tr")).toHaveCount(expectMovements);
    await expect(movementsRegion(page).getByRole("cell", { name: "+100", exact: true })).toBeVisible();

    // The sales document: order, line and invoice, still one linked document.
    await page.goto(state!.salesDocumentUrl);
    await expect(page.getByRole("heading", { name: `Invoice ${state!.invoiceNumber}` })).toBeVisible();
    await expect(page.getByText("Demo Oil Filter").first()).toBeVisible();

    // The stored document comes back from object storage with its own bytes.
    await page.goto(state!.productUrl);
    await page.getByRole("tab", { name: "Files" }).click();
    const datasheet = page.getByRole("link", { name: "oil-filter-datasheet-demo.txt" });
    await expect(datasheet).toBeVisible({ timeout: 30_000 });
    const [download] = await Promise.all([page.waitForEvent("download"), datasheet.click()]);
    const chunks: Buffer[] = [];
    for await (const chunk of await download.createReadStream()) chunks.push(Buffer.from(chunk));
    expect(Buffer.concat(chunks).toString("utf-8")).toContain("fictional document for the flagship journey");
  });

  test("the restricted cashier logs in, finds a product, and is still refused what they never had", async ({ page }) => {
    test.setTimeout(120_000);
    await login(page, state!.cashier.email, state!.cashier.password);
    await page.goto(state!.appHome);
    const headerSearch = page.getByLabel("Find a part number");
    await headerSearch.fill("04465 0k290");
    await headerSearch.press("Enter");
    await expect(page.getByRole("link", { name: "Demo Oil Filter" })).toBeVisible();

    await page.goto(`${state!.appHome}/suppliers`);
    await expect(page.getByText(/permission/i).first()).toBeVisible({ timeout: 15_000 });
    await expect(page.locator("body")).not.toContainText("Demo Supplier A");
    await page.goto(state!.productUrl);
    await page.getByRole("tab", { name: "Files" }).click();
    await expect(page.locator("body")).not.toContainText("oil-filter-datasheet-demo");
  });

  test("the business keeps operating: the cashier sells 1 and the owner receives 1", async ({ browser }) => {
    test.skip(!operate, "set UI_OPERATE=1 to record a sale and a receive");
    test.setTimeout(180_000);
    const before = Number(expectStock);

    const cashierContext = await browser.newContext();
    const cashier = await cashierContext.newPage();
    await login(cashier, state!.cashier.email, state!.cashier.password);
    await cashier.goto(`${state!.appHome}/sales/new`);
    await cashier.getByLabel("Customer", { exact: true }).selectOption({ label: "Demo Retail Customer" });
    await cashier.getByRole("combobox", { name: "Product (item 1)", exact: true }).fill("04465-0K290");
    await cashier.getByRole("option", { name: /Demo Oil Filter/ }).click();
    await cashier.getByLabel("Warehouse").selectOption({ label: "Main Warehouse" });
    await cashier.getByLabel("Quantity").fill("1");
    await cashier.getByRole("button", { name: "Confirm sale" }).click();
    await expect(cashier.getByTestId("on-hand-after-sale")).toHaveText(String(before - 1));
    await cashierContext.close();

    const ownerContext = await browser.newContext();
    const owner = await ownerContext.newPage();
    await login(owner, state!.owner.email, state!.owner.password);
    await owner.goto(`${state!.appHome}/receive`);
    await owner.getByRole("combobox", { name: "Product", exact: true }).fill("044650K290");
    await owner.getByRole("option", { name: /Demo Oil Filter/ }).click();
    await owner.getByLabel("Warehouse").selectOption({ label: "Main Warehouse" });
    await owner.getByLabel("Quantity").fill("1");
    await owner.getByRole("button", { name: "Confirm receive" }).click();
    await expect(owner.getByTestId("on-hand-now")).toHaveText(String(before));
    await ownerContext.close();
  });
});
