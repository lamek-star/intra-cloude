/**
 * The printed invoice: a complete, self-contained HTML page (every value escaped) for a print window, on A4 paper or on an
 * 80 mm / 58 mm receipt printer. Built from the sale's own records (SalesDocument.tsx); it changes nothing.
 */
import { canEncode128, code128Svg, escapeXml } from "./barcode";
import { withCurrency, type ShopDetails } from "./shop-details";

export type InvoicePaper = "a4" | "receipt80" | "receipt58";

export const PAPERS: Record<InvoicePaper, string> = {
  a4: "A4 page",
  receipt80: "Receipt printer, 80 mm",
  receipt58: "Receipt printer, 58 mm",
};

export type InvoiceLine = { number: string; name: string; quantity: string; unitPrice: string; total: string };

export type InvoiceData = {
  /** The invoice number, or empty for an order not yet invoiced. */
  number: string;
  date: string;
  /** "unpaid", "paid"... as recorded. */
  payment: string;
  customer: string;
  lines: InvoiceLine[];
  total: string;
  amountDue: string;
  /** "Part No." / "Item No.", and "Product" / "Medicine". */
  numberCaption: string;
  productWord: string;
  printedAt: string;
};

const e = escapeXml;

function shopBlock(shop: ShopDetails, centered: boolean): string {
  const lines = [shop.address, shop.phone ? `Tel. ${shop.phone}` : "", shop.taxId ? `Tax no. ${shop.taxId}` : ""].filter((l) => l.trim());
  return (
    `<div class="shop${centered ? " c" : ""}"><div class="shop-name">${e(shop.name || "Invoice")}</div>` +
    lines.map((l) => `<div>${e(l)}</div>`).join("") +
    `</div>`
  );
}

function barcode(number: string): string {
  return number && canEncode128(number) ? `<div class="code">${code128Svg(number)}<div>${e(number)}</div></div>` : "";
}

const BASE =
  `*{box-sizing:border-box}body{margin:0;color:#000;font-family:Arial,Helvetica,sans-serif}` +
  `.num{text-align:right;white-space:nowrap;font-variant-numeric:tabular-nums}.muted{color:#555}` +
  `.code{text-align:center;font-family:"Courier New",monospace;font-size:9pt;margin-top:4mm}.code svg{width:60mm;max-width:100%;height:10mm}`;

function a4(d: InvoiceData, shop: ShopDetails): string {
  const title = d.number ? "INVOICE" : "SALES ORDER";
  const rows = d.lines
    .map(
      (l, i) =>
        `<tr><td class="muted">${i + 1}</td><td class="mono">${e(l.number || "—")}</td><td>${e(l.name)}</td>` +
        `<td class="num">${e(l.quantity)}</td><td class="num">${e(l.unitPrice)}</td><td class="num">${e(l.total)}</td></tr>`,
    )
    .join("");
  const due = d.number ? d.amountDue : d.total;
  return (
    `<style>${BASE}@page{size:A4;margin:16mm 14mm}body{font-size:10pt}` +
    `.head{display:flex;justify-content:space-between;align-items:flex-start;gap:10mm;padding-bottom:6mm;border-bottom:2px solid #000}` +
    `.shop-name{font-size:18pt;font-weight:700;margin-bottom:1.5mm}.shop div{line-height:1.45}` +
    `.title{font-size:20pt;font-weight:700;letter-spacing:2px;text-align:right}.meta{margin-top:2mm;border-collapse:collapse;margin-left:auto}` +
    `.meta td{padding:.6mm 0 .6mm 6mm;text-align:right}.meta td:first-child{color:#555}` +
    `.bill{margin:7mm 0 5mm}.label{font-size:8pt;letter-spacing:1px;color:#555;text-transform:uppercase}.bill .who{font-size:12pt;font-weight:700;margin-top:1mm}` +
    `table.lines{width:100%;border-collapse:collapse}table.lines th{font-size:8pt;letter-spacing:.5px;text-transform:uppercase;text-align:left;color:#333;border-bottom:1.5px solid #000;padding:2mm 1.5mm}` +
    `table.lines th.num{text-align:right}table.lines td{padding:2.2mm 1.5mm;border-bottom:1px solid #ddd;vertical-align:top}.mono{font-family:"Courier New",monospace}` +
    `.totals{margin-top:5mm;margin-left:auto;width:75mm;border-collapse:collapse}.totals td{padding:1.4mm 1.5mm}` +
    `.totals tr.due td{font-size:13pt;font-weight:700;border-top:2px solid #000;padding-top:2.5mm}` +
    `.pay{display:inline-block;margin-top:2mm;padding:.8mm 3mm;border:1.5px solid #000;font-weight:700;letter-spacing:1px;text-transform:uppercase;font-size:9pt}` +
    `.foot{margin-top:12mm;display:flex;justify-content:space-between;align-items:flex-end;gap:10mm}.thanks{font-size:11pt;font-weight:700}` +
    `.printed{font-size:7.5pt;color:#777;margin-top:2mm}</style>` +
    `<div class="head">${shopBlock(shop, false)}<div><div class="title">${title}</div><table class="meta">` +
    (d.number ? `<tr><td>Invoice no.</td><td><b>${e(d.number)}</b></td></tr>` : "") +
    `<tr><td>Date</td><td>${e(d.date)}</td></tr>` +
    (d.payment ? `<tr><td>Payment</td><td>${e(d.payment)}</td></tr>` : "") +
    `</table></div></div>` +
    `<div class="bill"><div class="label">Bill to</div><div class="who">${e(d.customer || "—")}</div></div>` +
    `<table class="lines"><thead><tr><th>#</th><th>${e(d.numberCaption)}</th><th>${e(d.productWord)}</th><th class="num">Qty</th>` +
    `<th class="num">Unit price</th><th class="num">Amount</th></tr></thead><tbody>${rows}</tbody></table>` +
    `<table class="totals"><tr><td class="muted">Subtotal</td><td class="num">${e(withCurrency(d.total, shop.currency))}</td></tr>` +
    `<tr class="due"><td>${d.number ? "Amount due" : "Total"}</td><td class="num">${e(withCurrency(due, shop.currency))}</td></tr></table>` +
    (d.payment ? `<div style="text-align:right"><span class="pay">${e(d.payment)}</span></div>` : "") +
    `<div class="foot"><div><div class="thanks">${e(shop.footer)}</div><div class="printed">Printed ${e(d.printedAt)} · IntraForge</div></div>` +
    `${barcode(d.number)}</div>`
  );
}

function receipt(d: InvoiceData, shop: ShopDetails, width: 80 | 58): string {
  const small = width === 58;
  const rows = d.lines
    .map(
      (l) =>
        `<div class="item"><div class="iname">${e(l.name)}</div>` +
        (l.number ? `<div class="muted mono">${e(d.numberCaption)} ${e(l.number)}</div>` : "") +
        `<div class="row"><span>${e(l.quantity)} × ${e(l.unitPrice)}</span><span class="num">${e(l.total)}</span></div></div>`,
    )
    .join("");
  const due = d.number ? d.amountDue : d.total;
  return (
    `<style>${BASE}@page{size:${width}mm auto;margin:0}body{width:${width}mm;padding:3mm ${small ? 2 : 4}mm 6mm;font-size:${small ? 8 : 9}pt}` +
    `.shop.c{text-align:center}.shop-name{font-size:${small ? 11 : 13}pt;font-weight:700;margin-bottom:1mm}.shop div{line-height:1.35}` +
    `hr{border:0;border-top:1px dashed #000;margin:2.5mm 0}.row{display:flex;justify-content:space-between;gap:2mm}` +
    `.title{text-align:center;font-weight:700;letter-spacing:2px;margin:1mm 0}.item{margin-bottom:1.8mm}.iname{font-weight:700}` +
    `.mono{font-family:"Courier New",monospace;font-size:.9em}.due{font-size:${small ? 10 : 12}pt;font-weight:700}` +
    `.thanks{text-align:center;font-weight:700;margin-top:3mm}.printed{text-align:center;font-size:7pt;color:#555;margin-top:1mm}` +
    `.code svg{width:100%}</style>` +
    `${shopBlock(shop, true)}<hr><div class="title">${d.number ? "INVOICE" : "SALES ORDER"}</div>` +
    (d.number ? `<div class="row"><span>Invoice no.</span><b>${e(d.number)}</b></div>` : "") +
    `<div class="row"><span>Date</span><span>${e(d.date)}</span></div>` +
    `<div class="row"><span>Customer</span><span>${e(d.customer || "—")}</span></div><hr>${rows}<hr>` +
    `<div class="row due"><span>${d.number ? "AMOUNT DUE" : "TOTAL"}</span><span class="num">${e(withCurrency(due, shop.currency))}</span></div>` +
    (d.payment ? `<div class="row"><span>Payment</span><b>${e(d.payment.toUpperCase())}</b></div>` : "") +
    `<div class="thanks">${e(shop.footer)}</div>${barcode(d.number)}<div class="printed">Printed ${e(d.printedAt)}</div>`
  );
}

export function invoiceHtml(d: InvoiceData, paper: InvoicePaper, shop: ShopDetails): string {
  const body = paper === "a4" ? a4(d, shop) : receipt(d, shop, paper === "receipt58" ? 58 : 80);
  return `<!doctype html><html><head><meta charset="utf-8"><title>${e(d.number ? `Invoice ${d.number}` : "Sales order")}</title></head><body>${body}</body></html>`;
}
