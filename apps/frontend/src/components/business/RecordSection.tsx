"use client";

import Link from "next/link";
import { useCallback, useEffect, useId, useState, type FormEvent } from "react";
import { ApiError } from "@/lib/api";
import {
  cellText,
  createRecord,
  formatMoney,
  listRecords,
  parseMoney,
  type BusinessRow,
} from "@/lib/business";
import {
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

export type ColumnDef = { key: string; label: string };
export type FieldDef = {
  key: string;
  label: string;
  required?: boolean;
  /** money is entered as 15 or 15.50 and sent as a two-decimal string. */
  kind?: "text" | "money";
  placeholder?: string;
};

const PAGE_SIZE = 25;

export function Pager({
  offset,
  count,
  onChange,
}: {
  offset: number;
  count: number;
  onChange: (offset: number) => void;
}) {
  if (count <= PAGE_SIZE) return null;
  const from = offset + 1;
  const to = Math.min(offset + PAGE_SIZE, count);
  return (
    <div className="mt-3 flex items-center justify-between text-xs text-slate-500">
      <span>
        {from}–{to} of {count}
      </span>
      <span className="flex gap-2">
        <Button size="sm" variant="secondary" disabled={offset === 0} onClick={() => onChange(Math.max(0, offset - PAGE_SIZE))}>
          Previous
        </Button>
        <Button size="sm" variant="secondary" disabled={offset + PAGE_SIZE >= count} onClick={() => onChange(offset + PAGE_SIZE)}>
          Next
        </Button>
      </span>
    </div>
  );
}

/** A searchable, paged list of one model with an "Add" form. Search and paging are the server's. */
export default function RecordSection({
  modelKey,
  title,
  description,
  noun,
  columns,
  fields,
  searchPlaceholder,
  emptyHint,
  linkKey,
  rowHref,
}: {
  modelKey: string;
  title: string;
  description: string;
  noun: string;
  columns: ColumnDef[];
  fields: FieldDef[];
  searchPlaceholder: string;
  emptyHint: string;
  /** The column whose text links to the record's own page, when there is one. */
  linkKey?: string;
  rowHref?: (row: BusinessRow) => string;
}) {
  const { schema } = useBusiness();
  const searchId = useId();
  const [rows, setRows] = useState<BusinessRow[] | null>(null);
  const [count, setCount] = useState(0);
  const [offset, setOffset] = useState(0);
  const [searchInput, setSearchInput] = useState("");
  const [search, setSearch] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [open, setOpen] = useState(false);
  const [values, setValues] = useState<Record<string, string>>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const page = await listRecords(schema, modelKey, { search, offset, limit: PAGE_SIZE });
      setRows(page.results);
      setCount(page.count);
      setError(null);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : `The ${title.toLowerCase()} couldn't be loaded.`);
    }
  }, [schema, modelKey, search, offset, title]);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    load();
  }, [load]);

  function openForm() {
    setValues({});
    setFormError(null);
    setOpen(true);
  }

  async function submit(e: FormEvent) {
    e.preventDefault();
    const payload: Record<string, unknown> = {};
    for (const field of fields) {
      const raw = (values[field.key] ?? "").trim();
      if (!raw) {
        if (field.required) return setFormError(`${field.label} is required.`);
        continue;
      }
      if (field.kind === "money") {
        const cents = parseMoney(raw);
        if (cents === null) return setFormError(`${field.label} must be an amount like 15 or 15.50.`);
        payload[field.key] = formatMoney(cents);
      } else {
        payload[field.key] = raw;
      }
    }
    setSaving(true);
    setFormError(null);
    try {
      await createRecord(schema, modelKey, payload);
      setOpen(false);
      setNotice(`${noun} added.`);
      setSearchInput("");
      setSearch("");
      setOffset(0);
      await load();
    } catch (err) {
      setFormError(err instanceof ApiError ? err.message : `The ${noun.toLowerCase()} couldn't be added.`);
    } finally {
      setSaving(false);
    }
  }

  return (
    <section aria-labelledby={`${searchId}-title`}>
      <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 id={`${searchId}-title`} className="text-base font-semibold text-slate-900">
            {title}
          </h2>
          <p className="text-sm text-slate-500">{description}</p>
        </div>
        <Button onClick={openForm}>Add {noun.toLowerCase()}</Button>
      </div>

      <form
        className="mb-4 flex max-w-md gap-2"
        role="search"
        aria-label={`Search ${title.toLowerCase()}`}
        onSubmit={(e) => {
          e.preventDefault();
          setOffset(0);
          setSearch(searchInput);
        }}
      >
        <label htmlFor={searchId} className="sr-only">
          Search {title.toLowerCase()}
        </label>
        <Input
          id={searchId}
          type="search"
          value={searchInput}
          placeholder={searchPlaceholder}
          onChange={(e) => setSearchInput(e.target.value)}
        />
        <Button type="submit" variant="secondary">
          Search
        </Button>
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
          title={search ? `No ${title.toLowerCase()} match “${search}”` : `No ${title.toLowerCase()} yet`}
          description={search ? "Check the spelling, or try fewer words." : emptyHint}
          action={!search && <Button onClick={openForm}>Add {noun.toLowerCase()}</Button>}
        />
      )}
      {rows && rows.length > 0 && (
        <>
          <Table>
            <THead>
              {columns.map((c) => (
                <Th key={c.key}>{c.label}</Th>
              ))}
            </THead>
            <tbody>
              {rows.map((row) => (
                <tr key={String(row.id)} className="border-b border-slate-100 last:border-0">
                  {columns.map((c) => (
                    <Td key={c.key}>
                      {rowHref && c.key === linkKey ? (
                        <Link href={rowHref(row)} className="font-medium text-brand-700 hover:underline">
                          {cellText(schema, modelKey, row, c.key) || "(unnamed)"}
                        </Link>
                      ) : (
                        cellText(schema, modelKey, row, c.key)
                      )}
                    </Td>
                  ))}
                </tr>
              ))}
            </tbody>
          </Table>
          <Pager offset={offset} count={count} onChange={setOffset} />
        </>
      )}

      <Modal open={open} onClose={() => setOpen(false)} title={`Add ${noun.toLowerCase()}`}>
        <form onSubmit={submit} className="space-y-3">
          {formError && <ErrorBanner message={formError} />}
          {fields.map((field) => (
            <FieldInput
              key={field.key}
              field={field}
              value={values[field.key] ?? ""}
              onChange={(v) => setValues((current) => ({ ...current, [field.key]: v }))}
            />
          ))}
          <div className="flex justify-end gap-2 pt-1">
            <Button type="button" variant="secondary" onClick={() => setOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={saving}>
              {saving ? "Adding…" : "Add"}
            </Button>
          </div>
        </form>
      </Modal>
    </section>
  );
}

function FieldInput({
  field,
  value,
  onChange,
}: {
  field: FieldDef;
  value: string;
  onChange: (value: string) => void;
}) {
  const id = useId();
  return (
    <div>
      <Label htmlFor={id}>
        {field.label}
        {field.required ? " *" : ""}
      </Label>
      <Input
        id={id}
        value={value}
        placeholder={field.placeholder}
        inputMode={field.kind === "money" ? "decimal" : undefined}
        onChange={(e) => onChange(e.target.value)}
      />
    </div>
  );
}
