"use client";

import Link from "next/link";
import { useCallback, useEffect, useId, useRef, useState } from "react";
import { api, ApiError, type AppRecordAttachment, type Bucket, type FileObject } from "@/lib/api";
import { cellText, getRecord, listRecords, type BusinessRow } from "@/lib/business";
import { money } from "@/lib/format";
import { Badge, Button, Card, EmptyState, ErrorBanner, PageLoading, Table, Td, Th, THead } from "@/components/ui";
import { useBusiness } from "./BusinessApp";
import { MovementHistory, StockTable } from "./Inventory";
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

  return (
    <article aria-labelledby={`${tabsId}-title`}>
      <Link href={`/apps/${instance.id}/products`} className="text-sm font-medium text-brand-700 hover:underline">
        ← All products
      </Link>
      <h2 id={`${tabsId}-title`} className="mt-2 mb-4 text-lg font-semibold text-slate-900">
        {name}
      </h2>

      <div role="tablist" aria-label="Product sections" className="mb-5 flex flex-wrap gap-1 border-b border-slate-200">
        {TABS.map((t) => (
          <button
            key={t}
            role="tab"
            id={`${tabsId}-${t}`}
            aria-selected={tab === t}
            aria-controls={`${tabsId}-panel`}
            onClick={() => setTab(t)}
            className={`-mb-px border-b-2 px-3 py-2 text-sm font-medium ${
              tab === t ? "border-brand-600 text-brand-700" : "border-transparent text-slate-600 hover:text-slate-900"
            }`}
          >
            {t}
          </button>
        ))}
      </div>

      <div role="tabpanel" id={`${tabsId}-panel`} aria-labelledby={`${tabsId}-${tab}`}>
        {tab === "Overview" && <Overview part={part} />}
        {tab === "Part numbers" && <ProductNumbers partId={partId} name={name} />}
        {tab === "Stock" && <StockTable partId={partId} />}
        {tab === "Movements" && <MovementHistory partId={partId} />}
        {tab === "Files" && <ProductFiles partId={partId} />}
      </div>
    </article>
  );
}

function Overview({ part }: { part: BusinessRow }) {
  const { schema } = useBusiness();
  const rows: [string, string][] = [
    ["Description", cellText(schema, "part", part, "description")],
    ["Unit of measure", cellText(schema, "part", part, "unit_of_measure")],
    ["List price", part[schema.id("part", "list_price")] != null ? money(part[schema.id("part", "list_price")]) : ""],
    ["Standard cost", part[schema.id("part", "standard_cost")] != null ? money(part[schema.id("part", "standard_cost")]) : ""],
  ];
  const active = part[schema.id("part", "is_active")];
  return (
    <Card>
      <dl className="grid max-w-xl grid-cols-[10rem_1fr] gap-y-2 text-sm">
        {rows.map(([label, value]) => (
          <div key={label} className="contents">
            <dt className="text-slate-500">{label}</dt>
            <dd className="text-slate-900">{value || "—"}</dd>
          </div>
        ))}
        <dt className="text-slate-500">Status</dt>
        <dd>
          <Badge tone={active === false ? "default" : "success"}>{active === false ? "Inactive" : "Active"}</Badge>
        </dd>
      </dl>
    </Card>
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
                  <Td className="font-medium tabular-nums">{cellText(schema, "part_number", r, "number")}</Td>
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
