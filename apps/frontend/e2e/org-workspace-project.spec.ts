import { test, expect } from "@playwright/test";
import { createOrganization, register, uniqueEmail } from "./helpers";

test("create organization, workspace, and project end to end", async ({ page }) => {
  await register(page, uniqueEmail("e2e-owp"));

  const orgId = await createOrganization(page, "Acme Corp E2E");
  await expect(page).toHaveURL(new RegExp(`/orgs/${orgId}$`));

  await page.getByRole("button", { name: "New workspace" }).first().click();
  await page.getByLabel("Name").fill("Engineering");
  await page.getByRole("dialog").getByRole("button", { name: "Create" }).click();
  await expect(page.getByRole("dialog")).not.toBeVisible();

  const workspaceLink = page.getByRole("link", { name: /Engineering/ });
  await expect(workspaceLink).toBeVisible();
  await workspaceLink.click();
  await expect(page).toHaveURL(new RegExp(`/orgs/${orgId}/workspaces/[0-9a-f-]{36}$`));

  await page.getByRole("button", { name: "New project" }).first().click();
  await page.getByLabel("Name").fill("Demo Project");
  await page.getByRole("dialog").getByRole("button", { name: "Create" }).click();
  await expect(page.getByRole("dialog")).not.toBeVisible();

  const projectLink = page.getByRole("link", { name: /Demo Project/ });
  await expect(projectLink).toBeVisible();
  await projectLink.click();
  await expect(page).toHaveURL(/\/projects\/[0-9a-f-]{36}$/);
});
