"use client";

import { useId, useState } from "react";
import { Download, Printer } from "lucide-react";
import { canEncode128, code128Svg, escapeXml } from "@/lib/barcode";
import { downloadFiles, labelImages, labelPages } from "@/lib/label-image";
import { loadShopDetails, saveShopDetails } from "@/lib/shop-details";
import { Button, Input, Label, Modal, Select } from "@/components/ui";
import { useBusiness } from "./BusinessApp";

/** What one label shows: the number as a barcode and in text, the name, and the details that matter for the item. */
export type LabelData = {
  number: string;
  name: string;
  /** Short lines under the name: generic name and pack for a medicine, the part's description or unit for a spare part. */
  details: string[];
  price?: string;
  location?: string;
  /** "Rx" on a medicine that needs a prescription. */
  flag?: string;
};

export type LabelSize = "printer" | "sheet";

/** The shop's name at the top, and the caption in front of the number ("Part No.", "Item No."). */
export type LabelText = { shop: string; numberCaption: string };

const SIZES: Record<LabelSize, { label: string; css: string }> = {
  printer: {
    label: "Label printer, 50 × 30 mm",
    css: "@page{size:50mm 30mm;margin:0}.sheet{display:block}.label{width:50mm;height:30mm;page-break-after:always}",
  },
  sheet: {
    label: "A4 sheet, 3 × 8 labels (70 × 37 mm)",
    css: "@page{size:A4;margin:0}.sheet{display:grid;grid-template-columns:repeat(3,70mm);grid-auto-rows:37mm;justify-content:center;padding-top:0.5mm}.label{width:70mm;height:37mm}",
  },
};

/** "Part number" -> "Part No.", "Item number" -> "Item No.". */
export function numberCaption(word: string): string {
  return word.replace(/\s*number$/i, " No.");
}

/** The labels as a complete, self-contained HTML page (every value escaped), for a print window. */
export function labelsHtml(items: LabelData[], copies: number, size: LabelSize, text: LabelText = { shop: "", numberCaption: "No." }): string {
  const shop = text.shop.trim();
  const one = (item: LabelData) => {
    const barcode = canEncode128(item.number) ? `<div class="bars">${code128Svg(item.number)}</div>` : "";
    const details = item.details.filter(Boolean).map((d) => `<div class="detail">${escapeXml(d)}</div>`).join("");
    const bottom = [item.price ? escapeXml(item.price) : "", item.location ? escapeXml(item.location) : ""].filter(Boolean).join(" · ");
    const top =
      shop || item.flag
        ? `<div class="top"><span class="shop">${escapeXml(shop.toUpperCase())}</span>` +
          (item.flag ? `<span class="flag">${escapeXml(item.flag)}</span>` : "") +
          `</div>`
        : "";
    return (
      `<div class="label">${top}<div class="name">${escapeXml(item.name)}</div>${details}${barcode}` +
      `<div class="number"><span class="caption">${escapeXml(text.numberCaption)}</span> ${escapeXml(item.number)}</div>` +
      (bottom ? `<div class="bottom">${bottom}</div>` : "") +
      `</div>`
    );
  };
  const labels = items.flatMap((item) => Array.from({ length: Math.max(1, Math.min(copies, 200)) }, () => one(item))).join("");
  return (
    `<!doctype html><html><head><meta charset="utf-8"><title>Labels</title><style>` +
    `*{box-sizing:border-box}body{margin:0;font-family:Arial,Helvetica,sans-serif;color:#000}` +
    `.label{padding:1.6mm 2.5mm;overflow:hidden;display:flex;flex-direction:column;gap:.35mm}` +
    `.top{display:flex;justify-content:space-between;align-items:flex-start;gap:1mm}` +
    `.shop{font-weight:700;font-size:5.8pt;letter-spacing:.3px;color:#333;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}` +
    `.name{font-weight:700;font-size:8.5pt;line-height:1.12;overflow:hidden;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical}` +
    `.flag{font-weight:700;font-size:8pt;border:1px solid #000;padding:0 1mm;line-height:1.15}` +
    `.detail{font-size:6.5pt;line-height:1.15;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}` +
    `.bars{height:9mm;min-height:3mm;margin-top:auto;flex-shrink:1}.bars svg{width:100%;height:100%}` +
    `.number{font-family:"Courier New",monospace;font-weight:700;font-size:7.5pt;text-align:center;letter-spacing:.3px;white-space:nowrap;overflow:hidden}` +
    `.caption{font-family:Arial,Helvetica,sans-serif;font-weight:400;font-size:6.5pt}` +
    `.bottom{font-size:7pt;font-weight:700;display:flex;justify-content:center;gap:1mm}` +
    `${SIZES[size].css}</style></head><body><div class="sheet">${labels}</div></body></html>`
  );
}

/** Opens the labels in their own window and asks the browser to print them. */
export function printLabels(items: LabelData[], copies: number, size: LabelSize, text: LabelText): boolean {
  const win = window.open("", "_blank", "width=480,height=640");
  if (!win) return false;
  win.document.open();
  win.document.write(labelsHtml(items, copies, size, text));
  win.document.close();
  win.focus();
  win.setTimeout(() => win.print(), 250);
  return true;
}

export function PrintLabelsButton({ items, disabledReason, caption }: { items: LabelData[]; disabledReason?: string; caption: string }) {
  const { instance } = useBusiness();
  const [open, setOpen] = useState(false);
  const [copies, setCopies] = useState("1");
  const [size, setSize] = useState<LabelSize>("printer");
  const [shop, setShop] = useState(() => loadShopDetails(instance.id, instance.label).name);
  const [message, setMessage] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const ids = { copies: useId(), size: useId(), shop: useId() };
  const first = items[0];
  const text: LabelText = { shop, numberCaption: caption };
  const count = Math.max(1, Math.min(Number(copies) || 1, 200));

  function remember() {
    saveShopDetails(instance.id, { ...loadShopDetails(instance.id, instance.label), name: shop.trim() });
  }

  async function download() {
    setBusy(true);
    setMessage(null);
    try {
      remember();
      const files = await labelImages(items, count, size, text);
      downloadFiles(files);
      setMessage(files.length === 1 ? `Saved ${files[0][0]} to your Downloads.` : `Saved ${files.length} pictures to your Downloads.`);
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "The picture could not be made.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <Button variant="secondary" onClick={() => setOpen(true)} disabled={!first} title={!first ? disabledReason : undefined}>
        <Printer className="h-4 w-4" aria-hidden="true" />
        Print label
      </Button>
      {open && first && (
        <Modal open onClose={() => setOpen(false)} title="Print labels">
          <div className="flex flex-col gap-4">
            <div className="mx-auto w-full max-w-[16rem] rounded border border-slate-300 bg-white p-2 text-black shadow-sm" aria-label="Label preview">
              {(shop.trim() || first.flag) && (
                <div className="flex items-start justify-between gap-2">
                  <span className="truncate text-[9px] font-bold tracking-wide text-slate-700 uppercase">{shop.trim()}</span>
                  {first.flag && <span className="h-fit border border-black px-1 text-[10px] font-bold">{first.flag}</span>}
                </div>
              )}
              <div className="line-clamp-2 text-xs leading-tight font-bold">{first.name}</div>
              {first.details.filter(Boolean).map((d) => (
                <div key={d} className="truncate text-[10px] leading-tight">
                  {d}
                </div>
              ))}
              {canEncode128(first.number) ? (
                <div className="mt-1 h-9 [&>svg]:h-full [&>svg]:w-full" dangerouslySetInnerHTML={{ __html: code128Svg(first.number) }} />
              ) : (
                <p className="mt-1 text-[10px] text-amber-700">This number has characters a barcode cannot hold; the label shows it as text.</p>
              )}
              <div className="text-center font-mono text-[11px] font-bold">
                <span className="font-sans text-[10px] font-normal">{caption}</span> {first.number}
              </div>
              {(first.price || first.location) && (
                <div className="text-center text-[10px] font-bold">{[first.price, first.location].filter(Boolean).join(" · ")}</div>
              )}
            </div>
            <div>
              <Label htmlFor={ids.shop}>Shop name on the label</Label>
              <Input id={ids.shop} value={shop} maxLength={60} placeholder="Leave empty for no shop name" onChange={(e) => setShop(e.target.value)} />
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
            <p className="text-xs text-text-muted">
              {size === "printer"
                ? "Download image saves one 50 × 30 mm picture (300 dpi) for each label; your label printer prints the copies."
                : `Download image saves ${labelPages(items.length * count, "sheet")} A4 page${labelPages(items.length * count, "sheet") === 1 ? "" : "s"} (300 dpi) with ${items.length * count} label${items.length * count === 1 ? "" : "s"}.`}
            </p>
            {message && (
              <p className="text-sm text-slate-700" role="status">
                {message}
              </p>
            )}
            <div className="flex flex-wrap justify-end gap-2">
              <Button variant="secondary" onClick={() => setOpen(false)}>
                Cancel
              </Button>
              <Button variant="secondary" onClick={() => void download()} disabled={busy}>
                <Download className="h-4 w-4" aria-hidden="true" />
                {busy ? "Making the picture..." : "Download image"}
              </Button>
              <Button
                onClick={() => {
                  remember();
                  const ok = printLabels(items, count, size, text);
                  if (ok) setOpen(false);
                  else setMessage("The browser blocked the print window. Allow pop-ups for IntraForge and try again.");
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
