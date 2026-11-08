"use client";

import { useId, useState } from "react";
import { Printer } from "lucide-react";
import { canEncode128, code128Svg, escapeXml } from "@/lib/barcode";
import { Button, Input, Label, Modal, Select } from "@/components/ui";

/** What one label shows: the number as a barcode and in text, the name, and the details that matter for the item. */
export type LabelData = {
  number: string;
  name: string;
  /** Short lines under the name: generic name and pack for a medicine, the part's brand or unit for a spare part. */
  details: string[];
  price?: string;
  location?: string;
  /** "Rx" on a medicine that needs a prescription. */
  flag?: string;
};

export type LabelSize = "printer" | "sheet";

const SIZES: Record<LabelSize, { label: string; css: string }> = {
  printer: {
    label: "Label printer, 50 × 30 mm",
    css: "@page{size:50mm 30mm;margin:0}.sheet{display:block}.label{width:50mm;height:30mm;page-break-after:always}",
  },
  sheet: {
    label: "A4 sheet, 3 × 8 labels (70 × 37 mm)",
    css: "@page{size:A4;margin:8mm 0}.sheet{display:grid;grid-template-columns:repeat(3,70mm);grid-auto-rows:37mm;justify-content:center}.label{width:70mm;height:37mm}",
  },
};

/** The labels as a complete, self-contained HTML page (every value escaped), for a print window. */
export function labelsHtml(items: LabelData[], copies: number, size: LabelSize): string {
  const one = (item: LabelData) => {
    const barcode = canEncode128(item.number)
      ? `<div class="bars">${code128Svg(item.number)}</div>`
      : "";
    const details = item.details.filter(Boolean).map((d) => `<div class="detail">${escapeXml(d)}</div>`).join("");
    const bottom = [item.price ? `<b>${escapeXml(item.price)}</b>` : "", item.location ? escapeXml(item.location) : ""]
      .filter(Boolean)
      .join(" · ");
    return (
      `<div class="label"><div class="top"><span class="name">${escapeXml(item.name)}</span>` +
      (item.flag ? `<span class="flag">${escapeXml(item.flag)}</span>` : "") +
      `</div>${details}${barcode}<div class="number">${escapeXml(item.number)}</div>` +
      (bottom ? `<div class="bottom">${bottom}</div>` : "") +
      `</div>`
    );
  };
  const labels = items.flatMap((item) => Array.from({ length: Math.max(1, Math.min(copies, 200)) }, () => one(item))).join("");
  return (
    `<!doctype html><html><head><meta charset="utf-8"><title>Labels</title><style>` +
    `*{box-sizing:border-box}body{margin:0;font-family:Arial,Helvetica,sans-serif;color:#000}` +
    `.label{padding:1.5mm 2.5mm;overflow:hidden;display:flex;flex-direction:column;gap:.4mm}` +
    `.top{display:flex;justify-content:space-between;gap:1mm}.name{font-weight:700;font-size:8.5pt;line-height:1.1;` +
    `overflow:hidden;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical}` +
    `.flag{font-weight:700;font-size:8pt;border:1px solid #000;padding:0 1mm;height:fit-content}` +
    `.detail{font-size:6.5pt;line-height:1.15;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}` +
    `.bars{height:9mm;margin-top:auto}.bars svg{width:100%;height:100%}` +
    `.number{font-family:monospace;font-size:7.5pt;text-align:center;letter-spacing:.3px}` +
    `.bottom{font-size:7pt;display:flex;justify-content:center;gap:1mm}` +
    `${SIZES[size].css}</style></head><body><div class="sheet">${labels}</div></body></html>`
  );
}

/** Opens the labels in their own window and asks the browser to print them. */
export function printLabels(items: LabelData[], copies: number, size: LabelSize): boolean {
  const win = window.open("", "_blank", "width=480,height=640");
  if (!win) return false;
  win.document.open();
  win.document.write(labelsHtml(items, copies, size));
  win.document.close();
  win.focus();
  win.setTimeout(() => win.print(), 250);
  return true;
}

export function PrintLabelsButton({ items, disabledReason }: { items: LabelData[]; disabledReason?: string }) {
  const [open, setOpen] = useState(false);
  const [copies, setCopies] = useState("1");
  const [size, setSize] = useState<LabelSize>("printer");
  const [blocked, setBlocked] = useState(false);
  const ids = { copies: useId(), size: useId() };
  const first = items[0];

  return (
    <>
      <Button variant="secondary" onClick={() => setOpen(true)} disabled={!first} title={!first ? disabledReason : undefined}>
        <Printer className="h-4 w-4" aria-hidden="true" />
        Print label
      </Button>
      {open && first && (
        <Modal open onClose={() => setOpen(false)} title="Print labels">
          <div className="flex flex-col gap-4">
            <div
              className="mx-auto w-full max-w-[16rem] rounded border border-slate-300 bg-white p-2 text-black"
              aria-label="Label preview"
            >
              <div className="flex justify-between gap-2">
                <span className="line-clamp-2 text-xs font-bold leading-tight">{first.name}</span>
                {first.flag && <span className="h-fit border border-black px-1 text-[10px] font-bold">{first.flag}</span>}
              </div>
              {first.details.filter(Boolean).map((d) => (
                <div key={d} className="truncate text-[10px] leading-tight">
                  {d}
                </div>
              ))}
              {canEncode128(first.number) ? (
                <div className="mt-1 h-9" dangerouslySetInnerHTML={{ __html: code128Svg(first.number) }} />
              ) : (
                <p className="mt-1 text-[10px] text-amber-700">This number has characters a barcode cannot hold; the label shows it as text.</p>
              )}
              <div className="text-center font-mono text-[11px]">{first.number}</div>
              {(first.price || first.location) && (
                <div className="text-center text-[10px]">{[first.price, first.location].filter(Boolean).join(" · ")}</div>
              )}
            </div>
            <div className="grid gap-3 sm:grid-cols-2">
              <div>
                <Label htmlFor={ids.copies}>Copies</Label>
                <Input id={ids.copies} type="number" min={1} max={200} value={copies} onChange={(e) => setCopies(e.target.value)} />
              </div>
              <div>
                <Label htmlFor={ids.size}>Labels</Label>
                <Select id={ids.size} value={size} onChange={(e) => setSize(e.target.value as LabelSize)}>
                  {(Object.keys(SIZES) as LabelSize[]).map((s) => (
                    <option key={s} value={s}>
                      {SIZES[s].label}
                    </option>
                  ))}
                </Select>
              </div>
            </div>
            {blocked && <p className="text-sm text-amber-700">The browser blocked the print window. Allow pop-ups for IntraForge and try again.</p>}
            <div className="flex justify-end gap-2">
              <Button variant="secondary" onClick={() => setOpen(false)}>
                Cancel
              </Button>
              <Button
                onClick={() => {
                  const ok = printLabels(items, Number(copies) || 1, size);
                  setBlocked(!ok);
                  if (ok) setOpen(false);
                }}
              >
                <Printer className="h-4 w-4" aria-hidden="true" />
                Print
              </Button>
            </div>
          </div>
        </Modal>
      )}
    </>
  );
}
