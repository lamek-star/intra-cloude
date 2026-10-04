import { test, expect, type BrowserContext, type Page } from "@playwright/test";
import {
  call,
  grantCashier,
  grantReceiver,
  READ_MODELS,
  registerCashier,
  type Json,
  type Model,
  type Relationship,
} from "./cashier-setup";
import { buildFlagshipBusiness, nav, type FlagshipBusiness } from "./flagship-setup";

// Restricted users under BUSINESS-OPERATION AUTHORITY (ADR-0017): a real cashier and a real receiver, each a second
// user added through the UI and given ONLY the sharing grants listed in cashier-setup.ts (no role at all), then
// exercised through the browser and through direct API calls. Everything they must not do is refused by the SERVER.
//
//   the right to SELL is not the right to RECEIVE, ADJUST or make arbitrary stock movements -- and the reverse.
//
// The cashier holds no write access to the stock tables at all: selling is the server's controlled operation,
// authorized by `inventory.sell`, not a stock movement assembled by the caller.

const NOT_GRANTED = ["supplier", "purchase_order", "purchase_order_line", "vehicle"];

let biz: FlagshipBusiness;
let owner: Page;
let cashierContext: BrowserContext;
let cashier: Page;
let cashierEmail: string;
let receiverEmail: string;
let cashierId: string;
let receiverContext: BrowserContext;
let receiver: Page;
let receiverAccess: Awaited<ReturnType<typeof grantReceiver>>;
let models: Record<string, Model>;
let relationships: Relationship[];
let shareIds: Record<string, string>;
let partId: string;
let warehouseId: string;

const fieldId = (model: string, key: string) => {
  const found = models[model].fields.find((f) => f.key === key);
  if (found) return found.id;
  // Links to other records (a movement's part or warehouse) are relationships the model owns.
  const link = relationships.find((r) => r.key === key && r.source_model === models[model].id);
  if (!link) throw new Error(`no field or relationship ${model}.${key}`);
  return link.id;
};
const recordsPath = (model: string, id = "") => `/app-models/${models[model].id}/records/${id ? `${id}/` : ""}`;

async function onHand(page: Page): Promise<number> {
  const rows = (await call(page, "GET", recordsPath("inventory") + "?limit=50")).json?.results as Json[];
  return Number(rows[0][fieldId("inventory", "quantity_on_hand")]);
}

test.describe("Restricted cashier", () => {
  test.beforeAll(async ({ browser }) => {
    test.setTimeout(300_000);
    // The cashier must exist before the owner can add them by email.
    const registered = await registerCashier(browser);
    cashierContext = registered.context;
    cashier = registered.page;
    cashierEmail = registered.email;

    const ownerContext = await browser.newContext();
    owner = await ownerContext.newPage();
    biz = await buildFlagshipBusiness(owner, { prefix: "cashier-owner", withFile: true });

    const receiverRegistered = await registerCashier(browser, "receiver");
    receiverContext = receiverRegistered.context;
    receiver = receiverRegistered.page;
    receiverEmail = receiverRegistered.email;

    const access = await grantCashier(owner, biz, cashierEmail);
    cashierId = access.userId;
    models = access.models;
    relationships = access.relationships;
    shareIds = access.shareIds;
    receiverAccess = await grantReceiver(owner, biz, receiverEmail);

    const parts = (await call(owner, "GET", recordsPath("part") + "?limit=5")).json?.results as Json[];
    partId = String(parts[0].id);
    const warehouses = (await call(owner, "GET", recordsPath("warehouse") + "?limit=5")).json?.results as Json[];
    warehouseId = String(warehouses[0].id);
  });

  test.afterAll(async () => {
    await cashierContext?.close();
    await receiverContext?.close();
    await owner?.context().close();
  });

  test("the cashier can find a product, see stock and sell it through the normal screens", async () => {
    await cashier.goto(biz.appHome);
    await expect(nav(cashier)).toBeVisible();
    await cashier.goto(`${biz.appHome}/sales/new`);
    await cashier.getByLabel("Customer", { exact: true }).selectOption({ label: "Demo Retail Customer" });
    await cashier.getByRole("combobox", { name: "Product (item 1)", exact: true }).fill("04465-0K290");
    await cashier.getByRole("option", { name: /Demo Oil Filter/ }).click();
    await cashier.getByLabel("Warehouse").selectOption({ label: "Main Warehouse" });
    await cashier.getByLabel("Quantity").fill("2");
    await cashier.getByRole("button", { name: "Confirm sale" }).click();
    await expect(cashier.getByTestId("on-hand-after-sale")).toHaveText("93");
    await cashier.getByRole("link", { name: "Open sales document" }).click();
    await expect(cashier.getByRole("heading", { name: /Invoice INV-/ })).toBeVisible();
    expect(await onHand(owner)).toBe(93); // the owner reads the same server-side balance
  });

  test("directly opening a screen the cashier has no grant for shows a permission message and no data", async () => {
    await cashier.goto(`${biz.appHome}/suppliers`);
    await expect(cashier.getByText(/permission/i).first()).toBeVisible({ timeout: 15_000 });
    await expect(cashier.getByText("Demo Supplier A")).toHaveCount(0);
    await expect(cashier.locator("body")).not.toContainText("Demo Supplier A");
  });

  test("the home page still works for the cashier and shows nothing they cannot read", async () => {
    await cashier.goto(biz.appHome);
    await expect(cashier.getByRole("heading", { name: "At a glance" })).toBeVisible();
    const glance = cashier.getByRole("list").filter({ has: cashier.getByRole("link", { name: /^Suppliers/ }) });
    // A count the cashier may read is shown even though another model (Suppliers) is refused to them...
    await expect(glance.getByRole("link", { name: /^Products\s+\d+/ })).toBeVisible();
    await expect(glance.getByRole("link", { name: /^Customers\s+\d+/ })).toBeVisible();
    // ...and the refused one says so instead of showing a number or blanking the whole row.
    await expect(glance.getByRole("link", { name: /^Suppliers\s+—/ })).toBeVisible();
    await expect(cashier.locator("body")).not.toContainText("Demo Supplier A");
  });

  test("adding a product in the UI is refused by the server and creates nothing", async () => {
    const before = (await call(owner, "GET", recordsPath("part") + "?limit=1")).json?.count;
    await cashier.goto(`${biz.appHome}/products`);
    await cashier.getByRole("button", { name: "Add product" }).first().click();
    const dialog = cashier.getByRole("dialog");
    await dialog.getByLabel("Name").fill("Cashier Should Not Create This");
    await dialog.getByRole("button", { name: "Add", exact: true }).click();
    await expect(dialog.getByRole("alert")).toContainText(/permission/i);
    const after = (await call(owner, "GET", recordsPath("part") + "?limit=1")).json?.count;
    expect(after).toBe(before);
  });

  test("direct API: every ungranted model refuses reads and leaks nothing", async () => {
    for (const key of NOT_GRANTED) {
      const list = await call(cashier, "GET", recordsPath(key) + "?limit=5");
      expect(list.status, `${key} list`).toBe(403);
      expect(list.text).not.toContain("Demo Supplier A");
      expect(list.json ?? {}, `${key}: a refusal carries no count`).not.toHaveProperty("count");
      expect(list.json ?? {}, `${key}: a refusal carries no results`).not.toHaveProperty("results");
    }
    // A supplier record fetched by its real id is refused too (ID substitution inside the org).
    const suppliers = (await call(owner, "GET", recordsPath("supplier") + "?limit=1")).json?.results as Json[];
    const one = await call(cashier, "GET", recordsPath("supplier", String(suppliers[0].id)));
    expect(one.status).toBe(403);
    expect(one.text).not.toContain("Demo Supplier A");
  });

  test("direct API: read-only models cannot be created, changed or deleted", async () => {
    for (const key of READ_MODELS) {
      const list = await call(cashier, "GET", recordsPath(key) + "?limit=1");
      expect(list.status, `${key} read`).toBe(200);
    }
    const nameField = fieldId("part", "name");
    const create = await call(cashier, "POST", recordsPath("part"), { [nameField]: "Injected" });
    expect(create.status).toBe(403);
    const patch = await call(cashier, "PATCH", recordsPath("part", partId), { [nameField]: "Renamed" });
    expect(patch.status).toBe(403);
    const del = await call(cashier, "DELETE", recordsPath("part", partId));
    expect(del.status).toBe(403);
    const after = await call(owner, "GET", recordsPath("part", partId));
    expect(after.json?.[nameField]).toBe("Demo Oil Filter");
    const customerCreate = await call(cashier, "POST", recordsPath("customer"), {
      [fieldId("customer", "name")]: "Injected Customer",
    });
    expect(customerCreate.status).toBe(403);
  });

  test("direct API: no schema, sharing, membership, audit or backup authority", async () => {
    const addModel = await call(cashier, "POST", `/app-instances/${biz.instanceId}/models/`, {
      key: "evil",
      label: "Evil",
    });
    expect([401, 403]).toContain(addModel.status);
    const share = await call(cashier, "POST", `/organizations/${biz.orgId}/shares/`, {
      resource_type: "app_model",
      resource_id: models.supplier.id,
      principal_type: "user",
      user_id: "00000000-0000-0000-0000-000000000000",
      level: "read",
    });
    expect([400, 403, 404]).toContain(share.status);
    const revokeOwn = await call(cashier, "DELETE", `/shares/${shareIds["stock_movement:write"]}/`);
    expect([403, 404]).toContain(revokeOwn.status);
    const addMember = await call(cashier, "POST", `/organizations/${biz.orgId}/members/`, { email: cashierEmail });
    expect(addMember.status).toBe(403);
    const audit = await call(cashier, "GET", `/organizations/${biz.orgId}/audit/`);
    expect(audit.status).toBe(403);
    const upgrade = await call(cashier, "POST", `/app-instances/${biz.instanceId}/archive/`, {});
    expect([403, 404, 405]).toContain(upgrade.status);
  });

  test("direct API: the ledger cannot be tampered with even where the cashier has write access", async () => {
    const movements = (await call(owner, "GET", recordsPath("stock_movement") + "?limit=10")).json?.results as Json[];
    const movementId = String(movements[0].id);
    const before = await onHand(owner);

    const editMovement = await call(cashier, "PATCH", recordsPath("stock_movement", movementId), {
      [fieldId("stock_movement", "quantity_delta")]: 1000,
    });
    expect(editMovement.status, editMovement.text).toBeGreaterThanOrEqual(400);
    const deleteMovement = await call(cashier, "DELETE", recordsPath("stock_movement", movementId));
    expect(deleteMovement.status, deleteMovement.text).toBeGreaterThanOrEqual(400);

    const inventory = (await call(owner, "GET", recordsPath("inventory") + "?limit=1")).json?.results as Json[];
    const inflate = await call(cashier, "PATCH", recordsPath("inventory", String(inventory[0].id)), {
      [fieldId("inventory", "quantity_on_hand")]: 9999,
    });
    expect(inflate.status, inflate.text).toBeGreaterThanOrEqual(400);
    expect(await onHand(owner)).toBe(before);
  });

  test("direct API: a cashier cannot forge a stock balance by writing the inventory row directly", async () => {
    const second = await call(owner, "POST", recordsPath("warehouse"), {
      [fieldId("warehouse", "name")]: "Second Warehouse",
      [fieldId("warehouse", "code")]: "SEC",
    });
    expect(second.status, second.text).toBe(201);
    const before = (await call(owner, "GET", recordsPath("inventory") + "?limit=1")).json?.count;
    const forged = await call(cashier, "POST", recordsPath("inventory"), {
      [fieldId("inventory", "quantity_on_hand")]: 500,
      [fieldId("inventory", "part")]: partId,
      [fieldId("inventory", "warehouse")]: String(second.json?.id),
    });
    expect(forged.status, forged.text).toBeGreaterThanOrEqual(400); // the database's ledger guard refuses it
    expect((await call(owner, "GET", recordsPath("inventory") + "?limit=1")).json?.count).toBe(before);
  });

  test("files: the cashier gets no filenames, no bytes and cannot attach, even though they may read the product", async () => {
    const parts = (await call(owner, "GET", recordsPath("part") + "?limit=1")).json?.results as Json[];
    const ownerView = JSON.parse((await call(owner, "GET", `${recordsPath("part", partId)}attachments/`)).text) as {
      id: string;
      filename: string;
    }[];
    expect(ownerView.map((f) => f.filename)).toContain("oil-filter-datasheet-demo.txt"); // it really exists
    void parts;

    const list = await call(cashier, "GET", `${recordsPath("part", partId)}attachments/`);
    expect(list.text).not.toContain("oil-filter-datasheet-demo");
    expect(list.text).not.toContain("datasheet");
    const download = await call(cashier, "GET", `${recordsPath("part", partId)}attachments/${ownerView[0].id}/download/`);
    expect(download.status).toBeGreaterThanOrEqual(403);
    expect(download.text).not.toContain("DEMO data sheet");
    const attach = await call(cashier, "POST", `${recordsPath("part", partId)}attachments/`, {
      file_id: "00000000-0000-0000-0000-000000000000",
    });
    expect([400, 403, 404]).toContain(attach.status);

    // In the browser the Files tab shows no file name to the cashier either.
    await cashier.goto(`${biz.productUrl}`);
    await cashier.getByRole("tab", { name: "Files" }).click();
    await expect(cashier.locator("body")).not.toContainText("oil-filter-datasheet-demo");
  });

  test("direct API: no application administration, template installation, organization or permission management", async () => {
    const projectId = new URL(biz.projectUrl).pathname.split("/projects/")[1];
    const install = await call(cashier, "POST", `/projects/${projectId}/built-in-apps/spare_parts/install/`, {});
    expect(install.status).toBe(403);
    const apps = (await call(owner, "GET", `/projects/${projectId}/app-instances/?limit=50`)).json;
    expect(apps?.count, "no second application appeared").toBe(1);

    const workspace = await call(cashier, "POST", `/organizations/${biz.orgId}/workspaces/`, { name: "Cashier WS" });
    expect(workspace.status).toBe(403);
    const project = await call(cashier, "POST", `/workspaces/${biz.workspaceId}/projects/`, { name: "Cashier P" });
    expect(project.status).toBe(403);

    const members = JSON.parse((await call(cashier, "GET", `/organizations/${biz.orgId}/members/`)).text) as {
      id: string;
      user: { email: string };
    }[];
    const own = members.find((m) => m.user.email.toLowerCase() === cashierEmail.toLowerCase())!;
    const promote = await call(cashier, "POST", `/organizations/${biz.orgId}/members/${own.id}/role/`, {
      role_slug: "owner",
    });
    expect(promote.status).toBe(403);

    // Nothing above changed what the cashier can do: still refused on a model outside the grants.
    expect((await call(cashier, "GET", recordsPath("supplier") + "?limit=1")).status).toBe(403);
  });

  test("the cashier cannot receive stock, adjust it, or write a stock movement by any route", async () => {
    const before = await onHand(owner);
    const movements = (await call(owner, "GET", recordsPath("stock_movement") + "?limit=100")).json?.count;

    // 1. the controlled receive operation
    const receive = await call(cashier, "POST", `/app-instances/${biz.instanceId}/operations/receive/`, {
      part: partId, warehouse: warehouseId, quantity: 1, occurred_at: new Date().toISOString().slice(0, 19),
    });
    expect(receive.status, receive.text).toBe(403);
    // 2. a stock movement straight through the record API (a positive receive, a negative sale, an adjustment)
    for (const [delta, kind] of [[1, "receive"], [-1, "sale"], [5, "adjustment"]] as const) {
      const direct = await call(cashier, "POST", recordsPath("stock_movement"), {
        [fieldId("stock_movement", "stock_movement_part")]: partId,
        [fieldId("stock_movement", "stock_movement_warehouse")]: warehouseId,
        [fieldId("stock_movement", "quantity_delta")]: delta,
        [fieldId("stock_movement", "movement_type")]: kind,
        [fieldId("stock_movement", "occurred_at")]: "2026-09-19T10:00:00",
      });
      expect(direct.status, `${kind}: ${direct.text}`).toBe(403);
    }
    // 3. the generic atomic-transaction endpoint
    const generic = await call(cashier, "POST", `/app-instances/${biz.instanceId}/transactions/`, {
      operations: [
        {
          op: "create",
          model: models.stock_movement.id,
          data: {
            [fieldId("stock_movement", "stock_movement_part")]: partId,
            [fieldId("stock_movement", "stock_movement_warehouse")]: warehouseId,
            [fieldId("stock_movement", "quantity_delta")]: 1,
            [fieldId("stock_movement", "movement_type")]: "receive",
            [fieldId("stock_movement", "occurred_at")]: "2026-09-19T10:00:00",
          },
        },
      ],
    });
    expect(generic.status, generic.text).toBe(403);
    // 4. a request cannot name its own authority
    const forged = await call(cashier, "POST", recordsPath("stock_movement") + "?movement_operation=inventory.sell", {
      movement_operation: "inventory.sell",
    });
    expect(forged.status).toBe(403);

    expect(await onHand(owner)).toBe(before); // nothing moved
    expect((await call(owner, "GET", recordsPath("stock_movement") + "?limit=100")).json?.count).toBe(movements);

    // Every refusal is in the audit trail against the cashier, naming the authority that was missing.
    const audit = JSON.parse((await call(owner, "GET", `/organizations/${biz.orgId}/audit/?limit=100`)).text) as {
      results: { action: string; actor: string; result: string; context?: { required?: string } }[];
    };
    const byCashier = audit.results.filter((event) => event.actor === cashierId);
    expect(
      byCashier.some(
        (event) =>
          event.action === "inventory.receive" && event.result === "denied" && event.context?.required === "inventory.receive",
      ),
      "the refused receive is audited against the cashier",
    ).toBe(true);
    expect(byCashier.filter((event) => event.result === "denied").length).toBeGreaterThan(5);
  });

  test("the cashier's sale is audited, and a sale by the cashier is the only stock change they can make", async () => {
    const audit = JSON.parse((await call(owner, "GET", `/organizations/${biz.orgId}/audit/?limit=100`)).text) as {
      results: { action: string; actor: string; result: string }[];
    };
    expect(audit.results.some((e) => e.actor === cashierId && e.action === "inventory.sell" && e.result === "success")).toBe(true);
  });

  test("the receiver can receive through the UI but can neither sell nor write stock directly", async () => {
    const before = await onHand(owner);
    await receiver.goto(`${biz.appHome}/receive`);
    await receiver.getByRole("combobox", { name: "Product", exact: true }).fill("04465-0K290");
    await receiver.getByRole("option", { name: /Demo Oil Filter/ }).click();
    await receiver.getByLabel("Warehouse").selectOption({ label: "Main Warehouse" });
    await receiver.getByLabel("Quantity").fill("4");
    await receiver.getByRole("button", { name: "Confirm receive" }).click();
    await expect(receiver.getByTestId("on-hand-now")).toHaveText(String(before + 4));

    // ...but the same person may not sell: the operation, and the generic ways of writing a sale's stock, are refused.
    const orders = (await call(owner, "GET", recordsPath("sales_order") + "?limit=1")).json?.count;
    const sale = await call(receiver, "POST", `/app-instances/${biz.instanceId}/operations/sell/`, {
      customer: String(((await call(owner, "GET", recordsPath("customer") + "?limit=1")).json?.results as Json[])[0].id),
      invoice_number: "INV-RECEIVER-1",
      occurred_at: new Date().toISOString().slice(0, 19),
      lines: [{ part: partId, warehouse: warehouseId, quantity: 1, unit_price: "15.00" }],
    });
    expect(sale.status, sale.text).toBe(403);
    const direct = await call(receiver, "POST", recordsPath("stock_movement"), {
      [fieldId("stock_movement", "stock_movement_part")]: partId,
      [fieldId("stock_movement", "stock_movement_warehouse")]: warehouseId,
      [fieldId("stock_movement", "quantity_delta")]: -1,
      [fieldId("stock_movement", "movement_type")]: "sale",
      [fieldId("stock_movement", "occurred_at")]: "2026-09-19T10:00:00",
    });
    expect(direct.status).toBe(403);
    expect(await onHand(owner)).toBe(before + 4);
    expect((await call(owner, "GET", recordsPath("sales_order") + "?limit=1")).json?.count).toBe(orders);
    // and, like the cashier, no supplier-independent administration
    expect((await call(receiver, "POST", recordsPath("part"), { [fieldId("part", "name")]: "Injected" })).status).toBe(403);
  });

  test("the receiver is refused what the receiver role never had: customers' sales, files, administration", async () => {
    expect((await call(receiver, "GET", recordsPath("sales_order") + "?limit=1")).status).toBe(403);
    expect((await call(receiver, "GET", recordsPath("customer") + "?limit=1")).status).toBe(403);
    expect((await call(receiver, "GET", `${recordsPath("part", partId)}attachments/`)).text).not.toContain("datasheet");
    expect((await call(receiver, "GET", `/organizations/${biz.orgId}/audit/`)).status).toBe(403);
    expect(
      (await call(receiver, "POST", `/organizations/${biz.orgId}/shares/`, {
        resource_type: "inventory_operations", resource_id: biz.instanceId, principal_type: "user",
        user_id: receiverAccess.userId, level: "sell",
      })).status,
    ).toBe(403); // a receiver cannot promote themselves to a seller
  });

  test("a deliberately combined role can do both: granting the receiver SELL adds selling and nothing else", async () => {
    for (const key of ["sales_order", "sales_order_line", "invoice"]) {
      const res = await call(owner, "POST", `/organizations/${biz.orgId}/shares/`, {
        resource_type: "app_model", resource_id: models[key].id, principal_type: "user", user_id: receiverAccess.userId,
        level: "write",
      });
      expect(res.status, res.text).toBe(201);
    }
    const customerRead = await call(owner, "POST", `/organizations/${biz.orgId}/shares/`, {
      resource_type: "app_model", resource_id: models.customer.id, principal_type: "user", user_id: receiverAccess.userId,
      level: "read",
    });
    expect(customerRead.status, customerRead.text).toBe(201);
    const sellGrant = await call(owner, "POST", `/organizations/${biz.orgId}/shares/`, {
      resource_type: "inventory_operations", resource_id: biz.instanceId, principal_type: "user",
      user_id: receiverAccess.userId, level: "sell",
    });
    expect(sellGrant.status, sellGrant.text).toBe(201);

    const before = await onHand(owner);
    const customer = String(((await call(owner, "GET", recordsPath("customer") + "?limit=1")).json?.results as Json[])[0].id);
    const sale = await call(receiver, "POST", `/app-instances/${biz.instanceId}/operations/sell/`, {
      customer,
      invoice_number: "INV-COMBINED-1",
      occurred_at: new Date().toISOString().slice(0, 19),
      lines: [{ part: partId, warehouse: warehouseId, quantity: 1, unit_price: "15.00" }],
    }, { "Idempotency-Key": "combined-role-sale-1" });
    expect(sale.status, sale.text).toBe(201);
    expect(await onHand(owner)).toBe(before - 1);
    // ...and it still cannot administer: SELL added selling, not adjusting.
    const direct = await call(receiver, "POST", recordsPath("stock_movement"), {
      [fieldId("stock_movement", "stock_movement_part")]: partId,
      [fieldId("stock_movement", "stock_movement_warehouse")]: warehouseId,
      [fieldId("stock_movement", "quantity_delta")]: 9,
      [fieldId("stock_movement", "movement_type")]: "adjustment",
      [fieldId("stock_movement", "occurred_at")]: "2026-09-19T10:00:00",
    });
    expect(direct.status).toBe(403);
  });

  test("revoking SELL takes effect on the cashier's very next action (the model grants alone do not sell)", async () => {
    const before = await onHand(owner);
    const ordersBefore = (await call(owner, "GET", recordsPath("sales_order") + "?limit=1")).json?.count;
    const revoke = await call(owner, "DELETE", `/shares/${shareIds["inventory_operations:sell"]}/`);
    expect(revoke.status).toBe(204);

    await cashier.goto(`${biz.appHome}/sales/new`);
    await cashier.getByLabel("Customer", { exact: true }).selectOption({ label: "Demo Retail Customer" });
    await cashier.getByRole("combobox", { name: "Product (item 1)", exact: true }).fill("04465-0K290");
    await cashier.getByRole("option", { name: /Demo Oil Filter/ }).click();
    await cashier.getByLabel("Warehouse").selectOption({ label: "Main Warehouse" });
    await cashier.getByLabel("Quantity").fill("1");
    await cashier.getByRole("button", { name: "Confirm sale" }).click();
    await expect(cashier.getByText(/don't have permission/i)).toBeVisible();
    await expect(cashier.getByText(/Nothing was changed/i)).toBeVisible();
    expect(await onHand(owner)).toBe(before);
    // ...and no half-made sales document is left behind by the refused transaction.
    const ordersAfter = (await call(owner, "GET", recordsPath("sales_order") + "?limit=1")).json?.count;
    expect(ordersAfter).toBe(ordersBefore);
  });
});
