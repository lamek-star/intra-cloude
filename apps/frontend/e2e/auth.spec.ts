import { test, expect } from "@playwright/test";
import { login, register, uniqueEmail } from "./helpers";

test("register, land on /orgs, log out, and log back in", async ({ page }) => {
  const email = uniqueEmail("e2e-auth");
  await register(page, email);

  await expect(page.getByRole("heading", { name: "Organizations" })).toBeVisible();

  // Desktop sidebar (visible at the default >=640px test viewport) has a
  // plain "Log out" button; the mobile account-menu flow is covered
  // separately at a narrow viewport below.
  await page.getByRole("button", { name: "Log out" }).click();
  await expect(page).toHaveURL(/\/login$/);

  await login(page, email);
  await expect(page.getByRole("heading", { name: "Organizations" })).toBeVisible();
});

test("mobile account menu exposes logout behind an accessible, labeled control", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  const email = uniqueEmail("e2e-auth-mobile");
  await register(page, email);

  await page.getByRole("button", { name: "Account menu" }).click();
  await page.getByRole("menuitem", { name: "Log out" }).click();
  await expect(page).toHaveURL(/\/login$/);
});

test("wrong password is rejected with a real error, not a silent redirect", async ({ page }) => {
  const email = uniqueEmail("e2e-auth-bad");
  await register(page, email);
  await page.getByRole("button", { name: "Log out" }).click();

  await page.goto("/login");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill("definitely-the-wrong-password");
  await page.getByRole("button", { name: "Sign in" }).click();

  await expect(page).toHaveURL(/\/login$/);
  await expect(page.getByRole("alert")).toBeVisible();
});
