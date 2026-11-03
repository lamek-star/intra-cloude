"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { ApiError } from "@/lib/api";
import { cell, cellText, listRecords, type BusinessRow } from "@/lib/business";
import { formatDate, money } from "@/lib/format";
import { Badge, EmptyState, ErrorBanner, LinkButton, PageLoading, Table, Td, Th, THead } from "@/components/ui";
import { useBusiness } from "./BusinessApp";
import { useNames } from "./hooks";
import { Pager } from "./RecordSection";

export default function Sales() {
  const { schema, instance } = useBusiness();
  const [offset, setOffset] = useState(0);
  const [rows, setRows] = useState<BusinessRow[] | null>(null);
  const [count, setCount] = useState(0);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    listRecords(schema, "sales_order", { ordering: "-order_date", offset, limit: 25 })
      .then((page) => {
        if (cancelled) return;
        setRows(page.results);
        setCount(page.count);
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof ApiError ? err.message : "Sales couldn't be loaded.");
      });
    return () => {
      cancelled = true;
    };
  }, [schema, offset]);

  const customers = useNames("customer", "name", (rows ?? []).map((r) => cellText(schema, "sales_order", r, "customer")));

  return (
    <section aria-labelledby="sales-title">
      <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 id="sales-title" className="text-base font-semibold text-slate-900">
            Sales
          </h2>
          <p className="text-sm text-slate-500">Every sale, newest first. Open one to see its invoice.</p>
        </div>
        <LinkButton href={`/apps/${instance.id}/sales/new`} variant="primary">
          New sale
        </LinkButton>
      </div>
      {error && <ErrorBanner message={error} />}
      {!rows && !error && <PageLoading />}
      {rows && rows.length === 0 && (
        <EmptyState
          title="No sales yet"
          description="Your first sale will appear here with its invoice."
          action={<LinkButton href={`/apps/${instance.id}/sales/new`} variant="primary">New sale</LinkButton>}
        />
      )}
      {rows && rows.length > 0 && (
        <>
          <Table>
            <THead>
              <Th>Date</Th>
              <Th>Customer</Th>
              <Th>Total</Th>
              <Th>Status</Th>
              <Th>
                <span className="sr-only">Open</span>
              </Th>
            </THead>
            <tbody>
              {rows.map((row) => (
                <tr key={String(row.id)} className="border-b border-slate-100 last:border-0">
                  <Td>{formatDate(cell(schema, "sales_order", row, "order_date"))}</Td>
                  <Td>{customers[cellText(schema, "sales_order", row, "customer")] ?? "…"}</Td>
                  <Td className="tabular-nums">{money(cell(schema, "sales_order", row, "total_amount"))}</Td>
                  <Td>
                    <Badge tone="success">{cellText(schema, "sales_order", row, "status")}</Badge>
                  </Td>
                  <Td>
                    <Link href={`/apps/${instance.id}/sales/${row.id}`} className="font-medium text-brand-700 hover:underline">
                      Open sale
                    </Link>
                  </Td>
                </tr>
              ))}
            </tbody>
          </Table>
          <Pager offset={offset} count={count} onChange={setOffset} />
        </>
      )}
    </section>
  );
}
