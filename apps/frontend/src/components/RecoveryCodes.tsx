"use client";

import { Button, CopyButton } from "@/components/ui";

/** Recovery codes, shown once: copy them, download them, or print them, and keep them somewhere safe. */
export function RecoveryCodesBox({ codes, onClose }: { codes: string[]; onClose: () => void }) {
  const text = `IntraForge recovery codes (each works once)\n\n${codes.join("\n")}\n`;
  return (
    <div role="region" aria-label="Recovery codes" className="space-y-3 rounded-lg border border-amber-300 bg-amber-50 p-4">
      <p className="text-sm font-semibold text-amber-900">Save your recovery codes now</p>
      <p className="text-sm text-amber-900">
        If you lose your phone, each of these signs you in once instead of a code from the app. They are shown only
        now: keep them somewhere safe, not on the phone.
      </p>
      <ul className="grid grid-cols-2 gap-1 font-mono text-sm text-slate-900 sm:grid-cols-5">
        {codes.map((c) => (
          <li key={c}>{c}</li>
        ))}
      </ul>
      <div className="flex flex-wrap gap-2">
        <CopyButton value={codes.join("\n")} label="Copy" />
        <a
          href={`data:text/plain;charset=utf-8,${encodeURIComponent(text)}`}
          download="intraforge-recovery-codes.txt"
          className="inline-flex items-center rounded-lg border border-border-subtle px-2.5 py-1.5 text-xs font-medium text-slate-700 hover:bg-white"
        >
          Download
        </a>
        <Button size="sm" variant="ghost" onClick={onClose}>
          I have saved them
        </Button>
      </div>
    </div>
  );
}
