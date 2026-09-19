"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { ApiError } from "@/lib/api";
import { cell, cellText, listRecords, type BusinessRow } from "@/lib/business";
import { formatDateTime, signed } from "@/lib/format";
import { EmptyState, ErrorBanner, LinkButton, PageLoading, Select, Table, Td, Th, THead } from "@/components/ui";
import { useBusiness } from "./BusinessApp";
import { useNames, useOptions } from "./hooks";
import { Pager } from "./RecordSection";

const PAGE = 25;

/** Current stock per product and warehouse. The number shown is the quantity the DATABASE ledger
 * holds; this screen only reads it -- there is deliberately no way to type a balance in. */
export function StockTable({ partId }: { partId?: string }) {
  const { schema, instance } = useBusiness();
  const warehouses = useOptions("warehouse", "name");
  const [warehouse, setWarehouse] = useState("");
  const [offset, setOffset] = useState(0);
  const [rows, setRows] = useState<BusinessRow[] | null>(null);
  const [count, setCount] = useState(0);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const filters: Record<string, string> = {};
      if (partId) filters.part = partId;
      if (warehouse) filters.warehouse = warehouse;
      const page = await listRecords(schema, "inventory", { filters, offset, limit: PAGE });
      setRows(page.results);
      setCount(page.count);
      setError(null);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Stock couldn't be loaded.");
    }
  }, [schema, partId, warehouse, offset]);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    load();
  }, [load]);

  const partNames = useNames("part", "name", (rows ?? []).map((r) => cellText(schema, "inventory", r, "part")));
  const warehouseNames = useNames("warehouse", "name", (rows ?? []).map((r) => cellText(schema, "inventory", r, "warehouse")));

  return (
    <div>
      <div className="mb-3 flex flex-wrap items-end justify-between gap-3">
        <div className="w-56">
          <label htmlFor="stock-warehouse" className="mb-1.5 block text-xs font-medium text-slate-500">
            Warehouse
          </label>
          <Select
            id="stock-warehouse"
            value={warehouse}
            onChange={(e) => {
              setOffset(0);
              setWarehouse(e.target.value);
            }}
          >
            <option value="">All warehouses</option>
            {warehouses.options.map((o) => (
              <option key={o.id} value={o.id}>
                {o.label}
              </option>
            ))}
          </Select>
        </div>
        <LinkButton href={`/apps/${instance.id}/receive`} variant="primary">
          Receive stock
        </LinkButton>
      </div>
      {error && <ErrorBanner message={error} />}
      {!rows && !error && <PageLoading />}
      {rows && rows.length === 0 && (
        <EmptyState
          title="No stock recorded yet"
          description="Stock appears here as soon as you receive some. Its quantity is only ever changed by receiving, selling or moving stock."
        />
      )}
      {rows && rows.length > 0 && (
        <>
          <Table>
            <THead>
              <Th>Product</Th>
              <Th>Warehouse</Th>
              <Th>On hand</Th>
            </THead>
            <tbody>
              {rows.map((row) => {
                const pid = cellText(schema, "inventory", row, "part");
                return (
                  <tr key={String(row.id)} className="border-b border-slate-100 last:border-0">
                    <Td>
                      <Link href={`/apps/${instance.id}/products/${pid}`} className="font-medium text-brand-700 hover:underline">
                        {partNames[pid] ?? "…"}
                      </Link>
                    </Td>
                    <Td>{warehouseNames[cellText(schema, "inventory", row, "warehouse")] ?? "…"}</Td>
                    <Td className="font-medium tabular-nums">{cellText(schema, "inventory", row, "quantity_on_hand")}</Td>
                  </tr>
                );
              })}
            </tbody>
          </Table>
          <Pager offset={offset} count={count} onChange={setOffset} />
        </>
      )}
    </div>
  );
}

/** The append-only history behind the stock numbers, newest first. */
export function MovementHistory({ partId }: { partId?: string }) {
  const { schema } = useBusiness();
  const [offset, setOffset] = useState(0);
  const [rows, setRows] = useState<BusinessRow[] | null>(null);
  const [count, setCount] = useState(0);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    listRecords(schema, "stock_movement", {
      filters: partId ? { stock_movement_part: partId } : undefined,
      ordering: "-occurred_at",
      offset,
      limit: PAGE,
    })
      .then((page) => {
        if (cancelled) return;
        setRows(page.results);
        setCount(page.count);
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof ApiError ? err.message : "Movements couldn't be loaded.");
      });
    return () => {
      cancelled = true;
    };
  }, [schema, partId, offset]);

  const partNames = useNames("part", "name", (rows ?? []).map((r) => cellText(schema, "stock_movement", r, "stock_movement_part")));
  const warehouseNames = useNames(
    "warehouse",
    "name",
    (rows ?? []).map((r) => cellText(schema, "stock_movement", r, "stock_movement_warehouse")),
  );

  if (error) return <ErrorBanner message={error} />;
  if (!rows) return <PageLoading />;
  if (rows.length === 0) return <EmptyState title="No stock movements yet" description="Every receipt and sale is recorded here." />;
  return (
    <>
      <Table>
        <THead>
          <Th>When</Th>
          {!partId && <Th>Product</Th>}
          <Th>Warehouse</Th>
          <Th>Change</Th>
          <Th>Type</Th>
          <Th>Reference</Th>
        </THead>
        <tbody>
          {rows.map((row) => (
            <tr key={String(row.id)} className="border-b border-slate-100 last:border-0">
              <Td>{formatDateTime(cell(schema, "stock_movement", row, "occurred_at"))}</Td>
              {!partId && <Td>{partNames[cellText(schema, "stock_movement", row, "stock_movement_part")] ?? "…"}</Td>}
              <Td>{warehouseNames[cellText(schema, "stock_movement", row, "stock_movement_warehouse")] ?? "…"}</Td>
              <Td className="font-medium tabular-nums">{signed(cell(schema, "stock_movement", row, "quantity_delta"))}</Td>
              <Td>{cellText(schema, "stock_movement", row, "movement_type")}</Td>
              <Td>{cellText(schema, "stock_movement", row, "reference")}</Td>
            </tr>
          ))}
        </tbody>
      </Table>
      <Pager offset={offset} count={count} onChange={setOffset} />
    </>
  );
}

export default function InventoryPage() {
  return (
    <section aria-labelledby="stock-title" className="space-y-8">
      <div>
        <h2 id="stock-title" className="text-base font-semibold text-slate-900">
          Stock
        </h2>
        <p className="mb-4 text-sm text-slate-500">What you have, and where. Only receiving, selling and moving stock changes it.</p>
        <StockTable />
      </div>
      <div>
        <h2 className="mb-3 text-base font-semibold text-slate-900">Recent stock movements</h2>
        <MovementHistory />
      </div>
    </section>
  );
}
