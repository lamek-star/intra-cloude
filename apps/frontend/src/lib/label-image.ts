/**
 * Labels as PNG pictures, drawn on a canvas at 300 dpi with the same layout as the printed labels (Labels.tsx): the shop
 * name, the product name, its details, the barcode, the captioned number, price and shelf. For a label printer's own
 * software, a print shop, or sending by phone.
 */
import { canEncode128, code128Modules } from "./barcode";

export type ImageLabel = { number: string; name: string; details: string[]; price?: string; location?: string; flag?: string };
export type LabelSheet = "printer" | "sheet";
export type LabelOptions = { shop: string; numberCaption: string };

const DPI = 300;
const MM = DPI / 25.4;
const PT = DPI / 72;

export const SHEET = { pageW: 210, pageH: 297, cols: 3, rows: 8, labelW: 70, labelH: 37 };
export const PRINTER = { labelW: 50, labelH: 30 };

/** How many pictures the labels make: one per label for a label printer, one per A4 page of 24 for sheets. */
export function labelPages(count: number, sheet: LabelSheet): number {
  if (count <= 0) return 0;
  return sheet === "printer" ? count : Math.ceil(count / (SHEET.cols * SHEET.rows));
}

function fit(ctx: CanvasRenderingContext2D, text: string, width: number): string {
  if (ctx.measureText(text).width <= width) return text;
  let t = text;
  while (t.length > 1 && ctx.measureText(`${t}…`).width > width) t = t.slice(0, -1);
  return `${t.trimEnd()}…`;
}

function wrap(ctx: CanvasRenderingContext2D, text: string, width: number, maxLines: number): string[] {
  const words = text.split(/\s+/).filter(Boolean);
  const lines: string[] = [];
  let line = "";
  for (let i = 0; i < words.length; i++) {
    const attempt = line ? `${line} ${words[i]}` : words[i];
    if (ctx.measureText(attempt).width <= width || !line) line = attempt;
    else {
      lines.push(line);
      line = words[i];
      if (lines.length === maxLines - 1) {
        line = words.slice(i).join(" ");
        break;
      }
    }
  }
  if (line) lines.push(line);
  return lines.slice(0, maxLines).map((l, i, all) => (i === all.length - 1 ? fit(ctx, l, width) : l));
}

/** Draws one label with its top-left corner at (x, y) in pixels, `w` x `h` millimetres. */
export function drawLabel(ctx: CanvasRenderingContext2D, item: ImageLabel, x: number, y: number, w: number, h: number, opts: LabelOptions) {
  const padX = 2.5 * MM;
  const padY = 1.6 * MM;
  const left = x + padX;
  const width = w * MM - 2 * padX;
  const bottom = y + h * MM - padY;
  ctx.fillStyle = "#fff";
  ctx.fillRect(x, y, w * MM, h * MM);
  ctx.fillStyle = "#000";
  ctx.textBaseline = "top";
  let cy = y + padY;

  // Shop name and the Rx flag
  let flagW = 0;
  if (item.flag) {
    ctx.font = `bold ${8 * PT}px Arial, Helvetica, sans-serif`;
    flagW = ctx.measureText(item.flag).width + 2 * MM;
    ctx.lineWidth = 0.25 * MM;
    ctx.strokeStyle = "#000"; // a sheet's cut guides are grey; the flag's box is not
    ctx.strokeRect(x + w * MM - padX - flagW, cy, flagW, 8 * PT * 1.15);
    ctx.fillText(item.flag, x + w * MM - padX - flagW + MM, cy + 0.6 * PT);
  }
  if (opts.shop.trim()) {
    ctx.font = `bold ${5.8 * PT}px Arial, Helvetica, sans-serif`;
    ctx.fillStyle = "#333";
    ctx.fillText(fit(ctx, opts.shop.trim().toUpperCase(), width - flagW - MM), left, cy);
    ctx.fillStyle = "#000";
    cy += 5.8 * PT * 1.3;
  }

  // Name (up to two lines), then the details
  ctx.font = `bold ${8.5 * PT}px Arial, Helvetica, sans-serif`;
  const nameLines = wrap(ctx, item.name, width - (opts.shop.trim() ? 0 : flagW + MM), 2);
  for (const line of nameLines) {
    ctx.fillText(line, left, cy);
    cy += 8.5 * PT * 1.12;
  }
  ctx.font = `${6.5 * PT}px Arial, Helvetica, sans-serif`;
  const room = nameLines.length > 1 ? 1 : 2;
  for (const d of item.details.filter(Boolean).slice(0, room)) {
    ctx.fillText(fit(ctx, d, width), left, cy);
    cy += 6.5 * PT * 1.15;
  }

  // From the bottom up: price and shelf, the captioned number, the barcode in the space left
  let by = bottom;
  const bottomLine = [item.price, item.location].filter(Boolean).join(" · ");
  ctx.textAlign = "center";
  if (bottomLine) {
    ctx.font = `bold ${7 * PT}px Arial, Helvetica, sans-serif`;
    by -= 7 * PT * 1.1;
    ctx.fillText(fit(ctx, bottomLine, width), x + (w * MM) / 2, by);
  }
  ctx.font = `bold ${7.5 * PT}px "Courier New", monospace`;
  by -= 7.5 * PT * 1.15;
  ctx.fillText(fit(ctx, `${opts.numberCaption} ${item.number}`, width), x + (w * MM) / 2, by);
  ctx.textAlign = "left";
  if (canEncode128(item.number)) {
    const barH = Math.min(9 * MM, by - cy - 0.8 * MM);
    if (barH > 3 * MM) {
      const modules = code128Modules(item.number);
      const total = modules.reduce((a, b) => a + b, 0) + 20;
      const unit = width / total;
      let bx = left + 10 * unit;
      modules.forEach((m, i) => {
        if (i % 2 === 0) ctx.fillRect(bx, by - 0.6 * MM - barH, m * unit, barH);
        bx += m * unit;
      });
    }
  }
}

function canvasBlob(canvas: HTMLCanvasElement): Promise<Blob> {
  return new Promise((resolve, reject) => canvas.toBlob((b) => (b ? resolve(b) : reject(new Error("The picture could not be made."))), "image/png"));
}

/** The pictures, ready to download: [file name, PNG] pairs. */
export async function labelImages(items: ImageLabel[], copies: number, sheet: LabelSheet, opts: LabelOptions): Promise<[string, Blob][]> {
  const all = items.flatMap((item) => Array.from({ length: Math.max(1, Math.min(copies, 200)) }, () => item));
  const safe = (s: string) => s.replace(/[^0-9A-Za-z._-]+/g, "_").slice(0, 40) || "label";
  const files: [string, Blob][] = [];
  if (sheet === "printer") {
    // One picture per different label (copies are the printer's job).
    for (const item of items) {
      const canvas = document.createElement("canvas");
      canvas.width = Math.round(PRINTER.labelW * MM);
      canvas.height = Math.round(PRINTER.labelH * MM);
      const ctx = canvas.getContext("2d");
      if (!ctx) throw new Error("This browser cannot draw pictures.");
      drawLabel(ctx, item, 0, 0, PRINTER.labelW, PRINTER.labelH, opts);
      files.push([`label-${safe(item.number)}.png`, await canvasBlob(canvas)]);
    }
    return files;
  }
  const perPage = SHEET.cols * SHEET.rows;
  const left = ((SHEET.pageW - SHEET.cols * SHEET.labelW) / 2) * MM;
  const top = ((SHEET.pageH - SHEET.rows * SHEET.labelH) / 2) * MM;
  for (let page = 0; page < labelPages(all.length, "sheet"); page++) {
    const canvas = document.createElement("canvas");
    canvas.width = Math.round(SHEET.pageW * MM);
    canvas.height = Math.round(SHEET.pageH * MM);
    const ctx = canvas.getContext("2d");
    if (!ctx) throw new Error("This browser cannot draw pictures.");
    ctx.fillStyle = "#fff";
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    all.slice(page * perPage, (page + 1) * perPage).forEach((item, i) => {
      const x = left + (i % SHEET.cols) * SHEET.labelW * MM;
      const y = top + Math.floor(i / SHEET.cols) * SHEET.labelH * MM;
      drawLabel(ctx, item, x, y, SHEET.labelW, SHEET.labelH, opts);
      // Light cut guides, as on a pre-cut label sheet
      ctx.strokeStyle = "#d4d4d4";
      ctx.lineWidth = 1;
      ctx.strokeRect(x + 0.5, y + 0.5, SHEET.labelW * MM - 1, SHEET.labelH * MM - 1);
    });
    files.push([`labels-page-${page + 1}.png`, await canvasBlob(canvas)]);
  }
  return files;
}

/** Saves each picture through the browser's normal download. */
export function downloadFiles(files: [string, Blob][]) {
  files.forEach(([name, blob], i) => {
    const url = URL.createObjectURL(blob);
    window.setTimeout(() => {
      const a = document.createElement("a");
      a.href = url;
      a.download = name;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.setTimeout(() => URL.revokeObjectURL(url), 4000);
    }, i * 350);
  });
}
