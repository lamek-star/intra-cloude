import { expect, type APIResponse, type Browser, type BrowserContext, type Page } from "@playwright/test";
import { DEMO_PASSWORD, type FlagshipBusiness } from "./flagship-setup";
import { register, uniqueEmail } from "./helpers";

// Restricted users, set up exactly the way a customer would: a real second user, added to the organization
// through the "Add member" dialog, holding ONLY these sharing grants (no role at all). Shared by the
// restricted-user journeys and the recovery/upgrade drills so they all use the same, documented grants (see
// docs/LOCAL_EDITION_APPLICATIONS.md, "Roles and business-operation authority" and ADR-0017).
//
// CASHIER
//   app_instance          READ    open the application and read its structure
//   app_model             READ    part, part_number, warehouse, customer, inventory, stock_movement
//   app_model             WRITE   sales_order, sales_order_line, invoice
//   inventory_operations  SELL    record a sale (the server writes the stock movement; the cashier holds no
//                                 write access to the stock tables at all)
//
// RECEIVER
//   app_instance          READ
//   app_model             READ    part, part_number, warehouse, supplier, inventory, stock_movement
//   app_model             WRITE   purchase_order, purchase_order_line   (only needed when a supplier is recorded)
//   inventory_operations  RECEIVE receive stock

export const READ_MODELS = ["part", "part_number", "warehouse", "customer", "inventory", "stock_movement"];
export const WRITE_MODELS = ["sales_order", "sales_order_line", "invoice"];
export const RECEIVER_READ_MODELS = ["part", "part_number", "warehouse", "supplier", "inventory", "stock_movement"];
export const RECEIVER_WRITE_MODELS = ["purchase_order", "purchase_order_line"];

export type Json = Record<string, unknown>;
export type Field = { id: string; key: string };
export type Model = { id: string; key: string; fields: Field[] };
export type Relationship = { id: string; key: string; source_model: string };
export type Reply = { status: number; text: string; json: Json | null };

/** A session-cookie API call from a page's own login: primes and echoes the CSRF token, sends an Origin. */
export async function call(
  page: Page,
  method: string,
  path: string,
  data?: unknown,
  headers: Record<string, string> = {},
): Promise<Reply> {
  await page.request.get("/api/v1/auth/csrf/");
  const cookies = await page.context().cookies();
  const csrf = cookies.find((c) => c.name === "csrftoken")?.value ?? "";
  const origin = new URL(page.url() === "about:blank" ? "https://localhost:8444" : page.url()).origin;
  const res: APIResponse = await page.request.fetch(`/api/v1${path}`, {
    method,
    headers: { "X-CSRFToken": csrf, Origin: origin, Referer: `${origin}/`, ...headers },
    ...(data === undefined ? {} : { data }),
  });
  const text = await res.text();
  let json: Json | null = null;
  try {
    json = JSON.parse(text) as Json;
  } catch {
    json = null;
  }
  return { status: res.status(), text, json };
}

/** Registers the cashier's account (one auth call) in its own browser context. */
export async function registerCashier(browser: Browser, prefix = "cashier", fixedEmail?: string) {
  const context: BrowserContext = await browser.newContext();
  const page = await context.newPage();
  const email = fixedEmail ?? uniqueEmail(prefix);
  await register(page, email, DEMO_PASSWORD);
  return { context, page, email };
}

export type CashierAccess = {
  userId: string;
  models: Record<string, Model>;
  relationships: Relationship[];
  shareIds: Record<string, string>;
};

type Rights = { read: string[]; write: string[]; operations: ("sell" | "receive" | "adjust" | "transfer")[] };

/** The owner adds the person through the UI dialog, then grants exactly the listed rights. */
export async function grantMember(
  owner: Page,
  biz: FlagshipBusiness,
  email: string,
  rights: Rights,
): Promise<CashierAccess> {
  await owner.goto(`/orgs/${biz.orgId}`);
  await owner.getByRole("button", { name: "Add member" }).click();
  const dialog = owner.getByRole("dialog", { name: "Add member" });
  await dialog.getByLabel("Email of an existing user").fill(email);
  await dialog.getByRole("button", { name: "Add", exact: true }).click();
  await expect(dialog).toBeHidden();

  const schema = (await call(owner, "GET", `/app-instances/${biz.instanceId}/schema/`)).json as {
    models: Model[];
    relationships: Relationship[];
  };
  const models = Object.fromEntries(schema.models.map((m) => [m.key, m]));
  const members = JSON.parse((await call(owner, "GET", `/organizations/${biz.orgId}/members/`)).text) as {
    user: { id: string; email: string };
  }[];
  const member = members.find((m) => m.user.email.toLowerCase() === email.toLowerCase());
  expect(member, "the member appears in the member list").toBeTruthy();
  const userId = member!.user.id;

  const shareIds: Record<string, string> = {};
  const grant = async (type: string, resourceId: string, level: string, label: string) => {
    const res = await call(owner, "POST", `/organizations/${biz.orgId}/shares/`, {
      resource_type: type,
      resource_id: resourceId,
      principal_type: "user",
      user_id: userId,
      level,
    });
    expect(res.status, `${label}: ${res.text}`).toBe(201);
    shareIds[label] = String(res.json?.id);
  };
  await grant("app_instance", biz.instanceId, "read", "app_instance:read");
  for (const key of rights.read) await grant("app_model", models[key].id, "read", `${key}:read`);
  for (const key of rights.write) await grant("app_model", models[key].id, "write", `${key}:write`);
  for (const operation of rights.operations) {
    await grant("inventory_operations", biz.instanceId, operation, `inventory_operations:${operation}`);
  }
  return { userId, models, relationships: schema.relationships, shareIds };
}

export const grantCashier = (owner: Page, biz: FlagshipBusiness, email: string) =>
  grantMember(owner, biz, email, { read: READ_MODELS, write: WRITE_MODELS, operations: ["sell"] });

export const grantReceiver = (owner: Page, biz: FlagshipBusiness, email: string) =>
  grantMember(owner, biz, email, { read: RECEIVER_READ_MODELS, write: RECEIVER_WRITE_MODELS, operations: ["receive"] });
