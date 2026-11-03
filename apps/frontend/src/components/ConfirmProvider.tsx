"use client";

import { AlertTriangle } from "lucide-react";
import { createContext, useCallback, useContext, useId, useRef, useState, type ReactNode } from "react";
import { Button } from "@/components/ui";
import { useDialogA11y } from "@/lib/use-dialog-a11y";

type ConfirmOptions = {
  title: string;
  description?: string;
  confirmLabel?: string;
  /** Red confirm button for destructive actions (the common case here --
   * every current call site is a delete/remove/revoke). */
  danger?: boolean;
};

type ConfirmContextValue = (options: ConfirmOptions) => Promise<boolean>;

const ConfirmContext = createContext<ConfirmContextValue | null>(null);

/** Replaces every `window.confirm(...)` call site across the app
 * (Unit 7) with a styled, on-brand dialog -- same one-line-guard call
 * shape (`if (!(await confirm({...}))) return;`), just async and
 * consistent with the rest of the design system instead of a
 * browser-native, unstylable, thread-blocking prompt. Mounted once at
 * the AppShell level so any page can call `useConfirm()`. */
export function ConfirmProvider({ children }: { children: ReactNode }) {
  const [options, setOptions] = useState<ConfirmOptions | null>(null);
  const resolveRef = useRef<((value: boolean) => void) | null>(null);

  const confirm = useCallback<ConfirmContextValue>((opts) => {
    setOptions(opts);
    return new Promise<boolean>((resolve) => {
      resolveRef.current = resolve;
    });
  }, []);

  function settle(value: boolean) {
    setOptions(null);
    resolveRef.current?.(value);
    resolveRef.current = null;
  }

  return (
    <ConfirmContext.Provider value={confirm}>
      {children}
      {options && <ConfirmDialog options={options} onCancel={() => settle(false)} onConfirm={() => settle(true)} />}
    </ConfirmContext.Provider>
  );
}

function ConfirmDialog({
  options,
  onCancel,
  onConfirm,
}: {
  options: ConfirmOptions;
  onCancel: () => void;
  onConfirm: () => void;
}) {
  const panelRef = useRef<HTMLDivElement>(null);
  const titleId = useId();
  useDialogA11y(true, onCancel, panelRef);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-slate-900/40" onClick={onCancel} />
      <div
        ref={panelRef}
        role="alertdialog"
        aria-modal="true"
        aria-labelledby={titleId}
        tabIndex={-1}
        className="relative w-full max-w-sm rounded-2xl border border-slate-200 bg-white p-5 shadow-2xl outline-none"
      >
        <div className="flex items-start gap-3">
          {options.danger && (
            <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-red-50 text-red-600">
              <AlertTriangle className="h-4 w-4" />
            </span>
          )}
          <div className="min-w-0">
            <h2 id={titleId} className="text-sm font-semibold text-slate-900">
              {options.title}
            </h2>
            {options.description && <p className="mt-1.5 text-sm text-slate-500">{options.description}</p>}
          </div>
        </div>
        <div className="mt-5 flex justify-end gap-2">
          <Button variant="ghost" onClick={onCancel}>
            Cancel
          </Button>
          <Button variant={options.danger ? "danger" : "primary"} onClick={onConfirm}>
            {options.confirmLabel ?? "Confirm"}
          </Button>
        </div>
      </div>
    </div>
  );
}

export function useConfirm(): ConfirmContextValue {
  const ctx = useContext(ConfirmContext);
  if (!ctx) throw new Error("useConfirm must be used within ConfirmProvider");
  return ctx;
}
