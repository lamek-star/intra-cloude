import { test, expect, type Page } from "@playwright/test";
import { login } from "./helpers";

// Scale qualification, browser side: with the generated dataset (5,000 products, 10,000 part numbers,
// 10,000 movements, 500 customers) how many requests does each screen make, how many bytes come back and
// how long until it settles? Measurement only -- it reports; the assertions are loose ceilings that would
// catch an N+1 or an unbounded fetch, not tuned to today's numbers. The dataset is created by
// scripts/qualification/scale (never through Playwright). Needs SCALE_APP (the instance id) and the scale
// owner's credentials; logs in ONCE.

const APP = process.env.SCALE_APP;
const EMAIL = process.env.SCALE_EMAIL ?? "scale-owner@example.com";
const PASSWORD = process.env.SCALE_PASSWORD ?? "Scale-Owner-Pass-2026!";

type Result = { screen: string; requests: number; kilobytes: number; settled_ms: number; largest_kb: number };
const results: Result[] = [];

async function measure(page: Page, screen: string, action: () => Promise<void>, ready: () => Promise<void>) {
  const sizes: number[] = [];
  const onResponse = async (response: import("@playwright/test").Response) => {
    if (!response.url().includes("/api/v1/")) return;
    try {
      sizes.push((await response.body()).length);
    } catch {
      sizes.push(0);
    }
  };
  page.on("response", onResponse);
  const started = Date.now();
  await action();
  await ready();
  await page.waitForLoadState("networkidle");
  const settled = Date.now() - started;
  page.off("response", onResponse);
  const total = sizes.reduce((a, b) => a + b, 0);
  results.push({
    screen,
    requests: sizes.length,
    kilobytes: Math.round(total / 102.4) / 10,
    settled_ms: settled,
    largest_kb: Math.round(Math.max(0, ...sizes) / 102.4) / 10,
  });
}

test("screens stay light with 5,000 products, 10,000 part numbers and 10,000 movements", async ({ page }) => {
  test.skip(!APP, "set SCALE_APP to the generated instance id");
  test.setTimeout(240_000);
  page.setDefaultTimeout(20_000); // a locator mistake should fail in seconds, not at the test timeout
  await login(page, EMAIL, PASSWORD);
  const base = `/apps/${APP}`;

  await measure(page, "home (six counts)", () => page.goto(base).then(() => undefined),
    () => expect(page.getByRole("heading", { name: "At a glance" })).toBeVisible());
  await measure(page, "products, first page", () => page.goto(`${base}/products`).then(() => undefined),
    () => expect(page.getByRole("table").getByRole("link").first()).toBeVisible());
  await measure(page, "products, search 'Brake Pad Set 0001'", async () => {
    const search = page.getByRole("search", { name: "Search products" }).getByRole("searchbox");
    await search.fill("Brake Pad Set 0001");
    await search.press("Enter");
  }, () => expect(page.getByRole("link", { name: /Brake Pad Set 0001/ }).first()).toBeVisible());
  await measure(page, "part-number search (normalized)", () => page.goto(`${base}/part-numbers?q=am04284oil`).then(() => undefined),
    () => expect(page.getByRole("cell", { name: /AM 04284 OIL/ })).toBeVisible());
  await measure(page, "stock page", () => page.goto(`${base}/inventory`).then(() => undefined),
    () => expect(page.getByRole("region", { name: "Stock", exact: true })).toBeVisible());
  await measure(page, "sales list", () => page.goto(`${base}/sales`).then(() => undefined),
    () => expect(page.getByRole("heading", { name: "Sales", exact: true })).toBeVisible());
  await measure(page, "new sale (customer list of 500 loads)", () => page.goto(`${base}/sales/new`).then(() => undefined),
    () => expect(page.getByLabel("Customer", { exact: true })).toBeVisible());
  await measure(page, "receive stock (50 suppliers load)", () => page.goto(`${base}/receive`).then(() => undefined),
    () => expect(page.getByLabel("Supplier")).toBeVisible());
  await measure(page, "product picker search on the sale page", async () => {
    await page.goto(`${base}/sales/new`);
    await page.getByRole("combobox", { name: "Product (item 1)", exact: true }).fill("04284");
  }, () => expect(page.getByRole("listbox", { name: /matches/ }).getByRole("option").first()).toBeVisible());

  console.log("SCALE-BROWSER " + JSON.stringify(results));
  for (const r of results) {
    expect(r.requests, `${r.screen}: request count`).toBeLessThan(40);
    expect(r.largest_kb, `${r.screen}: largest single response`).toBeLessThan(600);
  }
});
