import { test, expect } from "@playwright/test";
import { login, register, uniqueEmail } from "./helpers";

test("register, land on /welcome, log out, and log back in with no forced organization redirect", async ({
  page,
}) => {
  const email = uniqueEmail("e2e-auth");
  await register(page, email);

  await expect(page.getByRole("heading", { name: "Welcome to IntraForge" })).toBeVisible();
  await page.getByRole("button", { name: "Continue" }).click();
  await expect(page).toHaveURL(/\/dashboard$/);

  // Desktop sidebar (visible at the default >=640px test viewport) has a
  // plain "Log out" button; the mobile account-menu flow is covered
  // separately at a narrow viewport below.
  await page.getByRole("button", { name: "Log out" }).click();
  await expect(page).toHaveURL(/\/login$/);

  await login(page, email);
  // Logging back in must land on the dashboard directly -- never back on
  // /welcome (a one-time step, not shown again) and never forced onto
  // /orgs just because this account has none.
  await expect(page).toHaveURL(/\/dashboard$/);
  await expect(page.getByRole("heading", { name: /^Welcome/ })).toBeVisible();
});

test("mobile account menu exposes logout behind an accessible, labeled control", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  const email = uniqueEmail("e2e-auth-mobile");
  await register(page, email);
  await page.getByRole("button", { name: "Continue" }).click();
  await expect(page).toHaveURL(/\/dashboard$/);

  await page.getByRole("button", { name: "Account menu" }).click();
  await page.getByRole("menuitem", { name: "Log out" }).click();
  await expect(page).toHaveURL(/\/login$/);
});

test("wrong password is rejected with a real error, not a silent redirect", async ({ page }) => {
  const email = uniqueEmail("e2e-auth-bad");
  await register(page, email);
  await page.getByRole("button", { name: "Continue" }).click();
  await page.getByRole("button", { name: "Log out" }).click();

  await page.goto("/login");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill("definitely-the-wrong-password");
  await page.getByRole("button", { name: "Sign in" }).click();

  await expect(page).toHaveURL(/\/login$/);
  await expect(page.getByRole("alert")).toBeVisible();
});

test("a user can skip organization creation entirely, use the account, and create an organization later", async ({
  page,
}) => {
  const email = uniqueEmail("e2e-org-less");
  await register(page, email);

  // Skip organization creation at onboarding.
  await page.getByRole("button", { name: "Continue" }).click();
  await expect(page).toHaveURL(/\/dashboard$/);
  await expect(page.getByText("Organizations").first()).toBeVisible();

  // The account is fully usable without an organization: the
  // Organizations page loads to a real empty state, not an error, and
  // offers an explicit way back to the dashboard instead of trapping the
  // user into creating one.
  await page.goto("/orgs");
  await expect(page.getByText("No organizations yet")).toBeVisible();
  await expect(page.getByRole("link", { name: /take me to my dashboard/ })).toBeVisible();

  // Sign out and back in -- still no forced organization redirect.
  await page.goto("/dashboard");
  await page.getByRole("button", { name: "Log out" }).click();
  await login(page, email);
  await expect(page).toHaveURL(/\/dashboard$/);

  // Create an organization later, from the same account -- organization
  // features become available immediately once created.
  await page.goto("/orgs");
  await page.getByRole("button", { name: "New organization" }).first().click();
  await page.getByLabel("Name").fill("Created Later Inc");
  await page.getByRole("dialog").getByRole("button", { name: "Create" }).click();
  await expect(page).toHaveURL(/\/orgs\/[0-9a-f-]{36}$/);
});
