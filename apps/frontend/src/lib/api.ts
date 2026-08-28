// Talks to the Django/DRF backend at the same origin (Caddy routes
// /api/v1/* to it — see infrastructure/proxy/Caddyfile), so plain
// relative fetches with credentials:"include" work with no CORS setup
// needed, in this deployment or in `next dev` run behind the proxy.
// Session-cookie auth + Django's CSRF discipline (docs/api/API.md):
// every mutating request needs an X-CSRFToken header matching the
// csrftoken cookie, and the cookie only exists once something has
// called GET /auth/csrf/ (see ensureCsrfCookie).

const API_BASE = "/api/v1";

export class ApiError extends Error {
  status: number;
  body: unknown;
  /** Present when the backend used the structured `{error: {code, ...}}`
   * shape (system/exceptions.py) -- absent for the many views that
   * still `return Response({"detail": "..."})` or a bare status code
   * directly. Never a stack trace either way; the backend logs those
   * server-side only, keyed by requestId (Section 14 of the master
   * prompt). Surfaced by ErrorBanner's optional "View technical
   * details" disclosure, not shown by default. */
  code: string | null;
  requestId: string | null;

  constructor(status: number, body: unknown) {
    const detail = extractDetail(body);
    super(detail ?? DEFAULT_STATUS_MESSAGES[status] ?? `Request failed with status ${status}`);
    this.status = status;
    this.body = body;
    const errorObj =
      body && typeof body === "object" && (body as Record<string, unknown>).error;
    const errorRecord = errorObj && typeof errorObj === "object" ? (errorObj as Record<string, unknown>) : null;
    this.code = typeof errorRecord?.code === "string" ? errorRecord.code : null;
    this.requestId = typeof errorRecord?.request_id === "string" ? errorRecord.request_id : null;
  }
}

const DEFAULT_STATUS_MESSAGES: Record<number, string> = {
  400: "That request wasn't valid.",
  401: "Invalid credentials.",
  403: "You don't have permission to do that.",
  404: "Not found.",
  409: "That already exists.",
  429: "Too many requests — slow down and try again shortly.",
  502: "The request couldn't reach an external system.",
};

// Two response shapes exist in this backend: exceptions raised through
// DRF (serializer.is_valid(raise_exception=True), PermissionDenied, ...)
// go through system/exceptions.py's structured_exception_handler and
// come back as {"error": {"code", "message", "request_id"}}; many views
// instead `return Response({"detail": "..."})` or a bare
// `Response(status=403)` directly, bypassing that handler entirely.
// This unwraps whichever shape actually comes back.
function extractDetail(body: unknown): string | null {
  if (!body || typeof body !== "object") return null;
  const record = body as Record<string, unknown>;

  const error = record.error;
  if (error && typeof error === "object") {
    return messageToText((error as Record<string, unknown>).message) ?? messageToText(record);
  }
  return messageToText(record);
}

function messageToText(value: unknown): string | null {
  if (typeof value === "string") return value;
  if (Array.isArray(value) && typeof value[0] === "string") return value[0];
  if (value && typeof value === "object") {
    const record = value as Record<string, unknown>;
    if (typeof record.detail === "string") return record.detail;
    const firstKey = Object.keys(record)[0];
    if (firstKey) {
      const val = record[firstKey];
      if (Array.isArray(val) && typeof val[0] === "string") return `${firstKey}: ${val[0]}`;
      if (typeof val === "string") return `${firstKey}: ${val}`;
    }
  }
  return null;
}

function readCookie(name: string): string | null {
  if (typeof document === "undefined") return null;
  const match = document.cookie.match(new RegExp(`(?:^|; )${name}=([^;]*)`));
  return match ? decodeURIComponent(match[1]) : null;
}

let csrfPrimed = false;

/** Hits GET /auth/csrf/ once per page load so a subsequent mutating
 * request has a `csrftoken` cookie to echo back as X-CSRFToken. */
export async function ensureCsrfCookie(): Promise<void> {
  if (csrfPrimed && readCookie("csrftoken")) return;
  await fetch(`${API_BASE}/auth/csrf/`, { credentials: "include" });
  csrfPrimed = true;
}

type RequestOptions = {
  method?: "GET" | "POST" | "PATCH" | "PUT" | "DELETE";
  body?: unknown;
  isFormData?: boolean;
};

async function request<T>(path: string, opts: RequestOptions = {}): Promise<T> {
  const method = opts.method ?? "GET";
  const mutating = method !== "GET";

  if (mutating) {
    await ensureCsrfCookie();
  }

  const headers: Record<string, string> = {};
  let body: BodyInit | undefined;

  if (opts.body !== undefined) {
    if (opts.isFormData) {
      body = opts.body as FormData;
    } else {
      headers["Content-Type"] = "application/json";
      body = JSON.stringify(opts.body);
    }
  }

  if (mutating) {
    const csrf = readCookie("csrftoken");
    if (csrf) headers["X-CSRFToken"] = csrf;
  }

  const res = await fetch(`${API_BASE}${path}`, {
    method,
    headers,
    body,
    credentials: "include",
  });

  if (res.status === 204) {
    return undefined as T;
  }

  // Several views return a bare `Response(status=403)` with no body at
  // all (storage/views.py, applications/views.py, ...) — .text() is safe
  // on an empty body, .json() throws a SyntaxError on one.
  const contentType = res.headers.get("content-type") ?? "";
  const raw = await res.text();
  let payload: unknown = raw;
  if (raw && contentType.includes("application/json")) {
    try {
      payload = JSON.parse(raw);
    } catch {
      payload = raw;
    }
  }

  if (!res.ok) {
    throw new ApiError(res.status, payload);
  }
  return payload as T;
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body?: unknown) => request<T>(path, { method: "POST", body }),
  patch: <T>(path: string, body?: unknown) => request<T>(path, { method: "PATCH", body }),
  del: <T = void>(path: string, body?: unknown) => request<T>(path, { method: "DELETE", body }),
  postForm: <T>(path: string, form: FormData) =>
    request<T>(path, { method: "POST", body: form, isFormData: true }),
};

// --- Domain types (mirrors docs/api/API.md; only the fields the UI uses) ---

export type User = {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  date_joined: string;
  mfa_enabled: boolean;
};

export type Organization = {
  id: string;
  name: string;
  slug: string;
  external_sharing_enabled: boolean;
  created_at: string;
  created_by: string;
};

export type Membership = {
  id: string;
  user: User;
  organization: string;
  team: string | null;
  status: "invited" | "active" | "suspended";
  created_at: string;
};

export type Team = {
  id: string;
  organization: string;
  name: string;
  created_at: string;
};

export type Workspace = {
  id: string;
  organization: string;
  name: string;
  created_at: string;
};

export type Project = {
  id: string;
  workspace: string;
  name: string;
  created_at: string;
};

export type Bucket = {
  id: string;
  project: string;
  name: string;
  versioning_enabled: boolean;
  created_at: string;
  created_by: string;
};

export type FileObject = {
  id: string;
  bucket: string;
  folder: string | null;
  display_filename: string;
  size: number;
  content_type: string;
  status: "active" | "deleted";
  created_at: string;
};

export type TenantDatabase = {
  id: string;
  project: string;
  name: string;
  created_at: string;
  created_by: string;
};

export type DBColumn = {
  id: string;
  table: string;
  name: string;
  data_type: string;
  max_length: number | null;
  precision: number | null;
  scale: number | null;
  is_primary_key: boolean;
  is_nullable: boolean;
  is_unique: boolean;
  default_value: unknown;
  created_at: string;
};

export type DBTable = {
  id: string;
  tenant_database: string;
  name: string;
  created_at: string;
  created_by: string;
  columns: DBColumn[];
};

export type ConnectedDatabase = {
  id: string;
  project: string;
  name: string;
  engine: string;
  host: string;
  port: number;
  database_name: string;
  username: string;
  sslmode: string;
  status: "untested" | "connected" | "unreachable";
  last_tested_at: string | null;
  last_test_error: string;
  created_at: string;
};

export type ConnectedColumn = {
  name: string;
  data_type: string;
  is_nullable: boolean;
};

export type ConnectedTableSchema = {
  name: string;
  columns: ConnectedColumn[];
};

export type RowsPage = {
  count: number;
  limit: number;
  offset: number;
  results: Record<string, unknown>[];
};

export type ImportPreviewColumn = {
  csv_column: string;
  inferred_type: string;
};

export type ImportPreview = {
  encoding: string;
  delimiter: string;
  headers: string[];
  sample_rows: string[][];
  columns: ImportPreviewColumn[];
};

export type ColumnMappingEntry = {
  csv_column: string;
  target_column: string;
  target_type: string;
};

export type ImportJob = {
  id: string;
  file: string;
  table: string;
  encoding: string;
  delimiter: string;
  column_mapping: ColumnMappingEntry[];
  status: "pending" | "running" | "completed" | "failed";
  total_rows: number;
  imported_rows: number;
  rejected_rows: number;
  error_message: string;
  created_by: string;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
};

export type ImportJobError = {
  id: string;
  row_number: number;
  message: string;
  raw_row: Record<string, unknown>;
  created_at: string;
};

export type ColumnProfile = {
  name: string;
  data_type: string;
  missing_count: number;
  null_percentage: number;
  unique_count: number;
  min?: number;
  max?: number;
  mean?: number;
  median?: number;
  stdev?: number;
  potential_outlier_count?: number;
  top_values?: { value: unknown; count: number }[];
};

export type TableProfile = {
  table: string;
  row_count: number;
  column_count: number;
  truncated: boolean;
  sampled_rows: number;
  columns: ColumnProfile[];
};

// DRF's stock LimitOffsetPagination shape (config/settings/base.py's
// DEFAULT_PAGINATION_CLASS) -- distinct from RowsPage above, which is a
// bespoke shape the row-browsing endpoint returns instead.
export type Paginated<T> = {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
};

export type AuditEvent = {
  id: string;
  timestamp: string;
  actor: string | null;
  organization: string | null;
  action: string;
  resource_type: string;
  resource_id: string;
  request_id: string;
  result: "success" | "denied" | "error";
  context: Record<string, unknown>;
};

export type Application = {
  id: string;
  organization: string;
  name: string;
  description: string;
  owner: string;
  created_at: string;
};

export type ApplicationCredential = {
  id: string;
  created_at: string;
  last_used_at: string | null;
  expires_at: string | null;
  revoked_at: string | null;
  /** Only present exactly once, in the response to create/rotate — the
   * backend never stores or re-returns the plaintext. */
  secret?: string;
};

export type Environment = {
  id: string;
  application: string;
  name: string;
  slug: string;
  environment_type: string;
  is_production_tier: boolean;
  status: "active" | "disabled";
  config: Record<string, unknown>;
  created_by: string;
  created_at: string;
  updated_at: string;
  last_activity_at: string | null;
  database_status: "connected" | "not_connected";
  storage_status: "connected" | "not_connected";
  credential_count: number;
};

export type EnvironmentVariable = {
  id: string;
  key: string;
  value: string;
  created_at: string;
  updated_at: string;
};

export type EnvironmentSecret = {
  id: string;
  key: string;
  created_at: string;
  rotated_at: string | null;
  /** Only present exactly once, in the response to create/rotate. */
  value?: string;
};

export type EnvironmentWebhook = {
  id: string;
  url: string;
  event_types: string[];
  enabled: boolean;
  created_at: string;
  /** Only present exactly once, in the response to creation. */
  signing_secret?: string;
};

export type ShareGrant = {
  id: string;
  organization: string;
  resource_type: string;
  resource_id: string;
  principal_type: "user" | "team" | "organization";
  user: string | null;
  team: string | null;
  level: "read" | "write" | "admin";
  expires_at: string | null;
  revoked_at: string | null;
  created_by: string | null;
  created_at: string;
};

export type ResourceGrant = {
  id: string;
  permission: string;
  resource_type: string;
  resource_id: string;
  granted_by: string | null;
  expires_at: string | null;
  created_at: string;
};

export type DashboardWidget = {
  table_id: string;
  operation: string;
  params?: Record<string, unknown>;
  chart_type?: string;
  title?: string;
  position?: number;
};

export type Dashboard = {
  id: string;
  tenant_database: string;
  name: string;
  widgets: DashboardWidget[];
  created_by: string;
  created_at: string;
  updated_at: string;
};

export type DashboardWidgetResult = {
  title: string;
  chart_type: string;
  data?: Record<string, unknown>;
  error?: string;
};

export type DashboardRenderResult = {
  id: string;
  name: string;
  widgets: DashboardWidgetResult[];
};
