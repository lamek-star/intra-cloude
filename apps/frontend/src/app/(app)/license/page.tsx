"use client";

import { useId, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Check, Copy, KeyRound, ShieldCheck } from "lucide-react";
import { licenceApi, type Licence } from "@/lib/license";
import {
  Badge,
  Button,
  Card,
  ErrorBanner,
  Input,
  Label,
  PageHeader,
  PageLoading,
} from "@/components/ui";

const STATE: Record<
  Licence["state"],
  [string, "success" | "warning" | "danger" | "default"]
> = {
  active: ["Licensed", "success"],
  trial: ["Trial", "warning"],
  expired: ["Read-only", "danger"],
  not_enforced: ["Not required here", "default"],
};

/** The licence: this PC's code, the serial number and the activation code from the vendor. */
export default function LicencePage() {
  const qc = useQueryClient();
  const licence = useQuery({ queryKey: ["licence"], queryFn: licenceApi.get });
  const [serial, setSerial] = useState("");
  const [code, setCode] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const ids = { serial: useId(), code: useId() };

  if (licence.isError)
    return (
      <ErrorBanner
        message="The licence could not be read."
        error={licence.error}
      />
    );
  if (!licence.data) return <PageLoading />;
  const l = licence.data;
  const [label, tone] = STATE[l.state];

  async function activate(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      qc.setQueryData(
        ["licence"],
        await licenceApi.activate(serial.trim(), code.trim()),
      );
      setSerial("");
      setCode("");
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "The licence could not be activated.",
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="max-w-3xl">
      <PageHeader
        title="Licence"
        description="IntraForge works fully for the trial; after it, a serial number activated for this PC keeps it working."
      />
      <Card className="flex flex-col gap-4">
        <div className="flex flex-wrap items-center gap-3">
          <span
            className={`grid h-10 w-10 place-items-center rounded-xl ${l.state === "active" ? "bg-green-100 text-green-700" : "bg-brand-50 text-brand-700"}`}
          >
            {l.state === "active" ? (
              <ShieldCheck className="h-5 w-5" />
            ) : (
              <KeyRound className="h-5 w-5" />
            )}
          </span>
          <div className="min-w-0 flex-1">
            <p className="text-base font-semibold text-slate-900">
              {l.state === "active"
                ? `Licensed${l.kind === "master" ? " (master)" : ""}: ${l.serial}`
                : l.state === "trial"
                  ? `Trial: ${l.days_left} ${l.days_left === 1 ? "day" : "days"} left`
                  : l.state === "expired"
                    ? "The trial has ended: read-only until activated"
                    : "No licence is needed on this installation"}
            </p>
            <p className="text-sm text-slate-500">
              {l.state === "active" && l.activated_at
                ? `Activated ${new Date(l.activated_at).toLocaleDateString()}`
                : l.state === "trial" || l.state === "expired"
                  ? `The ${l.trial_days}-day trial ${l.state === "trial" ? "ends" : "ended"} ${new Date(l.trial_ends).toLocaleDateString()}. Read-only means you can still sign in, see and export everything, and backups keep running.`
                  : ""}
            </p>
          </div>
          <Badge tone={tone}>{label}</Badge>
        </div>

        <div className="rounded-xl bg-slate-50 p-4">
          <p className="text-sm font-medium text-slate-700">
            This PC&apos;s code
          </p>
          {l.pc_code ? (
            <div className="mt-1 flex items-center gap-2">
              <code className="font-mono text-lg font-semibold tracking-wider text-slate-900">
                {l.pc_code}
              </code>
              <button
                type="button"
                className="rounded-md p-1.5 text-slate-500 hover:bg-white hover:text-slate-900"
                aria-label="Copy this PC's code"
                onClick={() =>
                  void navigator.clipboard
                    ?.writeText(l.pc_code ?? "")
                    .then(() => setCopied(true))
                }
              >
                {copied ? (
                  <Check className="h-4 w-4 text-green-600" />
                ) : (
                  <Copy className="h-4 w-4" />
                )}
              </button>
            </div>
          ) : (
            <p className="mt-1 text-sm text-slate-500">
              Not available: start IntraForge from the Control Center on the
              shop PC.
            </p>
          )}
          <p className="mt-2 text-xs text-slate-500">
            To activate: send this PC&apos;s code and your serial number to your
            IntraForge supplier. They send back an activation code made for this
            PC only.
          </p>
        </div>

        {l.state !== "active" &&
          l.state !== "not_enforced" &&
          (l.can_activate ? (
            <form
              onSubmit={(e) => void activate(e)}
              className="flex flex-col gap-3"
            >
              <div>
                <Label htmlFor={ids.serial}>Serial number</Label>
                <Input
                  id={ids.serial}
                  className="font-mono uppercase"
                  placeholder="IFG-XXXX-XXXX-XXXX-XXXX-XXXX"
                  value={serial}
                  onChange={(e) => setSerial(e.target.value)}
                  required
                />
              </div>
              <div>
                <Label htmlFor={ids.code}>Activation code</Label>
                <textarea
                  id={ids.code}
                  className="h-24 w-full rounded-lg border border-slate-300 px-3 py-2 font-mono text-xs focus:border-brand-500 focus:ring-2 focus:ring-brand-500/20 focus:outline-none"
                  placeholder="IFA1...."
                  value={code}
                  onChange={(e) => setCode(e.target.value)}
                  required
                />
              </div>
              {error && <ErrorBanner message={error} />}
              <div className="flex justify-end gap-2">
                <Button
                  type="button"
                  variant="secondary"
                  onClick={() => {
                    setSerial("");
                    setCode("");
                    setError(null);
                  }}
                  disabled={busy}
                >
                  Clear
                </Button>
                <Button type="submit" disabled={busy}>
                  {busy ? "Activating..." : "Activate"}
                </Button>
              </div>
            </form>
          ) : (
            <p className="text-sm text-slate-500">
              Ask an administrator of this IntraForge to activate the licence.
            </p>
          ))}
      </Card>
    </div>
  );
}
