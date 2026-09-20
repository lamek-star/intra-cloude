import AxeBuilder from "@axe-core/playwright";
import { test, expect, type Page } from "@playwright/test";
import { buildFlagshipBusiness, nav, type FlagshipBusiness } from "./flagship-setup";

// Accessibility qualification of the customer-facing Local Edition screens: an automated axe scan of
// every new screen and state, plus keyboard-only paths that automation alone cannot prove usable.
// One account is registered (auth is rate limited on purpose); every scan reuses that UI-built business.

test.describe("Spare Parts accessibility", () => {
  test.setTimeout(300_000);
  let page: Page;
  let biz: FlagshipBusiness;
  const findings: { screen: string; id: string; impact: string; nodes: number; help: string; target: string }[] = [];

  test.beforeAll(async ({ browser }) => {
    const context = await browser.newContext({
      baseURL: process.env.E2E_BASE_URL ?? "https://localhost:8443",
      ignoreHTTPSErrors: true,
    });
    page = await context.newPage();
    biz = await buildFlagshipBusiness(page, { withFile: true, prefix: "a11y" });
  });

  test.afterAll(async ({}, testInfo) => {
    await testInfo.attach("axe-findings", { body: JSON.stringify(findings, null, 2), contentType: "application/json" });
    console.log(`AXE FINDINGS (${findings.length}):\n` + findings.map((f) => `  [${f.impact}] ${f.screen}: ${f.id} x${f.nodes} — ${f.help} :: ${f.target}`).join("\n"));
    await page.context().close();
  });

  async function scan(screen: string) {
    const results = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "best-practice"])
      .analyze();
    for (const v of results.violations) {
      findings.push({
        screen,
        id: v.id,
        impact: v.impact ?? "n/a",
        nodes: v.nodes.length,
        help: v.help,
        target: String(v.nodes[0]?.target ?? ""),
      });
    }
    return results.violations;
  }

  const screens: [string, () => Promise<void>][] = [
    ["Application gallery", async () => { await page.goto(`${biz.projectUrl}/apps`); await expect(page.getByRole("article", { name: "Spare Parts" })).toBeVisible(); }],
    ["Install dialog (review)", async () => {
      await page.goto(`${biz.projectUrl}/apps`);
      await page.getByRole("button", { name: "Install another copy" }).click();
      await expect(page.getByRole("dialog", { name: "Install Spare Parts" })).toBeVisible();
    }],
    ["Spare Parts home", async () => { await page.goto(biz.appHome); await expect(page.getByText("At a glance")).toBeVisible(); }],
    ["Products", async () => { await page.goto(`${biz.appHome}/products`); await expect(page.getByRole("link", { name: "Demo Oil Filter" })).toBeVisible(); }],
    ["Add product dialog", async () => {
      await page.goto(`${biz.appHome}/products`);
      await page.getByRole("button", { name: "Add product" }).first().click();
      await expect(page.getByRole("dialog")).toBeVisible();
    }],
    ["Product detail: Overview", async () => { await page.goto(biz.productUrl); await expect(page.getByRole("tab", { name: "Overview" })).toBeVisible(); }],
    ["Product detail: Part numbers", async () => { await page.goto(biz.productUrl); await page.getByRole("tab", { name: "Part numbers" }).click(); await expect(page.getByRole("cell", { name: "04465-0K290" })).toBeVisible(); }],
    ["Product detail: Stock", async () => { await page.goto(biz.productUrl); await page.getByRole("tab", { name: "Stock" }).click(); await expect(page.getByRole("cell", { name: "95", exact: true })).toBeVisible(); }],
    ["Product detail: Movements", async () => { await page.goto(biz.productUrl); await page.getByRole("tab", { name: "Movements" }).click(); await expect(page.getByRole("cell", { name: "+100", exact: true })).toBeVisible(); }],
    ["Product detail: Files", async () => { await page.goto(biz.productUrl); await page.getByRole("tab", { name: "Files" }).click(); await expect(page.getByRole("link", { name: "oil-filter-datasheet-demo.txt" })).toBeVisible(); }],
    ["Part number search (results)", async () => { await page.goto(`${biz.appHome}/part-numbers?q=044650K290`); await expect(page.getByRole("cell", { name: /04465-0K290/ })).toBeVisible(); }],
    ["Part number search (no match)", async () => { await page.goto(`${biz.appHome}/part-numbers?q=ZZZ999`); await expect(page.getByText(/No part number matches/)).toBeVisible(); }],
    ["Stock and movements", async () => { await page.goto(`${biz.appHome}/inventory`); await expect(page.getByRole("region", { name: "Stock", exact: true })).toBeVisible(); await expect(page.getByRole("cell", { name: "+100", exact: true })).toBeVisible(); }],
    ["Warehouses", async () => { await page.goto(`${biz.appHome}/warehouses`); await expect(page.getByRole("cell", { name: "Main Warehouse" })).toBeVisible(); }],
    ["Suppliers", async () => { await page.goto(`${biz.appHome}/suppliers`); await expect(page.getByRole("cell", { name: "Demo Supplier A" })).toBeVisible(); }],
    ["Customers", async () => { await page.goto(`${biz.appHome}/customers`); await expect(page.getByRole("cell", { name: "Demo Retail Customer" })).toBeVisible(); }],
    ["Receive stock (empty)", async () => { await page.goto(`${biz.appHome}/receive`); await expect(page.getByRole("button", { name: "Confirm receive" })).toBeVisible(); }],
    ["Receive stock (validation errors)", async () => {
      await page.goto(`${biz.appHome}/receive`);
      await page.getByRole("button", { name: "Confirm receive" }).click();
      await expect(page.getByRole("alert").filter({ hasText: "Choose the product" })).toBeVisible();
    }],
    ["New sale (empty)", async () => { await page.goto(`${biz.appHome}/sales/new`); await expect(page.getByRole("button", { name: "Confirm sale" })).toBeVisible(); }],
    ["New sale (validation errors)", async () => {
      await page.goto(`${biz.appHome}/sales/new`);
      await page.getByRole("button", { name: "Confirm sale" }).click();
      await expect(page.getByRole("alert").filter({ hasText: "Choose the customer" })).toBeVisible();
    }],
    ["Sales list", async () => { await page.goto(`${biz.appHome}/sales`); await expect(page.getByRole("link", { name: "Open sale" })).toBeVisible(); }],
    ["Sales document", async () => { await page.goto(biz.salesDocumentUrl); await expect(page.getByRole("heading", { name: /Invoice INV-/ })).toBeVisible(); }],
    // The owner's page for granting business-operation authority (ADR-0017), and its Share dialog.
    ["Business operations access", async () => {
      await page.goto(`/app-instances/${biz.instanceId}`);
      await expect(page.getByRole("heading", { name: "Business operations" })).toBeVisible();
    }],
    ["Business operations: grant dialog", async () => {
      await page.goto(`/app-instances/${biz.instanceId}`);
      const section = page.locator("section").filter({ has: page.getByRole("heading", { name: "Business operations" }) });
      await section.getByRole("button", { name: "Share" }).click();
      const dialog = page.getByRole("dialog");
      await expect(dialog).toBeVisible();
      await expect(dialog.getByLabel("Access level").locator("option")).toHaveText(["Sell", "Receive"]);
    }],
  ];

  for (const [name, arrive] of screens) {
    test(`axe: ${name}`, async () => {
      await arrive();
      const violations = await scan(name);
      expect(
        violations.map((v) => `${v.id} [${v.impact}] x${v.nodes.length}: ${v.help}`),
        `accessibility violations on "${name}"`,
      ).toEqual([]);
    });
  }

  // ---------- keyboard-only paths --------------------------------------------------------------

  test("keyboard: the install dialog opens, holds focus, and returns focus on Escape", async () => {
    await page.goto(`${biz.projectUrl}/apps`);
    const opener = page.getByRole("button", { name: "Install another copy" });
    await opener.focus();
    await page.keyboard.press("Enter");
    const dialog = page.getByRole("dialog", { name: "Install Spare Parts" });
    await expect(dialog).toBeVisible();
    expect(await dialog.evaluate((el) => el.contains(document.activeElement))).toBe(true); // focus moved inside
    for (let i = 0; i < 8; i++) {
      await page.keyboard.press("Tab");
      expect(await dialog.evaluate((el) => el.contains(document.activeElement))).toBe(true); // Tab never leaves it
    }
    await page.keyboard.press("Escape");
    await expect(dialog).toBeHidden();
    await expect(opener).toBeFocused(); // focus returns to what opened it
  });

  test("keyboard: product tabs follow the ARIA tabs pattern (arrows, Home, End, roving tab stop)", async () => {
    await page.goto(biz.productUrl);
    const overview = page.getByRole("tab", { name: "Overview" });
    await overview.focus();
    await page.keyboard.press("ArrowRight");
    await expect(page.getByRole("tab", { name: "Part numbers" })).toBeFocused();
    await expect(page.getByRole("tab", { name: "Part numbers" })).toHaveAttribute("aria-selected", "true");
    await page.keyboard.press("End");
    await expect(page.getByRole("tab", { name: "Files" })).toBeFocused();
    await page.keyboard.press("ArrowRight"); // wraps
    await expect(overview).toBeFocused();
    await page.keyboard.press("ArrowLeft"); // wraps back
    await expect(page.getByRole("tab", { name: "Files" })).toBeFocused();
    await page.keyboard.press("Home");
    await expect(overview).toBeFocused();
    // only the selected tab is in the Tab order (roving tabindex)
    await expect(page.getByRole("tab", { name: "Files" })).toHaveAttribute("tabindex", "-1");
    await expect(overview).toHaveAttribute("tabindex", "0");
  });

  test("keyboard: pick a product with the arrow keys and Enter, complete and submit a form", async () => {
    await page.goto(`${biz.appHome}/receive`);
    const picker = page.getByRole("combobox", { name: "Product", exact: true });
    await picker.focus();
    await page.keyboard.type("044650K290");
    await expect(page.getByRole("option", { name: /Demo Oil Filter/ })).toBeVisible();
    await page.keyboard.press("ArrowDown");
    await expect(page.getByRole("option", { name: /Demo Oil Filter/ })).toBeFocused();
    await page.keyboard.press("Enter");
    await expect(page.getByText("Demo Oil Filter").first()).toBeVisible();
    await expect(page.getByRole("button", { name: "Change product" })).toBeFocused(); // focus lands somewhere sensible

    await page.getByLabel("Warehouse").focus();
    await page.keyboard.press("ArrowDown"); // native select: first real option
    await page.getByLabel("Quantity").focus();
    await page.keyboard.type("7");
    await page.keyboard.press("Enter"); // Enter submits the form
    await expect(page.getByText("Stock received")).toBeVisible();
    await expect(page.getByTestId("on-hand-now")).toHaveText("102");
  });

  test("keyboard: an Add dialog can be filled and dismissed without a mouse; errors are announced", async () => {
    await page.goto(`${biz.appHome}/suppliers`);
    const add = page.getByRole("button", { name: "Add supplier" }).first();
    await add.focus();
    await page.keyboard.press("Enter");
    const dialog = page.getByRole("dialog");
    await expect(dialog).toBeVisible();
    await page.keyboard.press("Enter"); // submit empty: a required-field error, announced as an alert
    await expect(dialog.getByRole("alert")).toContainText("Name is required");
    await page.keyboard.press("Escape");
    await expect(dialog).toBeHidden();
    await expect(add).toBeFocused();
  });

  test("keyboard: every interactive control on the sell page is reachable in a sensible Tab order", async () => {
    await page.goto(`${biz.appHome}/sales/new`);
    await expect(page.getByRole("button", { name: "Confirm sale" })).toBeVisible();
    type Stop = { name: string; tag: string; html: string };
    const stops: Stop[] = [];
    for (let i = 0; i < 40; i++) {
      await page.keyboard.press("Tab");
      stops.push(
        await page.evaluate(() => {
          const el = document.activeElement as HTMLElement | null;
          if (!el || el === document.body) return { name: "", tag: "BODY", html: "" };
          const labelled = (el as HTMLInputElement).labels?.[0]?.textContent;
          const name = (el.getAttribute("aria-label") || labelled || el.textContent || "").trim().slice(0, 40);
          return { name, tag: el.tagName, html: el.outerHTML.slice(0, 140) };
        }),
      );
    }
    // Every keyboard stop has an accessible name (report the offending element, not just the count).
    expect(stops.filter((stop) => stop.name === "" && stop.tag !== "BODY").map((stop) => `${stop.tag}: ${stop.html}`)).toEqual([]);
    // ...and the form's own controls come in reading order.
    const names = stops.map((stop) => stop.name);
    // Exact accessible names: the navigation also has links called "Customers" and "Warehouses".
    const idx = (text: string) => names.indexOf(text);
    expect(idx("Customer")).toBeGreaterThan(-1);
    expect(idx("Product (item 1)")).toBeGreaterThan(idx("Customer"));
    expect(idx("Warehouse")).toBeGreaterThan(idx("Product (item 1)"));
    expect(idx("Quantity")).toBeGreaterThan(idx("Warehouse"));
    expect(idx("Unit price")).toBeGreaterThan(idx("Quantity"));
    expect(idx("Confirm sale")).toBeGreaterThan(idx("Unit price"));
    void nav;
  });
});
