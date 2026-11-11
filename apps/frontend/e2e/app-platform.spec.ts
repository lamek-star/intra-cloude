import AxeBuilder from "@axe-core/playwright";
import { test, expect } from "@playwright/test";
import { createOrganization, register, uniqueEmail } from "./helpers";

test("offline App Builder: publish, install, provision, create, search and retain a record", async ({ page }) => {
  test.setTimeout(90_000);
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
  await register(page, uniqueEmail("local-builder"));
  const orgId = await createOrganization(page, "Local Workflow — DEMO");
  await page.getByRole("button", { name: "New workspace" }).first().click();
  await page.getByLabel("Name", { exact: true }).fill("Company");
  await page.getByRole("dialog").getByRole("button", { name: "Create", exact: true }).click();
  await page.getByRole("link", { name: /Company/ }).click();
  await page.getByRole("button", { name: "New project" }).first().click();
  await page.getByLabel("Name", { exact: true }).fill("Business");
  await page.getByRole("dialog").getByRole("button", { name: "Create", exact: true }).click();
  await page.getByRole("link", { name: /Business/ }).click();
  await expect(page).toHaveURL(/\/projects\/[0-9a-f-]+$/);
  const projectUrl = page.url();

  await page.goto(`/orgs/${orgId}/app-templates`);
  await page.getByRole("button", { name: "New template" }).first().click();
  await page.getByLabel("Name", { exact: true }).fill("Products DEMO");
  await page.getByRole("dialog").getByRole("button", { name: "Create", exact: true }).click();
  await page.getByRole("link", { name: /Products DEMO/ }).click();
  await page.getByLabel("New model name").fill("Product");
  await page.getByRole("button", { name: "Add model", exact: true }).click();
  await page.getByLabel("New field name").fill("Name");
  await page.getByRole("button", { name: "Add field", exact: true }).click();
  const published = page.waitForResponse((response) =>
    response.url().endsWith("/versions/") && response.request().method() === "POST",
  );
  await page.getByRole("button", { name: "Publish version" }).click();
  expect((await published).ok()).toBeTruthy();

  await page.goto(projectUrl);
  await page.getByRole("button", { name: "Install app" }).first().click();
  await page.getByLabel("Template", { exact: true }).selectOption({ label: "Products DEMO" });
  await page.getByLabel("Name this installed app").fill("Products DEMO");
  await page.getByRole("dialog").getByRole("button", { name: "Install", exact: true }).click();
  await page.getByRole("link", { name: /Products DEMO/ }).click();
  await page.getByRole("button", { name: "Provision runtime" }).click();
  await expect(page.getByText("Ready", { exact: true })).toBeVisible({ timeout: 30_000 });
  await page.getByRole("link", { name: /Product/ }).filter({ hasNotText: "Products DEMO" }).last().click();
  await expect(page).toHaveURL(/\/app-models\/[0-9a-f-]+$/);
  await page.getByRole("button", { name: "Add record" }).first().click();
  await page.getByLabel("Name", { exact: true }).fill("Demo Oil Filter");
  await page.getByRole("dialog").getByRole("button", { name: "Add record", exact: true }).click();
  await expect(page.getByText("Demo Oil Filter", { exact: true })).toBeVisible();
  await page.reload();
  await expect(page.getByText("Demo Oil Filter", { exact: true })).toBeVisible();
  const search = page.getByPlaceholder(/Search/);
  await search.fill("missing-demo-product");
  await search.press("Enter");
  await expect(page.getByText("Demo Oil Filter", { exact: true })).not.toBeVisible();
  await search.fill("Oil Filter");
  await search.press("Enter");
  await expect(page.getByText("Demo Oil Filter", { exact: true })).toBeVisible();
  expect(externalRequests).toEqual([]);
});

test("sign-in form has no serious or critical automated accessibility violations", async ({ page }, testInfo) => {
  await page.goto("/login");
  await expect(page.getByRole("button", { name: "Sign in", exact: true })).toBeVisible();
  const results = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa"]).analyze();
  await testInfo.attach("accessibility", { body: JSON.stringify(results.violations), contentType: "application/json" });
  expect(results.violations.filter((v) => ["serious", "critical"].includes(v.impact ?? ""))).toEqual([]);
});
