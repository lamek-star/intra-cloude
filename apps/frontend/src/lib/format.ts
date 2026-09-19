// Small, dependency-free display helpers for the business screens.

/** The platform stores and returns naive UTC timestamps (`2026-09-19T13:35:00`); JavaScript would
 * read a zone-less string as LOCAL time and show the wrong hour, so mark it as UTC first. */
function asUtc(value: string): string {
  return /^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}(:\d{2}(\.\d+)?)?$/.test(value) ? `${value.replace(" ", "T")}Z` : value;
}

/** "19 Sep 2026, 10:30" for a platform timestamp; the original text if it can't be parsed. */
export function formatDateTime(value: unknown): string {
  if (typeof value !== "string" || !value) return "";
  const date = new Date(asUtc(value));
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString("en-GB", { day: "2-digit", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" });
}

/** "19 Sep 2026" for an ISO date or timestamp. */
export function formatDate(value: unknown): string {
  if (typeof value !== "string" || !value) return "";
  const date = new Date(value.length === 10 ? `${value}T00:00:00` : value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric" });
}

/** "+100" / "-5" / "0" -- a movement's effect on stock, shown with its sign. */
export function signed(value: unknown): string {
  const n = Number(value);
  if (!Number.isFinite(n)) return String(value ?? "");
  return n > 0 ? `+${n}` : String(n);
}

/** A decimal string from the API ("75.0000") as "75.00"; anything else unchanged. */
export function money(value: unknown): string {
  const n = Number(value);
  return Number.isFinite(n) ? n.toFixed(2) : String(value ?? "");
}
