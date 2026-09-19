import { test, expect, type BrowserContext, type Page } from "@playwright/test";
import {
  call,
  grantCashier,
  READ_MODELS,
  registerCashier,
  type Json,
  type Model,
  type Relationship,
} from "./cashier-setup";
import { buildFlagshipBusiness, nav, type FlagshipBusiness } from "./flagship-setup";

// Restricted cashier: a real second user, added to the organization through the UI, given ONLY the
// grants below through the real sharing system, then exercised through the browser and through
// direct API calls. Everything the cashier must not do is refused by the SERVER; the UI is only ever
// a convenience. No role is assigned -- these grants are the cashier's whole authority.
//
//   app_instance  READ   the application itself (open it, read its schema -- labels, no data)
//   app_model     READ   part, part_number, warehouse, customer   (find a product, pick a customer/warehouse)
//   app_model     WRITE  sales_order, sales_order_line, invoice, stock_movement, inventory   (record a sale)
//
// NOT granted: supplier, purchase_order, purchase_order_line, vehicle (any access); write on part,
// part_number, warehouse, customer; any schema, sharing, membership, audit or backup right.

const NOT_GRANTED = ["supplier", "purchase_order", "purchase_order_line", "vehicle"];

let biz: FlagshipBusiness;
let owner: Page;
let cashierContext: BrowserContext;
let cashier: Page;
let cashierEmail: string;
let cashierId: string;
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

    const access = await grantCashier(owner, biz, cashierEmail);
    cashierId = access.userId;
    models = access.models;
    relationships = access.relationships;
    shareIds = access.shareIds;

    const parts = (await call(owner, "GET", recordsPath("part") + "?limit=5")).json?.results as Json[];
    partId = String(parts[0].id);
    const warehouses = (await call(owner, "GET", recordsPath("warehouse") + "?limit=5")).json?.results as Json[];
    warehouseId = String(warehouses[0].id);
  });

  test.afterAll(async () => {
    await cashierContext?.close();
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

  test("KNOWN LIMIT (pinned): grants are per model, so a cashier who may sell may also post stock movements", async () => {
    // ADR-0016: authority over a movement is authority over the movement model AND its balance model.
    // A sale and a receive both write those two models, so the server cannot tell "may sell" from
    // "may receive/adjust". This test PINS that behaviour so it can never change unnoticed: the day a
    // movement-type authority exists, this test must be inverted deliberately. See
    // docs/LOCAL_EDITION_APPLICATIONS.md ("Roles and the cashier limit").
    const before = await onHand(owner);
    const receive = await call(cashier, "POST", `/app-instances/${biz.instanceId}/transactions/`, {
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
    expect(receive.status, receive.text).toBe(201);
    expect(await onHand(owner)).toBe(before + 1);
    // The movement is still attributable: the audit trail names the cashier as the actor of the create...
    const audit = JSON.parse((await call(owner, "GET", `/organizations/${biz.orgId}/audit/?limit=100`)).text) as {
      results: { action: string; actor: string; result: string; resource_id: string }[];
    };
    const byCashier = audit.results.filter((event) => event.actor === cashierId);
    expect(
      byCashier.some(
        (event) =>
          event.action === "app_instance.record.create" &&
          event.result === "success" &&
          event.resource_id === models.stock_movement.id,
      ),
      "the receive is audited against the cashier",
    ).toBe(true);
    // ...and every attempt the server refused is in the same trail as a denied event.
    expect(byCashier.filter((event) => event.result === "denied").length).toBeGreaterThan(5);
  });

  test("revoking a grant takes effect on the cashier's very next action", async () => {
    const before = await onHand(owner);
    const ordersBefore = (await call(owner, "GET", recordsPath("sales_order") + "?limit=1")).json?.count;
    const revoke = await call(owner, "DELETE", `/shares/${shareIds["stock_movement:write"]}/`);
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
