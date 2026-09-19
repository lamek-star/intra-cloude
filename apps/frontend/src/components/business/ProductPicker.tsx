"use client";

import { useEffect, useId, useState } from "react";
import { cellText, getRecord, listRecords, type BusinessRow } from "@/lib/business";
import { Button } from "@/components/ui";
import { useBusiness } from "./BusinessApp";

export type PickedProduct = { id: string; name: string; row: BusinessRow };

type Suggestion = PickedProduct & { via?: string };

/** Type-ahead product finder. Every keystroke asks the SERVER: products are matched by name, and
 * part numbers -- however they are typed (04465-0K290, 044650K290, 04465 0K290) -- are searched with
 * the backend's normalized search and led back to their product. Nothing is scanned client-side. */
export default function ProductPicker({
  label,
  value,
  onChange,
}: {
  label: string;
  value: PickedProduct | null;
  onChange: (product: PickedProduct | null) => void;
}) {
  const { schema } = useBusiness();
  const inputId = useId();
  const listId = useId();
  const [query, setQuery] = useState("");
  const [suggestions, setSuggestions] = useState<Suggestion[] | null>(null);
  const [searching, setSearching] = useState(false);

  useEffect(() => {
    const q = query.trim();
    if (!q) return;
    let cancelled = false;
    const timer = setTimeout(async () => {
      setSearching(true);
      try {
        const [parts, numbers] = await Promise.all([
          listRecords(schema, "part", { search: q, limit: 8 }),
          listRecords(schema, "part_number", { search: q, limit: 8 }),
        ]);
        const found = new Map<string, Suggestion>();
        for (const row of parts.results) {
          found.set(String(row.id), { id: String(row.id), name: cellText(schema, "part", row, "name"), row });
        }
        for (const number of numbers.results) {
          const partId = cellText(schema, "part_number", number, "part_number_part");
          if (!partId || found.has(partId)) continue;
          try {
            const row = await getRecord(schema, "part", partId);
            found.set(partId, {
              id: partId,
              name: cellText(schema, "part", row, "name"),
              row,
              via: cellText(schema, "part_number", number, "number"),
            });
          } catch {
            /* a part number whose product can't be read is simply not offered */
          }
        }
        if (!cancelled) setSuggestions(Array.from(found.values()));
      } catch {
        if (!cancelled) setSuggestions([]);
      } finally {
        if (!cancelled) setSearching(false);
      }
    }, 250);
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [query, schema]);

  if (value) {
    return (
      <div>
        <span className="mb-1.5 block text-xs font-medium text-slate-500">{label}</span>
        <div className="flex items-center justify-between rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm">
          <span className="font-medium text-slate-900">{value.name}</span>
          <Button
            type="button"
            size="sm"
            variant="ghost"
            aria-label={`Change ${label.toLowerCase()}`}
            onClick={() => {
              onChange(null);
              setQuery("");
              setSuggestions(null);
            }}
          >
            Change
          </Button>
        </div>
      </div>
    );
  }

  const shown = query.trim() ? suggestions : null;
  return (
    <div>
      <label htmlFor={inputId} className="mb-1.5 block text-xs font-medium text-slate-500">
        {label}
      </label>
      <input
        id={inputId}
        type="search"
        autoComplete="off"
        role="combobox"
        aria-expanded={Boolean(shown)}
        aria-controls={listId}
        aria-autocomplete="list"
        value={query}
        placeholder="Type a product name or part number"
        onChange={(e) => setQuery(e.target.value)}
        className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 placeholder:text-slate-400 outline-none focus:border-brand-400 focus:ring-2 focus:ring-brand-500/20"
      />
      <div id={listId} role="listbox" aria-label={`${label} matches`} className="mt-1">
        {searching && <p className="px-1 py-1 text-xs text-slate-400">Searching…</p>}
        {shown && shown.length === 0 && !searching && (
          <p className="px-1 py-1 text-xs text-slate-500">No product or part number matches “{query.trim()}”.</p>
        )}
        {shown?.map((s) => (
          <button
            key={s.id}
            type="button"
            role="option"
            aria-selected="false"
            onClick={() => onChange({ id: s.id, name: s.name, row: s.row })}
            className="block w-full rounded-lg px-3 py-2 text-left text-sm text-slate-800 hover:bg-slate-100 focus-visible:bg-slate-100 focus-visible:outline-none"
          >
            {s.name}
            {s.via && <span className="ml-2 text-xs text-slate-500">part number {s.via}</span>}
          </button>
        ))}
      </div>
    </div>
  );
}
