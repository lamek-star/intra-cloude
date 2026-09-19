"use client";

import { useEffect, useState } from "react";
import { cellText, getRecord, listAllRecords, type BusinessRow } from "@/lib/business";
import { useBusiness } from "./BusinessApp";

/** id -> display name for the records a page is showing, fetched on demand and cached. Used to put
 * names next to relationship ids in tables (a product's name, a customer's name). */
export function useNames(modelKey: string, labelKey: string, ids: (string | null | undefined)[]): Record<string, string> {
  const { schema } = useBusiness();
  const [names, setNames] = useState<Record<string, string>>({});
  const wanted = Array.from(new Set(ids.filter((id): id is string => Boolean(id)))).sort();
  const wantedKey = wanted.join("|");

  useEffect(() => {
    const missing = wantedKey ? wantedKey.split("|").filter((id) => !(id in names)) : [];
    if (missing.length === 0) return;
    let cancelled = false;
    Promise.all(
      missing.map(async (id): Promise<[string, string]> => {
        try {
          const row = await getRecord(schema, modelKey, id);
          return [id, cellText(schema, modelKey, row, labelKey) || "(unnamed)"];
        } catch {
          return [id, "(unavailable)"];
        }
      }),
    ).then((pairs) => {
      if (!cancelled) setNames((previous) => ({ ...previous, ...Object.fromEntries(pairs) }));
    });
    return () => {
      cancelled = true;
    };
    // `names` is intentionally read but not a dependency: it only ever grows, and re-running on
    // each growth would re-request nothing new.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [schema, modelKey, labelKey, wantedKey]);

  return names;
}

export type Option = { id: string; label: string; row: BusinessRow };

/** A short pick list (warehouses, customers, suppliers) -- every record of a small model, sorted by
 * label. Product lookup never uses this: products are found by server-side search. */
export function useOptions(modelKey: string, labelKey: string): { options: Option[]; loading: boolean; error: boolean } {
  const { schema } = useBusiness();
  const [state, setState] = useState<{ options: Option[]; loading: boolean; error: boolean }>({
    options: [],
    loading: true,
    error: false,
  });

  useEffect(() => {
    let cancelled = false;
    listAllRecords(schema, modelKey)
      .then((rows) => {
        if (cancelled) return;
        const options = rows
          .map((row) => ({ id: String(row.id), label: cellText(schema, modelKey, row, labelKey), row }))
          .sort((a, b) => a.label.localeCompare(b.label));
        setState({ options, loading: false, error: false });
      })
      .catch(() => {
        if (!cancelled) setState({ options: [], loading: false, error: true });
      });
    return () => {
      cancelled = true;
    };
  }, [schema, modelKey, labelKey]);

  return state;
}
