"use client";

import Link from "next/link";
import { useCallback, useEffect, useId, useRef, useState } from "react";
import { api, ApiError, type AppRecordAttachment, type Bucket, type FileObject } from "@/lib/api";
import {
  cellText,
  editionOf,
  formatMoney,
  getRecord,
  listRecords,
  parseMoney,
  updateRecord,
  WORDS,
  type BusinessRow,
  type BusinessSchema,
  type Edition,
} from "@/lib/business";
import { money } from "@/lib/format";
import { Badge, Button, Card, EmptyState, ErrorBanner, Input, Label, PageLoading, Table, Td, Th, THead } from "@/components/ui";
import { useBusiness } from "./BusinessApp";
import { MovementHistory, StockTable } from "./Inventory";
import { numberCaption, PrintLabelsButton, type LabelData } from "./Labels";
import { ToyoDiyLookup } from "./ToyoDiyLookup";
import { AddPartNumber } from "./PartNumbers";
import { Pager } from "./RecordSection";

const TABS = ["Overview", "Part numbers", "Stock", "Movements", "Files"] as const;
type Tab = (typeof TABS)[number];

export default function ProductDetail({ partId }: { partId: string }) {
  const { schema, instance } = useBusiness();
  const [part, setPart] = useState<BusinessRow | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useState<Tab>("Overview");
  const tabsId = useId();

  useEffect(() => {
    let cancelled = false;
    getRecord(schema, "part", partId)
      .then((row) => {
        if (!cancelled) setPart(row);
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof ApiError && err.status === 404 ? "That product wasn't found." : "The product couldn't be loaded.");
      });
    return () => {
      cancelled = true;
    };
  }, [schema, partId]);

  if (error) return <ErrorBanner message={error} />;
  if (!part) return <PageLoading />;
  const name = cellText(schema, "part", part, "name");
  const words = WORDS[editionOf(schema)];

  return (
    <article aria-labelledby={`${tabsId}-title`}>
      <Link href={`/apps/${instance.id}/products`} className="text-sm font-medium text-brand-700 hover:underline">
        ← All {words.products.toLowerCase()}
      </Link>
      <h2 id={`${tabsId}-title`} className="mt-2 mb-4 text-lg font-semibold text-slate-900">
        {name}
      </h2>

      <div
        role="tablist"
        aria-label="Product sections"
        className="mb-5 flex flex-wrap gap-1 border-b border-slate-200"
        onKeyDown={(e) => {
          // ARIA tabs pattern: arrows move (and wrap), Home/End jump; only the selected tab is a Tab stop.
          const index = TABS.indexOf(tab);
          const target =
            e.key === "ArrowRight" ? TABS[(index + 1) % TABS.length]
            : e.key === "ArrowLeft" ? TABS[(index + TABS.length - 1) % TABS.length]
            : e.key === "Home" ? TABS[0]
            : e.key === "End" ? TABS[TABS.length - 1]
            : null;
          if (!target) return;
          e.preventDefault();
          setTab(target);
          document.getElementById(`${tabsId}-${target}`)?.focus();
        }}
      >
        {TABS.map((t) => (
          <button
            key={t}
            role="tab"
            id={`${tabsId}-${t}`}
            aria-selected={tab === t}
            aria-controls={`${tabsId}-panel`}
            tabIndex={tab === t ? 0 : -1}
            onClick={() => setTab(t)}
            className={`-mb-px border-b-2 px-3 py-2 text-sm font-medium ${
              tab === t ? "border-brand-600 text-brand-700" : "border-transparent text-slate-600 hover:text-slate-900"
            }`}
          >
            {t === "Part numbers" ? words.numbers : t}
          </button>
        ))}
      </div>

      <div role="tabpanel" id={`${tabsId}-panel`} aria-labelledby={`${tabsId}-${tab}`}>
        {tab === "Overview" && <Overview part={part} onSaved={setPart} />}
        {tab === "Part numbers" && <ProductNumbers partId={partId} name={name} />}
        {tab === "Stock" && <StockTable partId={partId} />}
        {tab === "Movements" && <MovementHistory partId={partId} />}
        {tab === "Files" && <ProductFiles partId={partId} />}
      </div>
    </article>
  );
}

type FactField = { key: string; label: string; kind?: "money" | "boolean" | "long" };

// What the Overview shows and the Edit form changes, per edition (fields the installed template lacks are skipped).
const FACTS: Record<Edition, FactField[]> = {
  spare_parts: [
    { key: "name", label: "Name" },
    { key: "description", label: "Description", kind: "long" },
    { key: "unit_of_measure", label: "Unit of measure" },
    { key: "list_price", label: "List price", kind: "money" },
    { key: "standard_cost", label: "Standard cost", kind: "money" },
  ],
  pharmacy: [
    { key: "name", label: "Name" },
    { key: "generic_name", label: "Generic name" },
    { key: "pack", label: "Pack" },
    { key: "manufacturer", label: "Manufacturer" },
    { key: "country_of_origin", label: "Country of origin" },
    { key: "prescription_required", label: "Prescription required", kind: "boolean" },
    { key: "used_for", label: "Used for", kind: "long" },
    { key: "storage_location", label: "Shelf location" },
    { key: "list_price", label: "Your price", kind: "money" },
    { key: "standard_cost", label: "Cost", kind: "money" },
    { key: "reference_price", label: "Reference price", kind: "money" },
    { key: "reference_currency", label: "Reference currency" },
    { key: "image_links", label: "Picture links", kind: "long" },
  ],
};

/** Picture links kept on a medicine: https only, at most six. They load from the internet when shown. */
export function pictureLinks(text: string): string[] {
  return text
    .split(",")
    .map((s) => s.trim())
    .filter((s) => /^https:\/\/[^\s"'<>]+$/.test(s))
    .slice(0, 6);
}

function factText(schema: BusinessSchema, part: BusinessRow, field: FactField): string {
  const value = part[schema.id("part", field.key)];
  if (value === null || value === undefined || value === "") return "";
  if (field.kind === "money") return money(value);
  if (field.kind === "boolean") return value === true ? "Yes" : "No";
  return String(value);
}

function Overview({ part, onSaved }: { part: BusinessRow; onSaved: (row: BusinessRow) => void }) {
  const { schema } = useBusiness();
  const edition = editionOf(schema);
  const facts = FACTS[edition].filter((f) => schema.has("part", f.key));
  const [editing, setEditing] = useState(false);
  const active = part[schema.id("part", "is_active")];
  const pictures = schema.has("part", "image_links") ? pictureLinks(cellText(schema, "part", part, "image_links")) : [];
  const shown = facts.filter((f) => f.key !== "name" && f.key !== "image_links");

  if (editing) return <EditFacts part={part} facts={facts} onCancel={() => setEditing(false)} onSaved={(row) => { setEditing(false); onSaved(row); }} />;

  return (
    <div className="space-y-4">
      <Card>
        <div className="mb-3 flex flex-wrap justify-end gap-2">
          <ProductLabelButton part={part} />
          <Button variant="secondary" onClick={() => setEditing(true)}>
            Edit
          </Button>
        </div>
        <dl className="grid max-w-xl grid-cols-[10rem_1fr] gap-y-2 text-sm">
          {shown.map((field) => (
            <div key={field.key} className="contents">
              <dt className="text-slate-500">{field.label}</dt>
              <dd className="text-slate-900">{factText(schema, part, field) || "—"}</dd>
            </div>
          ))}
          <dt className="text-slate-500">Status</dt>
          <dd>
            <Badge tone={active === false ? "default" : "success"}>{active === false ? "Inactive" : "Active"}</Badge>
          </dd>
        </dl>
      </Card>
      {pictures.length > 0 && (
        <Card>
          <h3 className="mb-1 text-sm font-semibold text-slate-900">Pictures from the catalogue</h3>
          <p className="mb-3 text-xs text-text-muted">
            Shown from the catalogue&apos;s website when this PC is online. Add your own photos under Files; they are kept in
            IntraForge.
          </p>
          <ul className="flex flex-wrap gap-3">
            {pictures.map((src) => (
              <li key={src}>
                <a href={src} target="_blank" rel="noopener noreferrer">
                  {/* eslint-disable-next-line @next/next/no-img-element -- an external link, not a build-time asset */}
                  <img
                    src={src}
                    alt=""
                    loading="lazy"
                    referrerPolicy="no-referrer"
                    className="h-24 w-24 rounded border border-slate-200 object-contain"
                    onError={(e) => {
                      e.currentTarget.style.display = "none";
                    }}
                  />
                </a>
              </li>
            ))}
          </ul>
        </Card>
      )}
    </div>
  );
}

function EditFacts({
  part,
  facts,
  onCancel,
  onSaved,
}: {
  part: BusinessRow;
  facts: FactField[];
  onCancel: () => void;
  onSaved: (row: BusinessRow) => void;
}) {
  const { schema } = useBusiness();
  const formId = useId();
  const [values, setValues] = useState<Record<string, string | boolean>>(() =>
    Object.fromEntries(
      facts.map((f) => {
        const v = part[schema.id("part", f.key)];
        return [f.key, f.kind === "boolean" ? v === true : v === null || v === undefined ? "" : String(v)];
      }),
    ),
  );
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  async function save(e: React.FormEvent) {
    e.preventDefault();
    const payload: Record<string, unknown> = {};
    for (const f of facts) {
      const raw = values[f.key];
      if (f.kind === "boolean") {
        payload[f.key] = raw === true;
        continue;
      }
      const text = String(raw ?? "").trim();
      if (f.key === "name" && !text) return setError("Name is required.");
      if (f.kind === "money") {
        if (!text) {
          payload[f.key] = null;
          continue;
        }
        const cents = parseMoney(text);
        if (cents === null) return setError(`${f.label}: enter an amount such as 15 or 15.50.`);
        payload[f.key] = formatMoney(cents);
        continue;
      }
      payload[f.key] = text;
    }
    setSaving(true);
    setError(null);
    try {
      onSaved(await updateRecord(schema, "part", String(part.id), payload));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "The changes couldn't be saved. Nothing was changed.");
      setSaving(false);
    }
  }

  return (
    <Card>
      <form onSubmit={save} className="space-y-4" aria-label="Edit">
        {error && <ErrorBanner message={error} />}
        <div className="grid gap-3 sm:grid-cols-2">
          {facts.map((f) => {
            const id = `${formId}-${f.key}`;
            if (f.kind === "boolean") {
              return (
                <label key={f.key} htmlFor={id} className="flex items-center gap-2 text-sm text-slate-700 sm:col-span-2">
                  <input
                    id={id}
                    type="checkbox"
                    checked={values[f.key] === true}
                    onChange={(e) => setValues((v) => ({ ...v, [f.key]: e.target.checked }))}
                  />
                  {f.label}
                </label>
              );
            }
            return (
              <div key={f.key} className={f.kind === "long" ? "sm:col-span-2" : undefined}>
                <Label htmlFor={id}>{f.label}</Label>
                <Input
                  id={id}
                  inputMode={f.kind === "money" ? "decimal" : undefined}
                  value={String(values[f.key] ?? "")}
                  onChange={(e) => setValues((v) => ({ ...v, [f.key]: e.target.value }))}
                />
              </div>
            );
          })}
        </div>
        <div className="flex gap-2">
          <Button type="submit" disabled={saving}>
            {saving ? "Saving..." : "Save"}
          </Button>
          <Button type="button" variant="ghost" onClick={onCancel} disabled={saving}>
            Cancel
          </Button>
        </div>
      </form>
    </Card>
  );
}

/** The label for this product: its first item/part number as a barcode, its name and the details that matter. */
export function labelFor(schema: BusinessSchema, part: BusinessRow, number: string): LabelData {
  const text = (key: string) => (schema.has("part", key) ? cellText(schema, "part", part, key) : "");
  const price = part[schema.id("part", "list_price")];
  if (editionOf(schema) === "pharmacy") {
    return {
      number,
      name: text("name"),
      details: [text("generic_name"), [text("pack"), text("manufacturer")].filter(Boolean).join(" · ")],
      price: price != null && price !== "" ? money(price) : undefined,
      location: text("storage_location") || undefined,
      flag: part[schema.id("part", "prescription_required")] === true ? "Rx" : undefined,
    };
  }
  return {
    number,
    name: text("name"),
    details: [text("description"), text("unit_of_measure")],
    price: price != null && price !== "" ? money(price) : undefined,
  };
}

function ProductLabelButton({ part }: { part: BusinessRow }) {
  const { schema } = useBusiness();
  const [number, setNumber] = useState<string | null>(null);
  const words = WORDS[editionOf(schema)];

  useEffect(() => {
    let cancelled = false;
    listRecords(schema, "part_number", { filters: { part_number_part: String(part.id) }, limit: 1 })
      .then((page) => {
        if (!cancelled) setNumber(page.results[0] ? cellText(schema, "part_number", page.results[0], "number") : "");
      })
      .catch(() => !cancelled && setNumber(""));
    return () => {
      cancelled = true;
    };
  }, [schema, part.id]);

  return (
    <PrintLabelsButton
      items={number ? [labelFor(schema, part, number)] : []}
      disabledReason={`Give it ${words.number.toLowerCase()} first: the label carries it as a barcode.`}
      caption={numberCaption(words.number)}
    />
  );
}

function ProductNumbers({ partId, name }: { partId: string; name: string }) {
  const { schema } = useBusiness();
  const [rows, setRows] = useState<BusinessRow[] | null>(null);
  const [count, setCount] = useState(0);
  const [offset, setOffset] = useState(0);
  const [open, setOpen] = useState(false);

  const load = useCallback(async () => {
    const page = await listRecords(schema, "part_number", { filters: { part_number_part: partId }, offset, limit: 25 });
    setRows(page.results);
    setCount(page.count);
  }, [schema, partId, offset]);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    load().catch(() => setRows([]));
  }, [load]);

  return (
    <div>
      <div className="mb-3 flex justify-end">
        <Button onClick={() => setOpen(true)}>Add part number</Button>
      </div>
      {!rows && <PageLoading />}
      {rows && rows.length === 0 && (
        <EmptyState title="No part numbers yet" description="Add the numbers this product is known by so it can be found quickly." />
      )}
      {rows && rows.length > 0 && (
        <>
          <Table>
            <THead>
              <Th>Part number</Th>
              <Th>Source</Th>
            </THead>
            <tbody>
              {rows.map((r) => (
                <tr key={String(r.id)} className="border-b border-slate-100 last:border-0">
                  <Td className="font-medium tabular-nums">
                    {cellText(schema, "part_number", r, "number")}
                    {editionOf(schema) === "spare_parts" && <ToyoDiyLookup number={cellText(schema, "part_number", r, "number")} />}
                  </Td>
                  <Td>{cellText(schema, "part_number", r, "source")}</Td>
                </tr>
              ))}
            </tbody>
          </Table>
          <Pager offset={offset} count={count} onChange={setOffset} />
        </>
      )}
      <AddPartNumber
        open={open}
        fixedProduct={{ id: partId, name, row: {} }}
        onClose={() => setOpen(false)}
        onAdded={() => {
          setOpen(false);
          load().catch(() => undefined);
        }}
      />
    </div>
  );
}

const FILES_BUCKET = "Business Files";

/** Product images and documents, kept in IntraForge's own object storage and attached to the
 * product record -- real files with real access control, not data URLs in the browser. */
function ProductFiles({ partId }: { partId: string }) {
  const { schema, instance } = useBusiness();
  const inputId = useId();
  const fileInput = useRef<HTMLInputElement>(null);
  const [files, setFiles] = useState<AppRecordAttachment[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const base = `/app-models/${schema.modelId("part")}/records/${partId}/attachments/`;

  const load = useCallback(async () => {
    try {
      setFiles(await api.get<AppRecordAttachment[]>(base));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Files couldn't be loaded.");
    }
  }, [base]);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    load();
  }, [load]);

  async function upload(file: File) {
    setUploading(true);
    setError(null);
    setNotice(null);
    try {
      const buckets = await api.get<Bucket[]>(`/projects/${instance.project}/buckets/`);
      const bucket =
        buckets.find((b) => b.name === FILES_BUCKET) ??
        (await api.post<Bucket>(`/projects/${instance.project}/buckets/`, { name: FILES_BUCKET }));
      const form = new FormData();
      form.append("file", file);
      form.append("display_filename", file.name);
      const stored = await api.postForm<FileObject>(`/buckets/${bucket.id}/files/`, form);
      await api.post(base, { file_id: stored.id });
      setNotice(`${file.name} added.`);
      await load();
    } catch (err) {
      setError(
        err instanceof ApiError && err.status === 403
          ? "You don't have permission to add files here."
          : err instanceof ApiError
            ? err.message
            : "The file couldn't be added.",
      );
    } finally {
      setUploading(false);
      if (fileInput.current) fileInput.current.value = "";
    }
  }

  return (
    <div>
      <div className="mb-3">
        <label htmlFor={inputId} className="mb-1.5 block text-xs font-medium text-slate-500">
          Add an image or document
        </label>
        <input
          ref={fileInput}
          id={inputId}
          type="file"
          disabled={uploading}
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) upload(file);
          }}
          className="block text-sm text-slate-700 file:mr-3 file:rounded-lg file:border file:border-slate-200 file:bg-white file:px-3 file:py-1.5 file:text-sm file:font-medium"
        />
        {uploading && (
          <p role="status" className="mt-1 text-xs text-slate-500">
            Uploading…
          </p>
        )}
      </div>
      {notice && (
        <p role="status" className="mb-3 text-sm text-green-700">
          {notice}
        </p>
      )}
      {error && <ErrorBanner message={error} />}
      {!files && !error && <PageLoading />}
      {files && files.length === 0 && (
        <EmptyState title="No files yet" description="Attach product photos, data sheets or supplier documents." />
      )}
      {files && files.length > 0 && (
        <ul className="grid gap-3 sm:grid-cols-2">
          {files.map((f) => {
            const href = `/api/v1${base}${f.id}/download/`;
            const image = f.mime_type.startsWith("image/");
            return (
              <li key={f.id}>
                <Card className="flex items-center gap-3">
                  {image && (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img src={href} alt={f.filename} className="h-16 w-16 rounded-lg border border-slate-200 object-cover" />
                  )}
                  <div className="min-w-0">
                    <a href={href} className="block truncate text-sm font-medium text-brand-700 hover:underline">
                      {f.filename}
                    </a>
                    <p className="text-xs text-slate-500">
                      {f.mime_type} · {Math.max(1, Math.round(f.size / 1024))} KB
                    </p>
                  </div>
                </Card>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
