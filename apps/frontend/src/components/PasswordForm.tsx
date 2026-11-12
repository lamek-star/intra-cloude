"use client";

import { useState, type FormEvent } from "react";
import { api, ApiError, ensureCsrfCookie } from "@/lib/api";
import { Button, ErrorBanner, Input, Label } from "@/components/ui";

/** Changing one's own password: the current one, then the new one twice. */
export function PasswordForm({ onDone, currentLabel = "Current password" }: { onDone: () => Promise<void> | void; currentLabel?: string }) {
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [again, setAgain] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const mismatch = again.length > 0 && next !== again;

  async function submit(e: FormEvent) {
    e.preventDefault();
    if (next !== again) return;
    setBusy(true);
    setError(null);
    try {
      await ensureCsrfCookie();
      await api.post("/auth/password/", { current_password: current, new_password: next });
      setCurrent("");
      setNext("");
      setAgain("");
      await onDone();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "The password was not changed.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={submit} className="space-y-3">
      {error && <ErrorBanner message={error} />}
      <div>
        <Label htmlFor="pw-current">{currentLabel}</Label>
        <Input id="pw-current" type="password" autoComplete="current-password" required value={current} onChange={(e) => setCurrent(e.target.value)} />
      </div>
      <div className="grid gap-3 sm:grid-cols-2">
        <div>
          <Label htmlFor="pw-new">New password</Label>
          <Input id="pw-new" type="password" autoComplete="new-password" required minLength={8} value={next} onChange={(e) => setNext(e.target.value)} />
        </div>
        <div>
          <Label htmlFor="pw-again">New password again</Label>
          <Input id="pw-again" type="password" autoComplete="new-password" required value={again} onChange={(e) => setAgain(e.target.value)} />
        </div>
      </div>
      {mismatch && <p className="text-xs text-red-600">The two new passwords are not the same.</p>}
      <Button type="submit" disabled={busy || mismatch || !current || !next}>
        {busy ? "Saving..." : "Change password"}
      </Button>
    </form>
  );
}
