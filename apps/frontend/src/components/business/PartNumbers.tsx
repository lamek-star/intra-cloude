"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useCallback, useEffect, useId, useState, type FormEvent } from "react";
import { ApiError } from "@/lib/api";
import { cellText, createRecord, listRecords, normalizeSearchKey, type BusinessRow } from "@/lib/business";
import {
  Badge,
  Button,
  EmptyState,
  ErrorBanner,
  Input,
  Label,
  Modal,
  PageLoading,
  Table,
  Td,
  Th,
  THead,
} from "@/components/ui";
import { useBusiness } from "./BusinessApp";
import { useNames } from "./hooks";
import ProductPicker, { type PickedProduct } from "./ProductPicker";
import { Pager } from "./RecordSection";

const PAGE = 25;

function PartNumbersInner() {
  const { schema, instance } = useBusiness();
  const initial = useSearchParams().get("q") ?? "";
  const searchId = useId();
  const [input, setInput] = useState(initial);
  const [query, setQuery] = useState(initial);
  const [offset, setOffset] = useState(0);
  const [rows, setRows] = useState<BusinessRow[] | null>(null);
  const [count, setCount] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [open, setOpen] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);

  // The global header search navigates here with ?q=; follow it.
  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setInput(initial);
    setQuery(initial);
    setOffset(0);
  }, [initial]);

  const load = useCallback(async () => {
    try {
      // The SERVER searches (normalized, indexed-scale): however the number is typed -- with or
      // without hyphens or spaces -- it finds the recorded number. The browser never scans records.
      const page = await listRecords(schema, "part_number", { search: query, offset, limit: PAGE });
      setRows(page.results);
      setCount(page.count);
      setError(null);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Part numbers couldn't be searched.");
    }
  }, [schema, query, offset]);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    load();
  }, [load]);

  // Presentation only: an exact match (ignoring hyphens/spaces/case) is listed first.
  const wanted = normalizeSearchKey(query);
  const ranked = [...(rows ?? [])].sort((a, b) => {
    const exact = (r: BusinessRow) => (wanted && normalizeSearchKey(cellText(schema, "part_number", r, "number")) === wanted ? 0 : 1);
    return exact(a) - exact(b);
  });
  const products = useNames("part", "name", ranked.map((r) => cellText(schema, "part_number", r, "part_number_part")));
  const exactCount = wanted ? ranked.filter((r) => normalizeSearchKey(cellText(schema, "part_number", r, "number")) === wanted).length : 0;

  return (
    <section aria-labelledby={`${searchId}-title`}>
      <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 id={`${searchId}-title`} className="text-base font-semibold text-slate-900">
            Part numbers
          </h2>
          <p className="text-sm text-slate-500">
            Find a product by any of its part numbers. Hyphens, spaces and capital letters don&apos;t matter: 04465-0K290,
            044650K290 and 04465 0K290 all find the same part.
          </p>
        </div>
        <Button onClick={() => setOpen(true)}>Add part number</Button>
      </div>

      <form
        role="search"
        className="mb-4 flex max-w-lg gap-2"
        onSubmit={(e) => {
          e.preventDefault();
          setOffset(0);
          setQuery(input);
        }}
      >
        <label htmlFor={searchId} className="sr-only">
          Search part numbers
        </label>
        <Input
          id={searchId}
          type="search"
          value={input}
          placeholder="Search a part number, e.g. 044650K290"
          onChange={(e) => setInput(e.target.value)}
        />
        <Button type="submit">Search</Button>
      </form>

      {notice && (
        <p role="status" className="mb-3 text-sm text-green-700">
          {notice}
        </p>
      )}
      {error && <ErrorBanner message={error} />}
      {!rows && !error && <PageLoading />}
      {rows && rows.length === 0 && (
        <EmptyState
          title={query ? `No part number matches “${query}”` : "No part numbers yet"}
          description={
            query
              ? "Check the number, or try just the first digits. If it isn't recorded yet you can add it."
              : "Add the numbers your products are known by, so they can be found quickly."
          }
          action={<Button onClick={() => setOpen(true)}>Add part number</Button>}
        />
      )}
      {rows && rows.length > 0 && (
        <>
          <p className="mb-2 text-xs text-slate-500" role="status">
            {count} {count === 1 ? "match" : "matches"}
            {exactCount > 1 ? ` — ${exactCount} numbers are the same code written differently; all are shown` : ""}
          </p>
          <Table>
            <THead>
              <Th>Part number</Th>
              <Th>Source</Th>
              <Th>Product</Th>
            </THead>
            <tbody>
              {ranked.map((row) => {
                const number = cellText(schema, "part_number", row, "number");
                const partId = cellText(schema, "part_number", row, "part_number_part");
                const exact = wanted !== "" && normalizeSearchKey(number) === wanted;
                return (
                  <tr key={String(row.id)} className="border-b border-slate-100 last:border-0">
                    <Td className="font-medium tabular-nums">
                      {number} {exact && <Badge tone="success">Exact</Badge>}
                    </Td>
                    <Td>{cellText(schema, "part_number", row, "source")}</Td>
                    <Td>
                      {partId ? (
                        <Link href={`/apps/${instance.id}/products/${partId}`} className="font-medium text-brand-700 hover:underline">
                          {products[partId] ?? "…"}
                        </Link>
                      ) : (
                        "—"
                      )}
                    </Td>
                  </tr>
                );
              })}
            </tbody>
          </Table>
          <Pager offset={offset} count={count} onChange={setOffset} />
        </>
      )}

      <AddPartNumber
        open={open}
        onClose={() => setOpen(false)}
        onAdded={() => {
          setOpen(false);
          setNotice("Part number added.");
          setInput("");
          setQuery("");
          setOffset(0);
          load();
        }}
      />
    </section>
  );
}

export function AddPartNumber({
  open,
  onClose,
  onAdded,
  fixedProduct,
}: {
  open: boolean;
  onClose: () => void;
  onAdded: () => void;
  /** When adding from a product's own page the product is already known. */
  fixedProduct?: PickedProduct;
}) {
  const { schema } = useBusiness();
  const numberId = useId();
  const sourceId = useId();
  const [product, setProduct] = useState<PickedProduct | null>(fixedProduct ?? null);
  const [number, setNumber] = useState("");
  const [source, setSource] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  async function submit(e: FormEvent) {
    e.preventDefault();
    const chosen = fixedProduct ?? product;
    if (!chosen) return setError("Choose the product this number belongs to.");
    if (!number.trim()) return setError("Part number is required.");
    setSaving(true);
    setError(null);
    try {
      await createRecord(schema, "part_number", {
        number: number.trim(),
        source: source.trim() || undefined,
        part_number_part: chosen.id,
      });
      setNumber("");
      setSource("");
      if (!fixedProduct) setProduct(null);
      onAdded();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "The part number couldn't be added.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <Modal open={open} onClose={onClose} title="Add part number">
      <form onSubmit={submit} className="space-y-3">
        {error && <ErrorBanner message={error} />}
        {fixedProduct ? (
          <p className="text-sm text-slate-600">
            For <strong>{fixedProduct.name}</strong>
          </p>
        ) : (
          <ProductPicker label="Product" value={product} onChange={setProduct} />
        )}
        <div>
          <Label htmlFor={numberId}>Part number *</Label>
          <Input id={numberId} value={number} placeholder="e.g. 04465-0K290" onChange={(e) => setNumber(e.target.value)} />
        </div>
        <div>
          <Label htmlFor={sourceId}>Source</Label>
          <Input id={sourceId} value={source} placeholder="e.g. OEM, aftermarket, supplier" onChange={(e) => setSource(e.target.value)} />
        </div>
        <div className="flex justify-end gap-2 pt-1">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" disabled={saving}>
            {saving ? "Adding…" : "Add"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}

export default function PartNumbers() {
  return (
    <Suspense fallback={<PageLoading />}>
      <PartNumbersInner />
    </Suspense>
  );
}
