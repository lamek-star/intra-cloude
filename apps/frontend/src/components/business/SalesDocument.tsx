"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { ApiError } from "@/lib/api";
import { cell, cellText, editionOf, getRecord, listRecords, WORDS, type BusinessRow } from "@/lib/business";
import { formatDate, formatDateTime, money, signed } from "@/lib/format";
import type { InvoiceData } from "@/lib/invoice";
import { Badge, Card, ErrorBanner, PageLoading, Table, Td, Th, THead } from "@/components/ui";
import { numberCaption } from "./Labels";
import { PrintInvoiceButton } from "./InvoicePrint";
import { useBusiness } from "./BusinessApp";
import { useNames } from "./hooks";

type Doc = {
  order: BusinessRow;
  customer: string;
  lines: BusinessRow[];
  invoice: BusinessRow | null;
  movements: BusinessRow[];
};

/** The sales document: the invoice for one sale, its lines, and the stock that left because of it.
 * Everything is read from IntraForge; this screen never changes anything. "Print invoice" prints it on
 * A4 or a receipt printer with the shop's details (InvoicePrint.tsx), or saves it as a PDF. */
export default function SalesDocument({ orderId, autoPrint = false }: { orderId: string; autoPrint?: boolean }) {
  const { schema, instance } = useBusiness();
  const [doc, setDoc] = useState<Doc | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const order = await getRecord(schema, "sales_order", orderId);
        const customerId = cellText(schema, "sales_order", order, "customer");
        const [customer, lines, invoices] = await Promise.all([
          customerId ? getRecord(schema, "customer", customerId) : Promise.resolve(null),
          listRecords(schema, "sales_order_line", { filters: { sales_order_line_sales_order: orderId }, limit: 200 }),
          listRecords(schema, "invoice", { filters: { invoice_sales_order: orderId }, limit: 1 }),
        ]);
        const invoice = invoices.results[0] ?? null;
        // The sale's stock movements carry the invoice number as their reference.
        const movements = invoice
          ? await listRecords(schema, "stock_movement", {
              filters: { reference: cellText(schema, "invoice", invoice, "invoice_number") },
              limit: 200,
            })
          : { results: [] as BusinessRow[] };
        if (!cancelled) {
          setDoc({
            order,
            customer: customer ? cellText(schema, "customer", customer, "name") : "",
            lines: lines.results,
            invoice,
            movements: movements.results,
          });
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof ApiError && err.status === 404 ? "That sale wasn't found." : "The sales document couldn't be loaded.");
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [schema, orderId]);

  const partIds = [
    ...(doc?.lines ?? []).map((l) => cellText(schema, "sales_order_line", l, "sales_order_line_part")),
    ...(doc?.movements ?? []).map((m) => cellText(schema, "stock_movement", m, "stock_movement_part")),
  ];
  const parts = useNames("part", "name", partIds);
  // Each line's part number (the first one the product has), for the printed invoice.
  const [numbers, setNumbers] = useState<Record<string, string>>({});
  const lineParts = [...new Set((doc?.lines ?? []).map((l) => cellText(schema, "sales_order_line", l, "sales_order_line_part")).filter(Boolean))];
  const linePartsKey = lineParts.join(",");
  useEffect(() => {
    if (!linePartsKey) return;
    let cancelled = false;
    Promise.all(
      linePartsKey.split(",").map(async (id) => {
        const page = await listRecords(schema, "part_number", { filters: { part_number_part: id }, limit: 1 });
        return [id, page.results[0] ? cellText(schema, "part_number", page.results[0], "number") : ""] as const;
      }),
    )
      .then((pairs) => !cancelled && setNumbers(Object.fromEntries(pairs)))
      .catch(() => !cancelled && setNumbers({}));
    return () => {
      cancelled = true;
    };
  }, [schema, linePartsKey]);
  const warehouses = useNames(
    "warehouse",
    "name",
    (doc?.movements ?? []).map((m) => cellText(schema, "stock_movement", m, "stock_movement_warehouse")),
  );

  if (error) return <ErrorBanner message={error} />;
  if (!doc) return <PageLoading />;

  const invoiceNumber = doc.invoice ? cellText(schema, "invoice", doc.invoice, "invoice_number") : "";
  const words = WORDS[editionOf(schema)];
  const namesReady = lineParts.every((id) => parts[id] !== undefined);
  const invoiceData: InvoiceData | null = namesReady
    ? {
        number: invoiceNumber,
        date: formatDate(
          (doc.invoice && cell(schema, "invoice", doc.invoice, "invoice_date")) || cell(schema, "sales_order", doc.order, "order_date"),
        ),
        payment: doc.invoice ? cellText(schema, "invoice", doc.invoice, "status") : "",
        customer: doc.customer,
        lines: doc.lines.map((line) => {
          const partId = cellText(schema, "sales_order_line", line, "sales_order_line_part");
          return {
            number: numbers[partId] ?? "",
            name: parts[partId] ?? "",
            quantity: cellText(schema, "sales_order_line", line, "quantity"),
            unitPrice: money(cell(schema, "sales_order_line", line, "unit_price")),
            total: money(cell(schema, "sales_order_line", line, "line_total")),
          };
        }),
        total: money(cell(schema, "sales_order", doc.order, "total_amount")),
        amountDue: money(doc.invoice ? cell(schema, "invoice", doc.invoice, "amount_due") : cell(schema, "sales_order", doc.order, "total_amount")),
        numberCaption: numberCaption(words.number),
        productWord: words.product,
        printedAt: new Date().toLocaleString("en-GB", { day: "2-digit", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" }),
      }
    : null;

  return (
    <article aria-labelledby="doc-title" className="max-w-3xl print:max-w-none">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-2 print:hidden">
        <Link href={`/apps/${instance.id}/sales`} className="text-sm font-medium text-brand-700 hover:underline">
          ← All sales
        </Link>
        <PrintInvoiceButton data={invoiceData} autoOpen={autoPrint} />
      </div>

      <Card className="print:border-0 print:shadow-none">
        <header className="flex flex-wrap items-start justify-between gap-3 border-b border-slate-200 pb-4">
          <div>
            <h2 id="doc-title" className="text-lg font-semibold text-slate-900">
              {invoiceNumber ? `Invoice ${invoiceNumber}` : "Sales order"}
            </h2>
            <p className="mt-1 text-sm text-slate-500">{instance.label}</p>
          </div>
          <dl className="text-sm">
            <div className="flex gap-2">
              <dt className="text-slate-500">Date</dt>
              <dd className="font-medium">{formatDate(cell(schema, "sales_order", doc.order, "order_date"))}</dd>
            </div>
            <div className="flex gap-2">
              <dt className="text-slate-500">Status</dt>
              <dd>
                <Badge tone="success">{cellText(schema, "sales_order", doc.order, "status")}</Badge>
              </dd>
            </div>
            {doc.invoice && (
              <div className="flex gap-2">
                <dt className="text-slate-500">Payment</dt>
                <dd>
                  <Badge tone="warning">{cellText(schema, "invoice", doc.invoice, "status")}</Badge>
                </dd>
              </div>
            )}
          </dl>
        </header>

        <div className="py-4 text-sm">
          <p className="text-xs font-medium uppercase tracking-wide text-slate-500">Bill to</p>
          <p className="mt-1 font-medium text-slate-900">{doc.customer || "—"}</p>
        </div>

        <Table>
          <THead>
            <Th>{words.number}</Th>
            <Th>{words.product}</Th>
            <Th>Quantity</Th>
            <Th>Unit price</Th>
            <Th>Line total</Th>
          </THead>
          <tbody>
            {doc.lines.map((line) => (
              <tr key={String(line.id)} className="border-b border-slate-100 last:border-0">
                <Td className="font-mono text-xs">{numbers[cellText(schema, "sales_order_line", line, "sales_order_line_part")] || "—"}</Td>
                <Td>{parts[cellText(schema, "sales_order_line", line, "sales_order_line_part")] ?? "…"}</Td>
                <Td className="tabular-nums">{cellText(schema, "sales_order_line", line, "quantity")}</Td>
                <Td className="tabular-nums">{money(cell(schema, "sales_order_line", line, "unit_price"))}</Td>
                <Td className="tabular-nums">{money(cell(schema, "sales_order_line", line, "line_total"))}</Td>
              </tr>
            ))}
          </tbody>
        </Table>

        <p className="mt-4 text-right text-sm text-slate-600">
          {doc.invoice ? "Amount due" : "Total"}{" "}
          <strong className="ml-2 text-base tabular-nums text-slate-900" data-testid="amount-due">
            {money(
              doc.invoice
                ? cell(schema, "invoice", doc.invoice, "amount_due")
                : cell(schema, "sales_order", doc.order, "total_amount"),
            )}
          </strong>
        </p>
      </Card>

      <section aria-labelledby="movements-title" className="mt-6 print:hidden">
        <h3 id="movements-title" className="mb-2 text-sm font-semibold text-slate-700">
          Stock taken out for this sale
        </h3>
        {doc.movements.length === 0 ? (
          <p className="text-sm text-slate-500">No stock movements are linked to this sale.</p>
        ) : (
          <Table>
            <THead>
              <Th>When</Th>
              <Th>Product</Th>
              <Th>Warehouse</Th>
              <Th>Change</Th>
              <Th>Type</Th>
            </THead>
            <tbody>
              {doc.movements.map((m) => (
                <tr key={String(m.id)} className="border-b border-slate-100 last:border-0">
                  <Td>{formatDateTime(cell(schema, "stock_movement", m, "occurred_at"))}</Td>
                  <Td>{parts[cellText(schema, "stock_movement", m, "stock_movement_part")] ?? "…"}</Td>
                  <Td>{warehouses[cellText(schema, "stock_movement", m, "stock_movement_warehouse")] ?? "…"}</Td>
                  <Td className="tabular-nums">
                    <span data-testid="movement-change">{signed(cell(schema, "stock_movement", m, "quantity_delta"))}</span>
                  </Td>
                  <Td>{cellText(schema, "stock_movement", m, "movement_type")}</Td>
                </tr>
              ))}
            </tbody>
          </Table>
        )}
      </section>
    </article>
  );
}
