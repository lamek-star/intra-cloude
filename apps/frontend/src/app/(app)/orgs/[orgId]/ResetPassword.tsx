"use client";

import { useState } from "react";
import { KeyRound } from "lucide-react";
import { api, ApiError, ensureCsrfCookie } from "@/lib/api";
import { Button, CopyButton, ErrorBanner, Modal } from "@/components/ui";
import { useConfirm } from "@/components/ConfirmProvider";

/** A member forgot their password: give them a temporary one (shown once). They are signed out everywhere and must
 * choose their own at the next sign-in. The server refuses when the person also belongs to an organization this
 * administrator does not manage. */
export function ResetPassword({ orgId, membershipId, who }: { orgId: string; membershipId: string; who: string }) {
  const confirm = useConfirm();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [temporary, setTemporary] = useState<string | null>(null);

  async function reset() {
    const ok = await confirm({
      title: `Reset the password of ${who}?`,
      description:
        "They get a temporary password that you hand to them, are signed out on every device, and choose their own at the next sign-in. Two-step sign-in, if they use it, stays on.",
      confirmLabel: "Reset password",
    });
    if (!ok) return;
    setBusy(true);
    setError(null);
    try {
      await ensureCsrfCookie();
      const r = await api.post<{ temporary_password: string }>(
        `/organizations/${orgId}/members/${membershipId}/reset-password/`,
      );
      setTemporary(r.temporary_password);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "The password was not reset.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <Button size="sm" variant="ghost" disabled={busy} onClick={() => void reset()} aria-label={`Reset the password of ${who}`}>
        <KeyRound aria-hidden="true" className="h-3.5 w-3.5" />
        Reset password
      </Button>
      {error && <ErrorBanner message={error} />}
      {temporary && (
        <Modal open onClose={() => setTemporary(null)} title="Temporary password">
          <div className="space-y-4">
            <p className="text-sm text-slate-600">
              Give this to <strong>{who}</strong> in person. It is shown only now; they choose their own password when they
              sign in with it.
            </p>
            <div className="flex items-center gap-2">
              <code className="rounded bg-slate-900 px-3 py-2 font-mono text-base tracking-wider text-slate-100">{temporary}</code>
              <CopyButton value={temporary} label="Copy" />
            </div>
            <div className="flex justify-end">
              <Button onClick={() => setTemporary(null)}>Done</Button>
            </div>
          </div>
        </Modal>
      )}
    </>
  );
}
