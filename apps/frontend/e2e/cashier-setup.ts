import { expect, type APIResponse, type Browser, type BrowserContext, type Page } from "@playwright/test";
import { DEMO_PASSWORD, type FlagshipBusiness } from "./flagship-setup";
import { register, uniqueEmail } from "./helpers";

// A restricted cashier, set up exactly the way a customer would: a real second user, added to the
// organization through the "Add member" dialog, holding ONLY these sharing grants (no role at all).
// Shared by the restricted-cashier journey and the recovery/upgrade drills so they all use the same,
// documented grants (see docs/LOCAL_EDITION_APPLICATIONS.md, "Roles and the cashier limit").
//
//   app_instance  READ   the application itself (open it, read its structure)
//   app_model     READ   part, part_number, warehouse, customer
//   app_model     WRITE  sales_order, sales_order_line, invoice, stock_movement, inventory

export const READ_MODELS = ["part", "part_number", "warehouse", "customer"];
export const WRITE_MODELS = ["sales_order", "sales_order_line", "invoice", "stock_movement", "inventory"];

export type Json = Record<string, unknown>;
export type Field = { id: string; key: string };
export type Model = { id: string; key: string; fields: Field[] };
export type Relationship = { id: string; key: string; source_model: string };
export type Reply = { status: number; text: string; json: Json | null };

/** A session-cookie API call from a page's own login: primes and echoes the CSRF token, sends an Origin. */
export async function call(page: Page, method: string, path: string, data?: unknown): Promise<Reply> {
  await page.request.get("/api/v1/auth/csrf/");
  const cookies = await page.context().cookies();
  const csrf = cookies.find((c) => c.name === "csrftoken")?.value ?? "";
  const origin = new URL(page.url() === "about:blank" ? "https://localhost:8444" : page.url()).origin;
  const res: APIResponse = await page.request.fetch(`/api/v1${path}`, {
    method,
    headers: { "X-CSRFToken": csrf, Origin: origin, Referer: `${origin}/` },
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
export async function registerCashier(browser: Browser, prefix = "cashier") {
  const context: BrowserContext = await browser.newContext();
  const page = await context.newPage();
  const email = uniqueEmail(prefix);
  await register(page, email, DEMO_PASSWORD);
  return { context, page, email };
}

export type CashierAccess = {
  userId: string;
  models: Record<string, Model>;
  relationships: Relationship[];
  shareIds: Record<string, string>;
};

/** The owner adds the cashier through the UI dialog, then grants exactly the documented rights. */
export async function grantCashier(owner: Page, biz: FlagshipBusiness, cashierEmail: string): Promise<CashierAccess> {
  await owner.goto(`/orgs/${biz.orgId}`);
  await owner.getByRole("button", { name: "Add member" }).click();
  const dialog = owner.getByRole("dialog", { name: "Add member" });
  await dialog.getByLabel("Email of an existing user").fill(cashierEmail);
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
  const member = members.find((m) => m.user.email.toLowerCase() === cashierEmail.toLowerCase());
  expect(member, "the cashier appears in the member list").toBeTruthy();
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
  for (const key of READ_MODELS) await grant("app_model", models[key].id, "read", `${key}:read`);
  for (const key of WRITE_MODELS) await grant("app_model", models[key].id, "write", `${key}:write`);
  return { userId, models, relationships: schema.relationships, shareIds };
}
