import { test, expect } from "@playwright/test";
import { createOrganization, register, uniqueEmail } from "./helpers";

// Directive workflow: "Verify Organization A cannot access Organization B
// resources" -- driven through the real UI/API, not asserted from the
// backend test suite alone. get_member_workspace (workspaces/views.py)
// resolves a Workspace only within the requester's own org's membership,
// 404ing otherwise; this proves that holds end to end, including that the
// frontend surfaces it as a real error state (ErrorBanner, role="alert"),
// not a blank page or a silent redirect.
test("a user from Organization B cannot reach Organization A's workspace by ID substitution", async ({
  browser,
}) => {
  const contextA = await browser.newContext();
  const contextB = await browser.newContext();
  const pageA = await contextA.newPage();
  const pageB = await contextB.newPage();

  await register(pageA, uniqueEmail("e2e-tenant-a"));
  const orgAId = await createOrganization(pageA, "Org A E2E");
  await pageA.getByRole("button", { name: "New workspace" }).first().click();
  await pageA.getByLabel("Name").fill("Org A Private Workspace");
  await pageA.getByRole("dialog").getByRole("button", { name: "Create" }).click();
  await expect(pageA.getByRole("dialog")).not.toBeVisible();
  const workspaceLink = pageA.getByRole("link", { name: /Org A Private Workspace/ });
  await workspaceLink.click();
  await expect(pageA).toHaveURL(/\/workspaces\/[0-9a-f-]{36}$/);
  const workspaceId = new URL(pageA.url()).pathname.split("/workspaces/")[1];
  expect(workspaceId).toMatch(/^[0-9a-f-]{36}$/);

  await register(pageB, uniqueEmail("e2e-tenant-b"));
  await createOrganization(pageB, "Org B E2E");

  await pageB.goto(`/orgs/${orgAId}/workspaces/${workspaceId}`);
  await expect(pageB.getByRole("alert")).toBeVisible();
  await expect(pageB.getByText("Org A Private Workspace")).not.toBeVisible();

  await contextA.close();
  await contextB.close();
});
