"use client";

import { useId, useState } from "react";
import { FileUp } from "lucide-react";
import { api, ApiError } from "@/lib/api";
import { cellText, listRecords, newIdempotencyKey, type BusinessSchema } from "@/lib/business";
import { readMedicines, sellingPrice, type Medicine } from "@/lib/medicine-import";
import { Button, ErrorBanner, Input, Label, Modal } from "@/components/ui";
import { useBusiness } from "./BusinessApp";

type Operation = { op: "create"; model: string; ref?: string; data: Record<string, unknown> };

// A medicine is two operations (the medicine, its item number); the server takes at most 100 per transaction.
const MEDICINES_PER_BATCH = 50;

/** What the Pharmacy already has: its item numbers, and its medicines by source link (or name when it has none) --
 * the same key `medicineFromRow` gives, so a medicine without an item number is recognised too. */
export type Existing = { numbers: Set<string>; keys: Set<string> };

export function medicineKey(sourceUrl: string, name: string): string {
  return sourceUrl.trim() || name.trim().toLowerCase();
}

/** The atomic batches that create these medicines, skipping any the Pharmacy already has (by source link or name).
 * An item number goes to one medicine only: a catalogue sometimes gives two different medicines the same product id
 * (it reuses a picture), and the second is then imported without one rather than left out. */
export function importBatches(
  schema: BusinessSchema,
  medicines: Medicine[],
  existing: Existing,
  rate: number | null,
): { batches: Operation[][]; skipped: number; withoutNumber: number } {
  const part = schema.modelId("part");
  const numberModel = schema.modelId("part_number");
  const f = (key: string) => schema.id("part", key);
  const batches: Operation[][] = [];
  let current: Operation[] = [];
  let skipped = 0;
  let withoutNumber = 0;
  const seen = new Set(existing.numbers);
  const known = new Set(existing.keys);
  medicines.forEach((m) => {
    if (known.has(medicineKey(m.source_url, m.name))) {
      skipped++;
      return;
    }
    known.add(medicineKey(m.source_url, m.name));
    const number = m.item_number && !seen.has(m.item_number) ? m.item_number : null;
    if (m.item_number && !number) withoutNumber++;
    const ref = `m${current.length}`;
    const data: Record<string, unknown> = {
      [f("name")]: m.name,
      [f("generic_name")]: m.generic_name,
      [f("pack")]: m.pack,
      [f("manufacturer")]: m.manufacturer,
      [f("country_of_origin")]: m.country_of_origin,
      [f("prescription_required")]: m.prescription_required,
      [f("used_for")]: m.used_for.join(", "),
      [f("image_links")]: m.image_links.join(", "),
      [f("source_url")]: m.source_url,
    };
    if (m.reference_price) {
      data[f("reference_price")] = m.reference_price;
      data[f("reference_currency")] = "INR";
    }
    const price = sellingPrice(m.reference_price, rate);
    if (price) data[f("list_price")] = price;
    current.push({ op: "create", model: part, ref, data });
    if (number) {
      seen.add(number);
      current.push({
        op: "create",
        model: numberModel,
        data: {
          [schema.id("part_number", "number")]: number,
          [schema.id("part_number", "source")]: "catalogue import",
          [schema.id("part_number", "part_number_part")]: { $ref: ref },
        },
      });
    }
    if (current.length >= MEDICINES_PER_BATCH * 2 - 1) {
      batches.push(current);
      current = [];
    }
  });
  if (current.length) batches.push(current);
  return { batches, skipped, withoutNumber };
}

async function existingCatalogue(schema: BusinessSchema): Promise<Existing> {
  const numbers = new Set<string>();
  const keys = new Set<string>();
  for (let offset = 0; ; offset += 500) {
    const page = await listRecords(schema, "part_number", { limit: 500, offset });
    for (const row of page.results) numbers.add(cellText(schema, "part_number", row, "number"));
    if (offset + 500 >= page.count || page.results.length === 0) break;
  }
  for (let offset = 0; ; offset += 500) {
    const page = await listRecords(schema, "part", { limit: 500, offset });
    for (const row of page.results) {
      keys.add(medicineKey(cellText(schema, "part", row, "source_url"), cellText(schema, "part", row, "name")));
    }
    if (offset + 500 >= page.count || page.results.length === 0) break;
  }
  return { numbers, keys };
}

const wait = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

export function MedicineImportButton({ onImported }: { onImported: () => void }) {
  const { schema } = useBusiness();
  const [open, setOpen] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [rate, setRate] = useState("");
  const [busy, setBusy] = useState(false);
  const [progress, setProgress] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState<string | null>(null);
  const ids = { file: useId(), rate: useId() };

  async function run() {
    if (!file) return;
    setBusy(true);
    setError(null);
    setDone(null);
    let imported = 0;
    try {
      setProgress("Reading the file...");
      const { medicines, rows } = await readMedicines(file, (read, count) =>
        setProgress(`Reading the file: ${Math.round((read / Math.max(file.size, 1)) * 100)}% · ${count.toLocaleString()} medicines`),
      );
      setProgress("Checking what the Pharmacy already has...");
      const existing = await existingCatalogue(schema);
      const parsedRate = rate.trim() ? Number(rate.replace(",", ".")) : null;
      const { batches, skipped, withoutNumber } = importBatches(
        schema,
        medicines,
        existing,
        parsedRate && parsedRate > 0 ? parsedRate : null,
      );
      for (let i = 0; i < batches.length; i++) {
        const key = newIdempotencyKey();
        for (let attempt = 0; ; attempt++) {
          try {
            await api.postIdempotent(`/app-instances/${schema.instanceId}/transactions/`, { operations: batches[i] }, key);
            break;
          } catch (err) {
            // Too many requests in a minute (the API's per-person limit): wait and send the same batch again --
            // the same idempotency key means it can never be imported twice.
            if (err instanceof ApiError && err.status === 429 && attempt < 10) {
              setProgress(`Waiting a moment (the server's request limit)... ${imported.toLocaleString()} imported`);
              await wait(15000);
              continue;
            }
            throw err;
          }
        }
        imported += batches[i].filter((op) => op.model === schema.modelId("part")).length;
        setProgress(`Importing: ${imported.toLocaleString()} of ${(medicines.length - skipped).toLocaleString()} medicines`);
      }
      setDone(
        `${imported.toLocaleString()} medicines imported from ${rows.toLocaleString()} rows` +
          (skipped ? `; ${skipped.toLocaleString()} were already here and were left as they are.` : ".") +
          (withoutNumber
            ? ` ${withoutNumber.toLocaleString()} got no item number because the catalogue gives another medicine the same one: add theirs by hand.`
            : ""),
      );
      onImported();
    } catch (err) {
      const reason = err instanceof ApiError ? err.message : err instanceof Error ? err.message : "Something went wrong.";
      setError(
        `${reason} ${imported ? `${imported.toLocaleString()} medicines were imported before this; import the same file again to add the rest (those already here are skipped).` : "Nothing was imported."}`,
      );
    } finally {
      setBusy(false);
      setProgress(null);
    }
  }

  return (
    <>
      <Button variant="secondary" onClick={() => setOpen(true)}>
        <FileUp className="h-4 w-4" aria-hidden="true" />
        Import medicines
      </Button>
      {open && (
        <Modal open onClose={() => !busy && setOpen(false)} title="Import a medicines catalogue">
          <div className="flex flex-col gap-4">
            <p className="text-sm text-slate-600">
              A CSV file with the columns of netmeds&apos; medicines.csv (med_name, generic_name, final_price, img_urls...).
              Each medicine gets its name, generic name, pack, manufacturer, origin, prescription flag, what it is used
              for, the catalogue&apos;s price as a reference price (INR), links to its pictures and an item number for its
              label. Descriptions are not copied. You set your own price and shelf location on each medicine afterwards.
            </p>
            {error && <ErrorBanner message={error} />}
            <div aria-live="polite">
              {done && <p className="text-sm text-green-700">{done}</p>}
              {progress && <p className="text-sm text-slate-600">{progress}</p>}
            </div>
            <div>
              <Label htmlFor={ids.file}>CSV file</Label>
              <Input id={ids.file} type="file" accept=".csv,text/csv" disabled={busy} onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
            </div>
            <div className="max-w-xs">
              <Label htmlFor={ids.rate}>Your price per 1 INR (optional)</Label>
              <Input
                id={ids.rate}
                inputMode="decimal"
                placeholder="e.g. 0.18"
                value={rate}
                disabled={busy}
                onChange={(e) => setRate(e.target.value)}
              />
              <p className="mt-1 text-xs text-text-muted">Leave empty to set every selling price yourself.</p>
            </div>
            <div className="flex justify-end gap-2">
              <Button variant="secondary" onClick={() => setOpen(false)} disabled={busy}>
                Close
              </Button>
              <Button onClick={() => void run()} disabled={busy || !file}>
                {busy ? "Importing..." : "Import"}
              </Button>
            </div>
          </div>
        </Modal>
      )}
    </>
  );
}
