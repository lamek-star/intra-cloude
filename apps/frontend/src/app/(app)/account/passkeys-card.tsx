"use client";

import { useState, type FormEvent } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Fingerprint, KeyRound, Smartphone, Trash2 } from "lucide-react";
import { api, ApiError, ensureCsrfCookie, type User } from "@/lib/api";
import {
  addPasskey,
  checkWithPasskey,
  passkeyErrorMessage,
  passkeysSupported,
  type PasskeyList,
  type PasskeyWhere,
} from "@/lib/passkeys";
import { Badge, Button, Card, ErrorBanner, Input, Label, Select } from "@/components/ui";

const passkeysKey = ["auth", "passkeys"] as const;

const WHERE_LABEL: Record<PasskeyWhere, string> = {
  phone: "My phone (scan a QR code)",
  this_device: "This computer (Windows Hello)",
  security_key: "A USB security key",
};

function when(value: string | null): string {
  return value ? new Date(value).toLocaleString() : "never";
}

type Mode = { kind: "idle" } | { kind: "add" } | { kind: "remove"; id: string; name: string } | { kind: "only-on" };

/** Passkeys (ADR-0019): sign in with a fingerprint or face on the owner's phone, and optionally only that way. */
export function PasskeysCard({ user, onChanged }: { user: User; onChanged: () => Promise<void> }) {
  const queryClient = useQueryClient();
  const list = useQuery({ queryKey: passkeysKey, queryFn: () => api.get<PasskeyList>("/auth/passkeys/") });
  const [mode, setMode] = useState<Mode>({ kind: "idle" });
  const [password, setPassword] = useState("");
  const [code, setCode] = useState("");
  const [name, setName] = useState("My phone");
  const [where, setWhere] = useState<PasskeyWhere>("phone");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState<string | null>(null);

  const data = list.data;
  const supported = passkeysSupported();
  const here = data?.passkeys.filter((p) => p.rp_id === data.this_address) ?? [];

  function reset() {
    setMode({ kind: "idle" });
    setPassword("");
    setCode("");
    setError(null);
  }

  async function run(action: () => Promise<string>) {
    setBusy(true);
    setError(null);
    setDone(null);
    try {
      await ensureCsrfCookie();
      const message = await action();
      reset();
      setDone(message);
      await Promise.all([queryClient.invalidateQueries({ queryKey: passkeysKey }), onChanged()]);
    } catch (err) {
      setError(passkeyErrorMessage(err) ?? (err instanceof ApiError ? err.message : "Something went wrong. Nothing was changed."));
    } finally {
      setBusy(false);
    }
  }

  const add = (e: FormEvent) => {
    e.preventDefault();
    return run(async () => {
      const made = await addPasskey({ password, code: code.trim(), name: name.trim() || "Passkey", where });
      return `"${made.name}" is added. You can now sign in with it at ${made.rp_id}.`;
    });
  };

  const remove = (e: FormEvent) => {
    e.preventDefault();
    if (mode.kind !== "remove") return;
    return run(async () => {
      await api.post(`/auth/passkeys/${mode.id}/remove/`, { password, code: code.trim() });
      return `"${mode.name}" is removed.`;
    });
  };

  const onlyOn = (e: FormEvent) => {
    e.preventDefault();
    return run(async () => {
      await api.post("/auth/passkeys/only/", { on: true, password, code: code.trim() });
      return "Password sign-in is off for your account. Only your passkey signs in now.";
    });
  };

  const onlyOff = () =>
    run(async () => {
      await checkWithPasskey("phone");
      await api.post("/auth/passkeys/only/", { on: false });
      return "Password sign-in is allowed again.";
    });

  const passwordFields = (
    <div className="grid gap-3 sm:grid-cols-2">
      <div>
        <Label htmlFor="passkey-password">Your password</Label>
        <Input
          id="passkey-password"
          type="password"
          autoComplete="current-password"
          required
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
      </div>
      {user.mfa_enabled && (
        <div>
          <Label htmlFor="passkey-code">Authenticator code</Label>
          <Input
            id="passkey-code"
            inputMode="numeric"
            autoComplete="one-time-code"
            pattern="[0-9]{6}"
            maxLength={6}
            required
            value={code}
            onChange={(e) => setCode(e.target.value)}
          />
        </div>
      )}
    </div>
  );

  return (
    <Card className="space-y-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex items-start gap-3">
          <Fingerprint aria-hidden="true" className={`mt-0.5 h-5 w-5 ${here.length ? "text-green-600" : "text-text-muted"}`} />
          <div>
            <h2 className="text-sm font-semibold text-text-primary">Passkeys</h2>
            <p className="mt-0.5 max-w-md text-sm text-slate-500">
              Sign in by scanning a QR code with your phone and confirming with your fingerprint or face. Nobody
              else can use it, even with your password.
            </p>
          </div>
        </div>
        {data?.passkey_only ? <Badge tone="success">Passkey only</Badge> : <Badge>{data?.passkeys.length ?? 0} added</Badge>}
      </div>

      <div aria-live="polite">{done && <p className="text-sm text-green-700">{done}</p>}</div>
      {error && <ErrorBanner message={error} />}
      {list.isError && <ErrorBanner message="Your passkeys could not be loaded." />}

      {data && !data.this_address && (
        <p className="rounded-lg bg-amber-50 p-3 text-sm text-amber-800">
          Passkeys need IntraForge&apos;s name in the address. Open it at https://localhost on this PC (or at the
          shop-network name) to add or use one.
        </p>
      )}
      {!supported && <p className="text-sm text-text-muted">This browser cannot use passkeys.</p>}

      {data && data.passkeys.length > 0 && (
        <ul className="divide-y divide-border-subtle rounded-lg border border-border-subtle">
          {data.passkeys.map((p) => (
            <li key={p.id} className="flex flex-wrap items-center justify-between gap-3 px-3 py-2.5">
              <div className="flex items-start gap-2.5">
                {p.transports.includes("hybrid") ? (
                  <Smartphone aria-hidden="true" className="mt-0.5 h-4 w-4 text-text-muted" />
                ) : (
                  <KeyRound aria-hidden="true" className="mt-0.5 h-4 w-4 text-text-muted" />
                )}
                <div>
                  <p className="text-sm font-medium text-text-primary">{p.name}</p>
                  <p className="text-xs text-text-muted">
                    For {p.rp_id}
                    {p.rp_id === data.this_address ? " (this address)" : ""} · added {when(p.created_at)} · last
                    used {when(p.last_used_at)}
                  </p>
                </div>
              </div>
              <Button
                variant="ghost"
                aria-label={`Remove ${p.name}`}
                onClick={() => {
                  reset();
                  setMode({ kind: "remove", id: p.id, name: p.name });
                }}
                disabled={busy}
              >
                <Trash2 size={15} aria-hidden="true" />
              </Button>
            </li>
          ))}
        </ul>
      )}

      {mode.kind === "idle" && (
        <div className="flex flex-wrap gap-2">
          <Button onClick={() => setMode({ kind: "add" })} disabled={busy || !supported || !data?.this_address}>
            Add a passkey
          </Button>
          {data && data.passkeys.length > 0 && !data.passkey_only && (
            <Button variant="secondary" onClick={() => setMode({ kind: "only-on" })} disabled={busy}>
              Sign in with passkey only
            </Button>
          )}
          {data?.passkey_only && (
            <Button variant="secondary" onClick={() => void onlyOff()} disabled={busy || !here.length}>
              Allow password sign-in again
            </Button>
          )}
        </div>
      )}

      {mode.kind === "add" && (
        <form onSubmit={add} className="space-y-4 rounded-lg border border-border-subtle bg-surface-sunken p-4">
          <p className="text-sm text-slate-600">
            Confirm it is you, then your browser shows a QR code: scan it with your phone&apos;s camera and confirm with
            your fingerprint or face. Bluetooth must be on, on both the phone and this PC.
          </p>
          <div className="grid gap-3 sm:grid-cols-2">
            <div>
              <Label htmlFor="passkey-name">Name</Label>
              <Input id="passkey-name" maxLength={80} value={name} onChange={(e) => setName(e.target.value)} />
            </div>
            <div>
              <Label htmlFor="passkey-where">Keep it on</Label>
              <Select id="passkey-where" value={where} onChange={(e) => setWhere(e.target.value as PasskeyWhere)}>
                {(Object.keys(WHERE_LABEL) as PasskeyWhere[]).map((w) => (
                  <option key={w} value={w}>
                    {WHERE_LABEL[w]}
                  </option>
                ))}
              </Select>
            </div>
          </div>
          {passwordFields}
          <div className="flex gap-2">
            <Button type="submit" disabled={busy || !password}>
              {busy ? "Waiting for the passkey..." : "Continue"}
            </Button>
            <Button type="button" variant="ghost" onClick={reset} disabled={busy}>
              Cancel
            </Button>
          </div>
        </form>
      )}

      {mode.kind === "remove" && (
        <form onSubmit={remove} className="space-y-4 rounded-lg border border-border-subtle bg-surface-sunken p-4">
          <p className="text-sm text-slate-600">
            Remove &ldquo;{mode.name}&rdquo;? It will no longer sign in. Delete it from your phone&apos;s password manager
            too.
          </p>
          {passwordFields}
          <div className="flex gap-2">
            <Button type="submit" variant="danger" disabled={busy || !password}>
              Remove
            </Button>
            <Button type="button" variant="ghost" onClick={reset} disabled={busy}>
              Cancel
            </Button>
          </div>
        </form>
      )}

      {mode.kind === "only-on" && (
        <form onSubmit={onlyOn} className="space-y-4 rounded-lg border border-border-subtle bg-surface-sunken p-4">
          <p className="text-sm text-slate-600">
            Your password will no longer sign in to this account -- only your passkey, at the address it was made for
            ({data?.passkeys.map((p) => p.rp_id).filter((v, i, a) => a.indexOf(v) === i).join(", ")}). If you lose
            your phone, IntraForge&apos;s administrator can let the password in again on the shop PC.
          </p>
          {passwordFields}
          <div className="flex gap-2">
            <Button type="submit" disabled={busy || !password}>
              Passkey only
            </Button>
            <Button type="button" variant="ghost" onClick={reset} disabled={busy}>
              Cancel
            </Button>
          </div>
        </form>
      )}
    </Card>
  );
}
