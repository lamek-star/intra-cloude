import { test, expect } from "@playwright/test";
import { mkdirSync, writeFileSync } from "node:fs";
import { dirname } from "node:path";
import { call, grantCashier, registerCashier } from "./cashier-setup";
import { buildFlagshipBusiness, DEMO_PASSWORD } from "./flagship-setup";

// Builds the UI-made flagship business for the template-upgrade and destructive-restore gates and records
// what those gates need to find it again. Not a test of behaviour -- a fixture: everything is created
// through the customer UI exactly as in the flagship journey (supplier, warehouse, product, part number,
// receive 100, customer, sell 5 -> 95, a stored document), plus a restricted cashier with the documented
// grants. The state file path comes from UI_STATE_FILE.
//
// Registers two accounts (owner + cashier); the auth endpoints are rate limited to 10/minute on purpose.
// DEMO_OWNER_EMAIL / DEMO_CASHIER_EMAIL give the accounts readable logins (the offline investor-demo kit);
// without them the emails are unique and random.

const STATE_FILE = process.env.UI_STATE_FILE;

test("prepare the UI-built flagship business (owner, cashier, 95 on hand, a stored document)", async ({ browser }) => {
  test.skip(!STATE_FILE, "set UI_STATE_FILE to record the prepared business");
  test.setTimeout(300_000);

  const cashier = await registerCashier(browser, "prep-cashier", process.env.DEMO_CASHIER_EMAIL);
  const ownerContext = await browser.newContext();
  const owner = await ownerContext.newPage();
  const biz = await buildFlagshipBusiness(owner, {
    prefix: "prep-owner",
    withFile: true,
    email: process.env.DEMO_OWNER_EMAIL,
  });
  const access = await grantCashier(owner, biz, cashier.email);

  // The state the later gates must find, restored or upgraded, exactly.
  const inventory = (await call(owner, "GET", `/app-models/${access.models.inventory.id}/records/?limit=5`)).json as {
    count: number;
    results: Record<string, unknown>[];
  };
  expect(inventory.count).toBe(1);
  const onHandField = access.models.inventory.fields.find((f) => f.key === "quantity_on_hand")!.id;
  expect(Number(inventory.results[0][onHandField])).toBe(95);

  mkdirSync(dirname(STATE_FILE!), { recursive: true });
  writeFileSync(
    STATE_FILE!,
    JSON.stringify(
      {
        owner: { email: biz.email, password: DEMO_PASSWORD },
        cashier: { email: cashier.email, password: DEMO_PASSWORD, userId: access.userId },
        orgId: biz.orgId,
        orgName: biz.orgName,
        instanceId: biz.instanceId,
        appHome: biz.appHome,
        productUrl: biz.productUrl,
        invoiceNumber: biz.invoiceNumber,
        salesDocumentUrl: biz.salesDocumentUrl,
        shareCount: Object.keys(access.shareIds).length,
        onHand: 95,
      },
      null,
      2,
    ),
  );
  await cashier.context.close();
  await ownerContext.close();
});
