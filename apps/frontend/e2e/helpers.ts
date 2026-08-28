import { Page, expect } from "@playwright/test";

/** A fresh, collision-free email per test run/worker. */
export function uniqueEmail(prefix: string): string {
  return `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}@example.com`;
}

export async function register(page: Page, email: string, password = "correct-horse-battery-9") {
  await page.goto("/register");
  await page.getByLabel("First name").fill("Test");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill(password);
  await page.getByRole("button", { name: "Create account" }).click();
  await expect(page).toHaveURL(/\/orgs$/);
}

export async function login(page: Page, email: string, password = "correct-horse-battery-9") {
  await page.goto("/login");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill(password);
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page).toHaveURL(/\/orgs$/);
}

export async function createOrganization(page: Page, name: string): Promise<string> {
  await page.goto("/orgs");
  // The empty state's own "New organization" button duplicates the
  // PageHeader action when the list is empty (the common case here,
  // since every E2E user is freshly registered) -- take the first.
  await page.getByRole("button", { name: "New organization" }).first().click();
  await page.getByLabel("Name").fill(name);
  await page.getByRole("dialog").getByRole("button", { name: "Create" }).click();
  // CreateOrgModal's onCreated navigates straight to the new org's detail
  // page via next/navigation's router.push -- a client-side (pushState)
  // transition, not a full page load, so page.waitForURL()'s default
  // waitUntil:"load" never resolves. expect(...).toHaveURL() polls the
  // URL directly instead and is the reliable way to wait for this.
  await expect(page).toHaveURL(/\/orgs\/[0-9a-f-]{36}$/);
  const orgId = new URL(page.url()).pathname.split("/orgs/")[1];
  return orgId;
}
