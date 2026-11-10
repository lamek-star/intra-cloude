"use client";

import { useId, useRef, useState } from "react";
import { Printer, X } from "lucide-react";
import { invoiceHtml, PAPERS, type InvoiceData, type InvoicePaper } from "@/lib/invoice";
import { loadShopDetails, saveShopDetails, type ShopDetails } from "@/lib/shop-details";
import { useDialogA11y } from "@/lib/use-dialog-a11y";
import { Button, Input, Label, Select } from "@/components/ui";
import { useBusiness } from "./BusinessApp";

const PAPER_KEY = "intraforge.invoice-paper";

function savedPaper(): InvoicePaper {
  try {
    const p = window.localStorage.getItem(PAPER_KEY);
    return p === "receipt80" || p === "receipt58" || p === "a4" ? p : "a4";
  } catch {
    return "a4";
  }
}

/** Opens the invoice in its own window and asks the browser to print it (or save it as a PDF). */
export function printInvoice(html: string): boolean {
  const win = window.open("", "_blank", "width=820,height=960");
  if (!win) return false;
  win.document.open();
  win.document.write(html);
  win.document.close();
  win.focus();
  win.setTimeout(() => win.print(), 300);
  return true;
}

/** "Print invoice": choose the paper, fill in the shop's details once, see the invoice exactly as it prints. */
export function PrintInvoiceButton({ data, autoOpen = false }: { data: InvoiceData | null; autoOpen?: boolean }) {
  const [open, setOpen] = useState(autoOpen);
  return (
    <>
      <Button onClick={() => setOpen(true)} disabled={!data}>
        <Printer className="h-4 w-4" aria-hidden="true" />
        Print invoice
      </Button>
      {open && data && <InvoiceDialog data={data} onClose={() => setOpen(false)} />}
    </>
  );
}

function InvoiceDialog({ data, onClose }: { data: InvoiceData; onClose: () => void }) {
  const { instance } = useBusiness();
  const [paper, setPaper] = useState<InvoicePaper>(savedPaper);
  const [shop, setShop] = useState<ShopDetails>(() => loadShopDetails(instance.id, instance.label));
  const [blocked, setBlocked] = useState(false);
  const panelRef = useRef<HTMLDivElement>(null);
  const titleId = useId();
  const ids = { paper: useId(), name: useId(), address: useId(), phone: useId(), tax: useId(), currency: useId(), footer: useId() };
  useDialogA11y(true, onClose, panelRef);
  const html = invoiceHtml(data, paper, shop);
  const set = (k: keyof ShopDetails) => (e: React.ChangeEvent<HTMLInputElement>) => setShop({ ...shop, [k]: e.target.value });

  function print() {
    saveShopDetails(instance.id, shop);
    try {
      window.localStorage.setItem(PAPER_KEY, paper);
    } catch {
      /* the choice applies to this print only */
    }
    const ok = printInvoice(html);
    setBlocked(!ok);
    if (ok) onClose();
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="dialog-backdrop absolute inset-0 bg-slate-900/40" onClick={onClose} />
      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        tabIndex={-1}
        className="dialog-panel relative flex max-h-[92vh] w-full max-w-5xl flex-col overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-2xl outline-none"
      >
        <div className="flex items-center justify-between border-b border-slate-200 px-5 py-3">
          <h2 id={titleId} className="text-sm font-semibold text-slate-900">
            Print {data.number ? `invoice ${data.number}` : "sales order"}
          </h2>
          <button onClick={onClose} aria-label="Close" className="rounded-lg p-1.5 text-slate-500 hover:bg-slate-100 hover:text-slate-900">
            <X className="h-4 w-4" />
          </button>
        </div>
        <div className="grid min-h-0 flex-1 overflow-y-auto md:grid-cols-[300px_1fr]">
          <div className="flex flex-col gap-3 border-b border-slate-200 p-5 md:border-r md:border-b-0">
            <div>
              <Label htmlFor={ids.paper}>Paper</Label>
              <Select id={ids.paper} value={paper} onChange={(e) => setPaper(e.target.value as InvoicePaper)}>
                {(Object.keys(PAPERS) as InvoicePaper[]).map((p) => (
                  <option key={p} value={p}>
                    {PAPERS[p]}
                  </option>
                ))}
              </Select>
            </div>
            <p className="mt-1 text-xs font-semibold tracking-wide text-slate-500 uppercase">Shop details on the invoice</p>
            <div>
              <Label htmlFor={ids.name}>Shop name</Label>
              <Input id={ids.name} value={shop.name} maxLength={80} onChange={set("name")} />
            </div>
            <div>
              <Label htmlFor={ids.address}>Address</Label>
              <Input id={ids.address} value={shop.address} maxLength={160} onChange={set("address")} placeholder="Street, city" />
            </div>
            <div className="grid grid-cols-2 gap-2">
              <div>
                <Label htmlFor={ids.phone}>Phone</Label>
                <Input id={ids.phone} value={shop.phone} maxLength={40} onChange={set("phone")} />
              </div>
              <div>
                <Label htmlFor={ids.currency}>Currency</Label>
                <Input id={ids.currency} value={shop.currency} maxLength={8} onChange={set("currency")} placeholder="e.g. ERN" />
              </div>
            </div>
            <div>
              <Label htmlFor={ids.tax}>Tax number</Label>
              <Input id={ids.tax} value={shop.taxId} maxLength={40} onChange={set("taxId")} placeholder="Optional" />
            </div>
            <div>
              <Label htmlFor={ids.footer}>Note at the bottom</Label>
              <Input id={ids.footer} value={shop.footer} maxLength={160} onChange={set("footer")} />
            </div>
            <p className="text-xs text-text-muted">The shop details are remembered on this computer for every invoice and label.</p>
          </div>
          <div className="flex min-h-[420px] flex-col bg-slate-100 p-4">
            <p className="mb-2 text-xs font-medium text-slate-500">Preview, exactly as it prints</p>
            <div className="flex flex-1 justify-center overflow-auto">
              <iframe
                title="Invoice preview"
                sandbox=""
                srcDoc={html}
                className={`rounded bg-white shadow-md ${paper === "a4" ? "h-[620px] w-full max-w-[560px]" : paper === "receipt80" ? "h-[620px] w-[320px]" : "h-[620px] w-[240px]"}`}
              />
            </div>
          </div>
        </div>
        <div className="flex flex-wrap items-center justify-end gap-2 border-t border-slate-200 px-5 py-3">
          {blocked && <p className="mr-auto text-sm text-amber-700">The browser blocked the print window. Allow pop-ups for IntraForge and try again.</p>}
          <span className="mr-auto hidden text-xs text-text-muted sm:inline">To keep a PDF, choose &quot;Save as PDF&quot; as the printer.</span>
          <Button variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button onClick={print}>
            <Printer className="h-4 w-4" aria-hidden="true" />
            Print
          </Button>
        </div>
      </div>
    </div>
  );
}
