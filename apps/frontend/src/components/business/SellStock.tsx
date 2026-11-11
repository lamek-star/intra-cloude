"use client";

import Link from "next/link";
import { useId, useRef, useState, type FormEvent } from "react";
import {
  buildSaleIntent,
  cellText,
  explainOperationError,
  formatMoney,
  listRecords,
  newIdempotencyKey,
  newInvoiceNumber,
  parseMoney,
  parseQuantity,
  postSale,
  saleTotalCents,
  type SaleLine,
} from "@/lib/business";
import { Printer } from "lucide-react";
import { Button, Card, ErrorBanner, Input, Label, LinkButton, Select } from "@/components/ui";
import { useBusiness } from "./BusinessApp";
import { useOptions } from "./hooks";
import ProductPicker, { type PickedProduct } from "./ProductPicker";

type LineDraft = { key: number; product: PickedProduct | null; warehouseId: string; quantity: string; price: string };

type Sold = {
  orderId: string;
  invoiceNumber: string;
  customerName: string;
  lines: { name: string; warehouseName: string; quantity: number; unitPrice: string; onHand: string | null }[];
  total: string;
};

let nextKey = 1;
const blankLine = (): LineDraft => ({ key: nextKey++, product: null, warehouseId: "", quantity: "", price: "" });

export default function SellStock() {
  const { schema, instance } = useBusiness();
  const customerId = useId();
  const customers = useOptions("customer", "name");
  const warehouses = useOptions("warehouse", "name");

  const [customer, setCustomer] = useState("");
  const [lines, setLines] = useState<LineDraft[]>([blankLine()]);
  const [problems, setProblems] = useState<string[]>([]);
  const [failure, setFailure] = useState<string | null>(null);
  const [working, setWorking] = useState(false);
  const [sold, setSold] = useState<Sold | null>(null);
  // One idempotency key AND one invoice number per unchanged sale: a retry after a dropped
  // connection replays the first sale rather than selling twice. Any edit starts a new sale.
  const keyRef = useRef<string | null>(null);
  const invoiceRef = useRef<string | null>(null);

  function touch() {
    keyRef.current = null;
    invoiceRef.current = null;
    setFailure(null);
  }

  function updateLine(key: number, patch: Partial<LineDraft>) {
    touch();
    setLines((current) => current.map((l) => (l.key === key ? { ...l, ...patch } : l)));
  }

  function pickProduct(key: number, product: PickedProduct | null) {
    // Prefill the price from the product's list price; the shop can change it.
    const list = product ? cellText(schema, "part", product.row, "list_price") : "";
    const cents = list ? parseMoney(Number(list).toFixed(2)) : null;
    updateLine(key, { product, ...(product && cents !== null ? { price: formatMoney(cents) } : {}) });
  }

  function parsedLines(): { lines: SaleLine[]; problems: string[] } {
    const found: string[] = [];
    const parsed: SaleLine[] = [];
    lines.forEach((line, index) => {
      const n = index + 1;
      const qty = parseQuantity(line.quantity);
      const cents = parseMoney(line.price);
      if (!line.product) found.push(`Item ${n}: choose a product.`);
      if (!line.warehouseId) found.push(`Item ${n}: choose the warehouse it is sold from.`);
      if (qty === null) found.push(`Item ${n}: enter a whole quantity of at least 1.`);
      if (cents === null) found.push(`Item ${n}: enter the unit price as an amount like 15.00.`);
      if (line.product && line.warehouseId && qty !== null && cents !== null) {
        parsed.push({ partId: line.product.id, warehouseId: line.warehouseId, quantity: qty, unitPriceCents: cents });
      }
    });
    return { lines: parsed, problems: found };
  }

  const preview = parsedLines();
  const total = preview.problems.length === 0 ? formatMoney(saleTotalCents(preview.lines)) : null;

  async function submit(e: FormEvent) {
    e.preventDefault();
    const { lines: valid, problems: found } = parsedLines();
    if (!customer) found.unshift("Choose the customer.");
    setProblems(found);
    if (found.length > 0) return;

    setWorking(true);
    setFailure(null);
    keyRef.current ??= newIdempotencyKey();
    invoiceRef.current ??= newInvoiceNumber();
    try {
      const intent = buildSaleIntent({ customerId: customer, lines: valid, invoiceNumber: invoiceRef.current });
      const result = await postSale(schema, intent, keyRef.current);
      const order = result.results.find((r) => r.ref === "order");
      if (!order) throw new Error("The sale was recorded but its order could not be found.");
      // Resulting stock is READ BACK from the server (the database ledger decided it).
      const done = await Promise.all(
        lines.map(async (line, i) => {
          const inventory = await listRecords(schema, "inventory", {
            filters: { part: valid[i].partId, warehouse: valid[i].warehouseId },
            limit: 1,
          });
          return {
            name: line.product?.name ?? "",
            warehouseName: warehouses.options.find((o) => o.id === valid[i].warehouseId)?.label ?? "",
            quantity: valid[i].quantity,
            unitPrice: formatMoney(valid[i].unitPriceCents),
            onHand: inventory.results[0] ? cellText(schema, "inventory", inventory.results[0], "quantity_on_hand") : null,
          };
        }),
      );
      setSold({
        orderId: String(order.record.id),
        invoiceNumber: invoiceRef.current,
        customerName: customers.options.find((o) => o.id === customer)?.label ?? "",
        lines: done,
        total: formatMoney(saleTotalCents(valid)),
      });
    } catch (err) {
      setFailure(explainOperationError(err));
    } finally {
      setWorking(false);
    }
  }

  function newSale() {
    keyRef.current = null;
    invoiceRef.current = null;
    setSold(null);
    setCustomer("");
    setLines([blankLine()]);
    setProblems([]);
  }

  if (sold) {
    return (
      <Card>
        <div role="status">
          <h2 className="text-base font-semibold text-slate-900">Sale complete</h2>
          <p className="mt-1 text-sm text-slate-600">
            Invoice <strong>{sold.invoiceNumber}</strong> for <strong>{sold.customerName}</strong> — total{" "}
            <strong>{sold.total}</strong>.
          </p>
          <ul className="mt-3 space-y-1 text-sm text-slate-700">
            {sold.lines.map((line, i) => (
              <li key={i}>
                {line.quantity} × {line.name} @ {line.unitPrice} from {line.warehouseName} — on hand now{" "}
                <strong data-testid="on-hand-after-sale">{line.onHand ?? "—"}</strong>
              </li>
            ))}
          </ul>
        </div>
        <div className="mt-4 flex gap-2">
          <LinkButton href={`/apps/${instance.id}/sales/${sold.orderId}?print=1`} variant="primary">
            <Printer className="h-4 w-4" aria-hidden="true" />
            Print invoice
          </LinkButton>
          <LinkButton href={`/apps/${instance.id}/sales/${sold.orderId}`} variant="secondary">
            Open sales document
          </LinkButton>
          <Button variant="secondary" onClick={newSale}>
            New sale
          </Button>
        </div>
      </Card>
    );
  }

  const noSetup = (!customers.loading && customers.options.length === 0) || (!warehouses.loading && warehouses.options.length === 0);

  return (
    <section aria-labelledby="sell-title">
      <h2 id="sell-title" className="text-base font-semibold text-slate-900">
        New sale
      </h2>
      <p className="mb-4 text-sm text-slate-500">
        Sell to a customer. The order, its lines, the stock taken out and the invoice are recorded together — if anything fails
        (for example not enough stock), nothing is changed.
      </p>
      {noSetup && (
        <div className="mb-4">
          <ErrorBanner message="You need at least one customer and one warehouse before you can sell." />
          <div className="mt-2 flex gap-4 text-sm font-medium text-brand-700">
            <Link href={`/apps/${instance.id}/customers`} className="hover:underline">
              Go to Customers
            </Link>
            <Link href={`/apps/${instance.id}/warehouses`} className="hover:underline">
              Go to Warehouses
            </Link>
          </div>
        </div>
      )}
      <form onSubmit={submit} className="max-w-3xl space-y-5" noValidate>
        {problems.length > 0 && (
          <div role="alert" className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
            <ul className="list-disc pl-4">
              {problems.map((p) => (
                <li key={p}>{p}</li>
              ))}
            </ul>
          </div>
        )}
        {failure && <ErrorBanner message={failure} />}

        <div className="max-w-sm">
          <Label htmlFor={customerId}>Customer</Label>
          <Select
            id={customerId}
            value={customer}
            onChange={(e) => {
              touch();
              setCustomer(e.target.value);
            }}
          >
            <option value="">Choose a customer…</option>
            {customers.options.map((o) => (
              <option key={o.id} value={o.id}>
                {o.label}
              </option>
            ))}
          </Select>
        </div>

        {lines.map((line, index) => (
          <LineEditor
            key={line.key}
            index={index}
            line={line}
            warehouses={warehouses.options}
            canRemove={lines.length > 1}
            onPick={(product) => pickProduct(line.key, product)}
            onChange={(patch) => updateLine(line.key, patch)}
            onRemove={() => {
              touch();
              setLines((current) => current.filter((l) => l.key !== line.key));
            }}
          />
        ))}

        <div>
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={() => {
              touch();
              setLines((current) => [...current, blankLine()]);
            }}
          >
            Add another item
          </Button>
        </div>

        <div className="flex items-center gap-4 border-t border-slate-200 pt-4">
          <p className="text-sm text-slate-600">
            Total: <strong className="tabular-nums text-slate-900">{total ?? "—"}</strong>
          </p>
          <Button type="submit" disabled={working || noSetup}>
            {working ? "Recording sale…" : "Confirm sale"}
          </Button>
        </div>
      </form>
    </section>
  );
}

function LineEditor({
  index,
  line,
  warehouses,
  canRemove,
  onPick,
  onChange,
  onRemove,
}: {
  index: number;
  line: LineDraft;
  warehouses: { id: string; label: string }[];
  canRemove: boolean;
  onPick: (product: PickedProduct | null) => void;
  onChange: (patch: Partial<LineDraft>) => void;
  onRemove: () => void;
}) {
  const ids = { warehouse: useId(), quantity: useId(), price: useId() };
  return (
    <fieldset className="space-y-3 rounded-lg border border-slate-200 p-3">
      <legend className="px-1 text-xs font-medium text-slate-500">Item {index + 1}</legend>
      <ProductPicker label={`Product (item ${index + 1})`} value={line.product} onChange={onPick} />
      <div className="grid gap-3 sm:grid-cols-3">
        <div>
          <Label htmlFor={ids.warehouse}>Warehouse</Label>
          <Select id={ids.warehouse} value={line.warehouseId} onChange={(e) => onChange({ warehouseId: e.target.value })}>
            <option value="">Choose…</option>
            {warehouses.map((o) => (
              <option key={o.id} value={o.id}>
                {o.label}
              </option>
            ))}
          </Select>
        </div>
        <div>
          <Label htmlFor={ids.quantity}>Quantity</Label>
          <Input id={ids.quantity} inputMode="numeric" value={line.quantity} onChange={(e) => onChange({ quantity: e.target.value })} />
        </div>
        <div>
          <Label htmlFor={ids.price}>Unit price</Label>
          <Input id={ids.price} inputMode="decimal" value={line.price} onChange={(e) => onChange({ price: e.target.value })} />
        </div>
      </div>
      {canRemove && (
        <Button type="button" variant="ghost" size="sm" onClick={onRemove}>
          Remove item {index + 1}
        </Button>
      )}
    </fieldset>
  );
}
