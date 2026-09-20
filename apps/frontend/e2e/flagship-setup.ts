import { expect, type Page } from "@playwright/test";
import { createOrganization, register, uniqueEmail } from "./helpers";

// Builds the flagship business THROUGH THE CUSTOMER UI (no shortcuts, no seeding): the same steps as
// spare-parts-flagship.spec.ts, packaged so the accessibility, restricted-cashier and disaster-recovery
// gates can start from a real, UI-built instance. Registers ONE account (the auth endpoints are rate
// limited to 10/minute on purpose -- do not loop this helper).

export const DEMO_PASSWORD = "correct-horse-battery-9";
export const nav = (page: Page) => page.getByRole("navigation", { name: "Application sections" });

export async function addRecord(page: Page, addButton: string, fields: Record<string, string>) {
  await page.getByRole("button", { name: addButton }).first().click();
  const dialog = page.getByRole("dialog");
  for (const [label, value] of Object.entries(fields)) await dialog.getByLabel(label).fill(value);
  await dialog.getByRole("button", { name: "Add", exact: true }).click();
  await expect(dialog).toBeHidden();
}

export type FlagshipBusiness = {
  email: string;
  password: string;
  orgId: string;
  orgName: string;
  projectUrl: string;
  workspaceId: string;
  appHome: string;
  instanceId: string;
  salesDocumentUrl: string;
  productUrl: string;
  invoiceNumber: string;
};

export async function buildFlagshipBusiness(
  page: Page,
  opts: { withFile?: boolean; prefix?: string } = {},
): Promise<FlagshipBusiness> {
  const email = uniqueEmail(opts.prefix ?? "flagship");
  await register(page, email, DEMO_PASSWORD);
  const orgName = "Harmoney Auto Parts LLC — DEMO";
  const orgId = await createOrganization(page, orgName);
  await page.getByRole("button", { name: "New workspace" }).first().click();
  await page.getByLabel("Name", { exact: true }).fill("Company");
  await page.getByRole("dialog").getByRole("button", { name: "Create", exact: true }).click();
  await page.getByRole("link", { name: /Company/ }).click();
  await expect(page).toHaveURL(/\/workspaces\/[0-9a-f-]{36}$/);
  const workspaceId = new URL(page.url()).pathname.split("/workspaces/")[1];
  await page.getByRole("button", { name: "New project" }).first().click();
  await page.getByLabel("Name", { exact: true }).fill("Shop");
  await page.getByRole("dialog").getByRole("button", { name: "Create", exact: true }).click();
  await page.getByRole("link", { name: /Shop/ }).click();
  await expect(page).toHaveURL(/\/projects\/[0-9a-f-]+$/);
  const projectUrl = page.url();

  await page.locator('a[href$="/apps"]').first().click();
  const card = page.getByRole("article", { name: "Spare Parts" });
  await card.getByRole("button", { name: "Install" }).click();
  const install = page.getByRole("dialog", { name: "Install Spare Parts" });
  // A QUALIFIED application needs no preview acknowledgement.
  await expect(install.getByRole("checkbox", { name: "I understand this is a preview" })).toHaveCount(0);
  await install.getByRole("button", { name: "Install", exact: true }).click();
  await expect(install.getByText(/Spare Parts is ready/)).toBeVisible({ timeout: 90_000 });
  await install.getByRole("link", { name: "Open application" }).click();
  await expect(page).toHaveURL(/\/apps\/[0-9a-f-]+$/);
  const appHome = page.url();
  const instanceId = appHome.split("/apps/")[1];

  await nav(page).getByRole("link", { name: "Suppliers" }).click();
  await addRecord(page, "Add supplier", { Name: "Demo Supplier A" });
  await nav(page).getByRole("link", { name: "Warehouses" }).click();
  await addRecord(page, "Add warehouse", { Name: "Main Warehouse", Code: "MAIN" });
  await nav(page).getByRole("link", { name: "Products" }).click();
  await addRecord(page, "Add product", { Name: "Demo Oil Filter", "List price": "15.00" });
  await expect(page.getByRole("link", { name: "Demo Oil Filter" })).toBeVisible();
  const productUrl = await page.getByRole("link", { name: "Demo Oil Filter" }).getAttribute("href");

  await nav(page).getByRole("link", { name: "Part numbers" }).click();
  await page.getByRole("button", { name: "Add part number" }).first().click();
  const numberDialog = page.getByRole("dialog");
  await numberDialog.getByRole("combobox", { name: "Product", exact: true }).fill("Oil");
  await numberDialog.getByRole("option", { name: /Demo Oil Filter/ }).click();
  await numberDialog.getByLabel("Part number").fill("04465-0K290");
  await numberDialog.getByLabel("Source").fill("OEM (demo)");
  await numberDialog.getByRole("button", { name: "Add", exact: true }).click();
  await expect(numberDialog).toBeHidden();

  await nav(page).getByRole("link", { name: "Receive stock" }).click();
  await page.getByRole("combobox", { name: "Product", exact: true }).fill("044650K290");
  await page.getByRole("option", { name: /Demo Oil Filter/ }).click();
  await page.getByLabel("Warehouse").selectOption({ label: "Main Warehouse" });
  await page.getByLabel("Quantity").fill("100");
  await page.getByLabel("Supplier").selectOption({ label: "Demo Supplier A" });
  await page.getByLabel("Unit cost").fill("9.50");
  await page.getByLabel("Reference").fill("DN-1001 (demo)");
  await page.getByRole("button", { name: "Confirm receive" }).click();
  await expect(page.getByTestId("on-hand-now")).toHaveText("100");

  await nav(page).getByRole("link", { name: "Customers" }).click();
  await addRecord(page, "Add customer", { Name: "Demo Retail Customer" });
  await nav(page).getByRole("link", { name: "New sale" }).click();
  await page.getByLabel("Customer", { exact: true }).selectOption({ label: "Demo Retail Customer" });
  await page.getByRole("combobox", { name: "Product (item 1)", exact: true }).fill("04465 0K290");
  await page.getByRole("option", { name: /Demo Oil Filter/ }).click();
  await page.getByLabel("Warehouse").selectOption({ label: "Main Warehouse" });
  await page.getByLabel("Quantity").fill("5");
  await page.getByRole("button", { name: "Confirm sale" }).click();
  await expect(page.getByTestId("on-hand-after-sale")).toHaveText("95");
  await page.getByRole("link", { name: "Open sales document" }).click();
  const heading = await page.getByRole("heading", { name: /Invoice INV-\d{8}-[0-9A-Z]{5}/ }).innerText();
  const invoiceNumber = heading.replace("Invoice ", "").trim();
  const salesDocumentUrl = page.url();

  if (opts.withFile) {
    await page.goto(`${productUrl}`);
    await page.getByRole("tab", { name: "Files" }).click();
    await page.getByLabel("Add an image or document").setInputFiles({
      name: "oil-filter-datasheet-demo.txt",
      mimeType: "text/plain",
      buffer: Buffer.from("DEMO data sheet: fictional document for the flagship journey.\n"),
    });
    await expect(page.getByRole("link", { name: "oil-filter-datasheet-demo.txt" })).toBeVisible({ timeout: 30_000 });
  }

  return {
    email,
    password: DEMO_PASSWORD,
    orgId,
    orgName,
    projectUrl,
    workspaceId,
    appHome,
    instanceId,
    salesDocumentUrl,
    productUrl: productUrl ?? "",
    invoiceNumber,
  };
}
