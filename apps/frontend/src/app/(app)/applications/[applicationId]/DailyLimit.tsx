"use client";

import { useState, type FormEvent } from "react";
import { Gauge } from "lucide-react";
import { api, ApiError, type Application } from "@/lib/api";
import { Badge, Button, Card, ErrorBanner, Input, Label } from "@/components/ui";

export const MAX_DAILY_LIMIT = 10_000_000;

/** "120 of 5,000 today" / "120 today, no limit" -- what the owner reads at a glance. */
export function limitText(limit: number | null | undefined, used: number | undefined): string {
  const today = (used ?? 0).toLocaleString("en-US");
  return limit ? `${today} of ${limit.toLocaleString("en-US")} today` : `${today} today, no limit`;
}

/** The share of today's limit already used, 0..100; null with no limit. */
export function limitPercent(limit: number | null | undefined, used: number | undefined): number | null {
  if (!limit) return null;
  return Math.min(100, Math.round(((used ?? 0) / limit) * 100));
}

/** Empty = no limit; otherwise a whole number 1..10,000,000. Returns the value or a message for the person. */
export function parseLimit(text: string): { value: number | null } | { error: string } {
  const clean = text.replace(/[,\s]/g, "");
  if (clean === "") return { value: null };
  if (!/^\d+$/.test(clean)) return { error: "Type a whole number, or leave it empty for no limit." };
  const value = Number(clean);
  if (value < 1 || value > MAX_DAILY_LIMIT) return { error: "Choose between 1 and 10,000,000 requests a day." };
  return { value };
}

function tone(percent: number | null): "info" | "warning" | "danger" | "default" {
  if (percent === null) return "default";
  if (percent >= 100) return "danger";
  return percent >= 80 ? "warning" : "info";
}

/** How many requests the application's keys may make per day (applications/quotas.py). Changing it needs the
 * right to manage the application's keys; the server says so if the person does not have it. */
export function DailyLimit({ application, onChange }: { application: Application; onChange: (a: Application) => void }) {
  const [editing, setEditing] = useState(false);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<{ message: string; cause?: unknown } | null>(null);
  const limit = application.daily_request_limit ?? null;
  const percent = limitPercent(limit, application.requests_today);

  async function save(event: FormEvent) {
    event.preventDefault();
    const parsed = parseLimit(text);
    if ("error" in parsed) {
      setError({ message: parsed.error });
      return;
    }
    setBusy(true);
    setError(null);
    try {
      onChange(await api.patch<Application>(`/applications/${application.id}/`, { daily_request_limit: parsed.value }));
      setEditing(false);
    } catch (err) {
      setError({
        message:
          err instanceof ApiError && err.status === 403
            ? "Only someone who manages this application's keys can change its limit."
            : err instanceof ApiError
              ? err.message
              : "Could not change the limit.",
        cause: err,
      });
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="flex items-center gap-2 text-sm font-semibold text-text-primary">
            <Gauge className="h-4 w-4" /> Daily request limit
          </h3>
          <p className="mt-1 text-sm text-text-muted">{limitText(limit, application.requests_today)}</p>
        </div>
        <Badge tone={tone(percent)}>{percent === null ? "No limit" : `${percent}% used`}</Badge>
      </div>
      {percent !== null && (
        <div className="mt-3 h-2 w-full overflow-hidden rounded bg-slate-100" aria-hidden="true">
          <div
            className={`h-full ${percent >= 100 ? "bg-red-500" : percent >= 80 ? "bg-amber-500" : "bg-blue-500"}`}
            style={{ width: `${percent}%` }}
          />
        </div>
      )}
      <p className="mt-3 text-xs text-text-muted">
        When the limit is reached, IntraForge refuses the application&apos;s requests until midnight (UTC) and
        lists them as 429 under Requests. People using IntraForge themselves are never limited.
      </p>
      {error && (
        <div className="mt-3">
          <ErrorBanner message={error.message} error={error.cause} />
        </div>
      )}
      {editing ? (
        <form onSubmit={save} className="mt-3 flex flex-wrap items-end gap-2">
          <div>
            <Label htmlFor="daily-limit">Requests per day</Label>
            <Input
              id="daily-limit"
              inputMode="numeric"
              placeholder="Empty = no limit"
              value={text}
              onChange={(e) => setText(e.target.value)}
              autoFocus
            />
          </div>
          <Button type="submit" size="sm" disabled={busy}>
            {busy ? "Saving…" : "Save"}
          </Button>
          <Button type="button" size="sm" variant="ghost" onClick={() => setEditing(false)}>
            Cancel
          </Button>
        </form>
      ) : (
        <div className="mt-3">
          <Button
            size="sm"
            variant="secondary"
            onClick={() => {
              setText(limit ? String(limit) : "");
              setError(null);
              setEditing(true);
            }}
          >
            {limit ? "Change limit" : "Set a limit"}
          </Button>
        </div>
      )}
    </Card>
  );
}
