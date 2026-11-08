/**
 * Importing a medicines catalogue (a CSV such as netmeds' medicines.csv: disease_name, med_name, med_url, final_price,
 * price, prescription_required, drug_varient, drug_manufacturer, drug_manufacturer_origin, drug_content, generic_name,
 * img_urls) into the Pharmacy.
 *
 * The file is read as a stream (the full catalogue is ~240 MB, mostly descriptions), one row at a time, keeping only the
 * facts: name, generic name, pack, manufacturer, origin, prescription, what it is listed for, the catalogue's price as a
 * *reference* price, links to its pictures and the page it came from. The long descriptions are not imported -- they
 * are the catalogue's own writing, not facts about the medicine. The shop's selling price stays empty unless the
 * person gives an exchange rate. A medicine listed under several diseases is one medicine.
 */

export type Medicine = {
  key: string;
  name: string;
  generic_name: string;
  pack: string;
  manufacturer: string;
  country_of_origin: string;
  prescription_required: boolean;
  used_for: string[];
  reference_price: string | null;
  image_links: string[];
  source_url: string;
  /** The item number its label carries, from the catalogue's own product id ("NM-847249"), or null. */
  item_number: string | null;
};

/** Splits CSV text that arrives in chunks into rows (RFC 4180: quoted fields, "" inside quotes, line breaks in quotes). */
export class CsvStream {
  private field = "";
  private row: string[] = [];
  private quoted = false;
  private quoteSeen = false;

  push(chunk: string, onRow: (row: string[]) => void): void {
    for (let i = 0; i < chunk.length; i++) {
      const c = chunk[i];
      if (this.quoted) {
        if (this.quoteSeen) {
          this.quoteSeen = false;
          if (c === '"') {
            this.field += '"';
            continue;
          }
          this.quoted = false; // the quote closed the field; fall through to handle c
        } else if (c === '"') {
          this.quoteSeen = true;
          continue;
        } else {
          this.field += c;
          continue;
        }
      }
      if (c === '"' && this.field === "") this.quoted = true;
      else if (c === ",") this.endField();
      else if (c === "\n") this.endRow(onRow);
      else if (c !== "\r") this.field += c;
    }
  }

  end(onRow: (row: string[]) => void): void {
    if (this.quoteSeen) this.quoted = false;
    if (this.field !== "" || this.row.length) this.endRow(onRow);
  }

  private endField() {
    this.row.push(this.field);
    this.field = "";
  }

  private endRow(onRow: (row: string[]) => void) {
    this.endField();
    const row = this.row;
    this.row = [];
    if (!(row.length === 1 && row[0] === "")) onRow(row);
  }
}

const strip = (value: string | undefined, prefix: RegExp) => (value ?? "").replace(prefix, "").replace(/\s+/g, " ").trim();

/** "₹335.68", "MRP ₹ 275.15", "MRP ₹381.46  Save 12 %" -> "335.68" / "275.15" / "381.46". */
export function parseRupees(value: string | undefined): string | null {
  const match = (value ?? "").replace(/,/g, "").match(/₹\s*([0-9]+(?:\.[0-9]{1,2})?)/);
  return match ? Number(match[1]).toFixed(2) : null;
}

export function itemNumberFrom(imageLinks: string[], url: string): string | null {
  for (const link of imageLinks) {
    const id = link.match(/\/product-v1\/\d+x\d+\/(\d+)\//);
    if (id) return `NM-${id[1]}`;
  }
  const tail = url.match(/[?&/](\d{4,})(?:$|[/?#])/);
  return tail ? `NM-${tail[1]}` : null;
}

/** One catalogue row as a medicine, or null when it has no name. */
export function medicineFromRow(row: Record<string, string>): Medicine | null {
  const name = strip(row.med_name, /^$/);
  if (!name) return null;
  const images = (row.img_urls ?? "")
    .split(",")
    .map((s) => s.trim())
    .filter((s) => /^https:\/\/[^\s"'<>]+$/.test(s))
    .slice(0, 6);
  const source = /^https?:\/\/\S+$/.test((row.med_url ?? "").trim()) ? row.med_url.trim() : "";
  const country = strip(row.drug_manufacturer_origin, /^\*?\s*Country of Origin:\s*/i);
  const disease = strip(row.disease_name, /\s*\(\d+\)\s*$/);
  return {
    key: source || name.toLowerCase(),
    name: name.slice(0, 200),
    generic_name: strip(row.generic_name, /^Generic Name\s*/i).slice(0, 250),
    pack: strip(row.drug_varient, /^\*\s*/).slice(0, 100),
    manufacturer: strip(row.drug_manufacturer, /^\*?\s*(Mkt:)?\s*/i).slice(0, 150),
    country_of_origin: /^(NA|N\/A)$/i.test(country) ? "" : country.slice(0, 80),
    prescription_required: /rx\s*required/i.test(row.prescription_required ?? ""),
    used_for: disease ? [disease.slice(0, 60)] : [],
    reference_price: parseRupees(row.final_price) ?? parseRupees(row.price),
    image_links: images,
    source_url: source,
    item_number: itemNumberFrom(images, source),
  };
}

/** Reads the whole file, merging a medicine listed under several diseases into one. */
export async function readMedicines(
  file: Blob,
  onProgress?: (bytesRead: number, medicines: number) => void,
): Promise<{ medicines: Medicine[]; rows: number; skipped: number }> {
  const byKey = new Map<string, Medicine>();
  const csv = new CsvStream();
  let header: string[] | null = null;
  let rows = 0;
  let skipped = 0;
  const onRow = (cells: string[]) => {
    if (!header) {
      header = cells.map((h) => h.trim().replace(/^﻿/, ""));
      if (!header.includes("med_name")) throw new Error("This file has no med_name column: it is not a medicines catalogue.");
      return;
    }
    rows++;
    const record: Record<string, string> = {};
    header.forEach((h, i) => {
      if (h !== "drug_content") record[h] = cells[i] ?? "";
    });
    const medicine = medicineFromRow(record);
    if (!medicine) {
      skipped++;
      return;
    }
    const known = byKey.get(medicine.key);
    if (known) {
      for (const d of medicine.used_for) if (!known.used_for.includes(d) && known.used_for.length < 12) known.used_for.push(d);
    } else byKey.set(medicine.key, medicine);
  };
  if (typeof file.stream === "function" && typeof TextDecoderStream === "function") {
    const reader = file.stream().pipeThrough(new TextDecoderStream("utf-8")).getReader();
    let read = 0;
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      read += value.length;
      csv.push(value, onRow);
      onProgress?.(read, byKey.size);
    }
  } else {
    // A browser without streams: the whole file at once (fine for the readable part of a catalogue).
    const text = await file.text();
    csv.push(text, onRow);
    onProgress?.(text.length, byKey.size);
  }
  csv.end(onRow);
  return { medicines: [...byKey.values()], rows, skipped };
}

/** The shop's selling price from the reference price and an exchange rate, or null. */
export function sellingPrice(reference: string | null, rate: number | null): string | null {
  if (!reference || !rate || !(rate > 0)) return null;
  return (Math.round(Number(reference) * rate * 100) / 100).toFixed(2);
}
