// Customer-facing business screens over an installed App Platform application.
//
// Nothing here knows a database table or a hard-coded id: models, fields and relationships
// are resolved by their stable *keys* from the instance's own metadata (`loadSchema`), the same
// records API every screen uses. Inventory arithmetic is never done in the browser -- a receive or
// a sale is described as an ordered list of operations and posted to the backend's atomic
// transaction endpoint (app_platform/transactions.py), where the database ledger decides the
// resulting balance. The only arithmetic here is money on the *document* (line totals), which the
// template models as plain caller-supplied decimals.

import {
  ApiError,
  api,
  type AppFieldDefinition,
  type AppModelDefinition,
  type AppRecordsPage,
  type AppRelationshipDefinition,
} from "@/lib/api";

export type BusinessRow = Record<string, unknown>;

export type BusinessSchema = {
  instanceId: string;
  /** The model's id, by its template key (e.g. "part"). */
  modelId: (modelKey: string) => string;
  /** The id of a field on the model, or of a relationship it owns, by key (e.g. "name", "part"). */
  id: (modelKey: string, key: string) => string;
};

export function makeSchema(
  instanceId: string,
  models: AppModelDefinition[],
  fieldsByModelId: Record<string, AppFieldDefinition[]>,
  relationships: AppRelationshipDefinition[],
): BusinessSchema {
  const modelByKey = new Map(models.map((m) => [m.key, m]));
  const modelId = (modelKey: string) => {
    const model = modelByKey.get(modelKey);
    if (!model) throw new Error(`This application has no "${modelKey}" section.`);
    return model.id;
  };
  const id = (modelKey: string, key: string) => {
    const model = modelId(modelKey);
    const field = (fieldsByModelId[model] ?? []).find((f) => f.key === key);
    if (field) return field.id;
    const relation = relationships.find((r) => r.key === key && r.source_model === model);
    if (relation) return relation.id;
    throw new Error(`"${modelKey}" has no "${key}".`);
  };
  return { instanceId, modelId, id };
}

/** The whole schema arrives in ONE request (`GET /app-instances/<id>/schema/`). It used to take 2 + N
 * list requests per page load (N = number of models), which exhausted the per-user rate limit after
 * about twenty full page loads. */
export async function loadSchema(instanceId: string): Promise<BusinessSchema> {
  const schema = await api.get<{
    models: (AppModelDefinition & { fields: AppFieldDefinition[] })[];
    relationships: AppRelationshipDefinition[];
  }>(`/app-instances/${instanceId}/schema/`);
  const fieldsByModelId: Record<string, AppFieldDefinition[]> = {};
  for (const model of schema.models) fieldsByModelId[model.id] = model.fields;
  return makeSchema(instanceId, schema.models, fieldsByModelId, schema.relationships);
}

// --- records (all filtering, searching and paging is done by the server) ---------------------

export type ListOptions = {
  /** Server-side search; App Platform record search also matches part numbers however they are written. */
  search?: string;
  /** Equality filters keyed by field/relationship key. */
  filters?: Record<string, string>;
  limit?: number;
  offset?: number;
  /** A field key; prefix with "-" for descending. */
  ordering?: string;
};

export async function listRecords(
  schema: BusinessSchema,
  modelKey: string,
  opts: ListOptions = {},
): Promise<AppRecordsPage> {
  const params = new URLSearchParams();
  params.set("limit", String(opts.limit ?? 50));
  if (opts.offset) params.set("offset", String(opts.offset));
  if (opts.search?.trim()) params.set("search", opts.search.trim());
  if (opts.ordering) {
    const desc = opts.ordering.startsWith("-");
    params.set("ordering", `${desc ? "-" : ""}${schema.id(modelKey, desc ? opts.ordering.slice(1) : opts.ordering)}`);
  }
  for (const [key, value] of Object.entries(opts.filters ?? {})) params.set(schema.id(modelKey, key), value);
  return api.get<AppRecordsPage>(`/app-models/${schema.modelId(modelKey)}/records/?${params.toString()}`);
}

/** Every record of a (small) model, in pages of 500 -- for name lookups and short pick lists only. */
export async function listAllRecords(schema: BusinessSchema, modelKey: string, cap = 5000): Promise<BusinessRow[]> {
  const rows: BusinessRow[] = [];
  for (let offset = 0; offset < cap; offset += 500) {
    const page = await listRecords(schema, modelKey, { limit: 500, offset });
    rows.push(...page.results);
    if (rows.length >= page.count || page.results.length === 0) break;
  }
  return rows;
}

/** The named records of one model in as few requests as possible (`?ids=`, at most 100 per request).
 * Used to put names next to ids in a page of rows: one request for the page, never one per row. */
export async function listRecordsByIds(schema: BusinessSchema, modelKey: string, ids: string[]): Promise<BusinessRow[]> {
  const rows: BusinessRow[] = [];
  for (let start = 0; start < ids.length; start += IDS_PER_REQUEST) {
    const chunk = ids.slice(start, start + IDS_PER_REQUEST);
    const page = await api.get<AppRecordsPage>(
      `/app-models/${schema.modelId(modelKey)}/records/?ids=${chunk.join(",")}&limit=${IDS_PER_REQUEST}`,
    );
    rows.push(...page.results);
  }
  return rows;
}

const IDS_PER_REQUEST = 100; // the server's cap (record_views.MAX_IDS)

export async function getRecord(schema: BusinessSchema, modelKey: string, recordId: string): Promise<BusinessRow> {
  return api.get<BusinessRow>(`/app-models/${schema.modelId(modelKey)}/records/${recordId}/`);
}

export function toPayload(schema: BusinessSchema, modelKey: string, values: Record<string, unknown>) {
  const payload: Record<string, unknown> = {};
  for (const [key, value] of Object.entries(values)) {
    if (value !== undefined) payload[schema.id(modelKey, key)] = value;
  }
  return payload;
}

export async function createRecord(
  schema: BusinessSchema,
  modelKey: string,
  values: Record<string, unknown>,
): Promise<BusinessRow> {
  return api.post<BusinessRow>(`/app-models/${schema.modelId(modelKey)}/records/`, toPayload(schema, modelKey, values));
}

/** A record's value by field/relationship key. */
export function cell(schema: BusinessSchema, modelKey: string, row: BusinessRow, key: string): unknown {
  return row[schema.id(modelKey, key)];
}

export function cellText(schema: BusinessSchema, modelKey: string, row: BusinessRow, key: string): string {
  const value = cell(schema, modelKey, row, key);
  return value === null || value === undefined ? "" : String(value);
}

/** Presentation only -- used to put an exact match first in a result list the SERVER already
 * searched. The authoritative rule and search live in the backend (databases/normalization.py:
 * remove whitespace and hyphens, uppercase); this mirrors it so `044650K290` ranks above a partial
 * match for `04465 0K290`. It never decides what is found. */
export function normalizeSearchKey(value: string): string {
  return value.replace(/[\s-]/g, "").toUpperCase();
}

// --- money, quantities, dates ----------------------------------------------------------------

/** "15", "15.5", "15.50" -> cents; anything else (empty, negative, 3 decimals, text) -> null. */
export function parseMoney(input: string): number | null {
  const match = /^(\d{1,12})(?:\.(\d{1,2}))?$/.exec(input.trim());
  if (!match) return null;
  return Number(match[1]) * 100 + Number((match[2] ?? "").padEnd(2, "0") || "0");
}

export function formatMoney(cents: number): string {
  const sign = cents < 0 ? "-" : "";
  const abs = Math.abs(cents);
  return `${sign}${Math.floor(abs / 100)}.${String(abs % 100).padStart(2, "0")}`;
}

/** A whole number of at least 1, else null. */
export function parseQuantity(input: string): number | null {
  const trimmed = input.trim();
  if (!/^\d{1,9}$/.test(trimmed)) return null;
  const value = Number(trimmed);
  return value >= 1 ? value : null;
}

/** A timestamp in the form the platform's datetime contract accepts: naive UTC, whole seconds,
 * `YYYY-MM-DDTHH:MM:SS` (databases/formats.py, shared with the CSV importer). `Date.toISOString()`
 * -- with milliseconds and a `Z` -- is refused by the API, so it must not be sent as-is. */
export function platformTimestamp(now: Date = new Date()): string {
  return now.toISOString().slice(0, 19);
}

export function todayIso(now: Date = new Date()): string {
  return now.toISOString().slice(0, 10);
}

/** A readable, practically unique invoice number, e.g. INV-20260919-K3F9Q. The backend enforces
 * uniqueness; a collision is rejected and the user simply submits again. */
export function newInvoiceNumber(now: Date = new Date(), random: () => number = Math.random): string {
  const alphabet = "0123456789ABCDEFGHJKLMNPQRSTUVWXYZ";
  let suffix = "";
  for (let i = 0; i < 5; i++) suffix += alphabet[Math.floor(random() * alphabet.length)];
  return `INV-${todayIso(now).replaceAll("-", "")}-${suffix}`;
}

export function newIdempotencyKey(): string {
  return crypto.randomUUID();
}

// --- business operations -----------------------------------------------------------------------
//
// The browser states an INTENT -- "sell these lines to this customer", "receive this quantity into this
// warehouse" -- and the server builds the records, checks the caller's business-operation authority
// (`inventory.sell` / `inventory.receive`, ADR-0017) and commits everything atomically. The browser never
// assembles stock movements and never states a balance: the database ledger decides the result.

export type TransactionResult = {
  results: { operation: number; model: string; ref: string | null; record: BusinessRow }[];
};

export type ReceiveInput = {
  partId: string;
  warehouseId: string;
  quantity: number;
  supplierId?: string;
  /** Cost per unit in cents; only used when a supplier is given (it then records a purchase order). */
  unitCostCents?: number;
  reference?: string;
  now?: Date;
};

export type ReceiveIntent = {
  part: string;
  warehouse: string;
  quantity: number;
  supplier?: string;
  unit_cost?: string;
  reference?: string;
  occurred_at: string;
};

/** Receiving stock: one stock-in movement, plus -- when a supplier is chosen -- a received purchase order. */
export function buildReceiveIntent(input: ReceiveInput): ReceiveIntent {
  const intent: ReceiveIntent = {
    part: input.partId,
    warehouse: input.warehouseId,
    quantity: input.quantity,
    occurred_at: platformTimestamp(input.now ?? new Date()),
  };
  if (input.supplierId) {
    intent.supplier = input.supplierId;
    intent.unit_cost = formatMoney(input.unitCostCents ?? 0);
  }
  const reference = input.reference?.trim();
  if (reference) intent.reference = reference;
  return intent;
}

export type SaleLine = { partId: string; warehouseId: string; quantity: number; unitPriceCents: number };

export type SaleInput = { customerId: string; lines: SaleLine[]; invoiceNumber: string; now?: Date };

export type SaleIntent = {
  customer: string;
  invoice_number: string;
  occurred_at: string;
  lines: { part: string; warehouse: string; quantity: number; unit_price: string }[];
};

export function saleTotalCents(lines: SaleLine[]): number {
  return lines.reduce((sum, line) => sum + line.unitPriceCents * line.quantity, 0);
}

/** A sale: the server records the order, one line and one stock-out movement per item, and the invoice, all
 * in one transaction. The movement's reference is the invoice number so the document can list them. */
export function buildSaleIntent(input: SaleInput): SaleIntent {
  return {
    customer: input.customerId,
    invoice_number: input.invoiceNumber,
    occurred_at: platformTimestamp(input.now ?? new Date()),
    lines: input.lines.map((line) => ({
      part: line.partId,
      warehouse: line.warehouseId,
      quantity: line.quantity,
      unit_price: formatMoney(line.unitPriceCents),
    })),
  };
}

export async function postSale(schema: BusinessSchema, intent: SaleIntent, idempotencyKey: string): Promise<TransactionResult> {
  return api.postIdempotent<TransactionResult>(`/app-instances/${schema.instanceId}/operations/sell/`, intent, idempotencyKey);
}

export async function postReceive(
  schema: BusinessSchema,
  intent: ReceiveIntent,
  idempotencyKey: string,
): Promise<TransactionResult> {
  return api.postIdempotent<TransactionResult>(
    `/app-instances/${schema.instanceId}/operations/receive/`,
    intent,
    idempotencyKey,
  );
}

/** A plain-language reason for a failed business operation. Nothing was changed on failure -- the
 * backend rolls the whole transaction back -- and the message says so. */
export function explainOperationError(err: unknown): string {
  if (err instanceof ApiError) {
    const detail = (err.body as { detail?: unknown } | null)?.detail;
    if (err.status === 400 && typeof detail === "string" && detail.includes("would go negative")) {
      return "There is not enough stock in that warehouse to complete this. Nothing was changed.";
    }
    if (err.status === 403) return "You don't have permission to do this. Nothing was changed.";
    if (err.status === 409) return "This was already submitted with different details. Start it again. Nothing was changed.";
    if (err.status === 400 && typeof detail === "string") return `${detail} Nothing was changed.`;
    if (err.status >= 500) return "Something went wrong on the server. Nothing was changed; please try again.";
    return `${err.message} Nothing was changed.`;
  }
  return "Something went wrong. Nothing was changed; please try again.";
}
