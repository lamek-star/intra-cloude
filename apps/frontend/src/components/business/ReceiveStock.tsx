"use client";

import Link from "next/link";
import { useId, useRef, useState, type FormEvent } from "react";
import {
  buildReceiveIntent,
  cellText,
  explainOperationError,
  listRecords,
  newIdempotencyKey,
  parseMoney,
  parseQuantity,
  postReceive,
} from "@/lib/business";
import { signed } from "@/lib/format";
import { Button, Card, ErrorBanner, Input, Label, LinkButton, Select } from "@/components/ui";
import { useBusiness } from "./BusinessApp";
import { useOptions } from "./hooks";
import ProductPicker, { type PickedProduct } from "./ProductPicker";

type Received = { productName: string; warehouseName: string; quantity: number; onHand: string | null; movementChange: string };

export default function ReceiveStock() {
  const { schema, instance } = useBusiness();
  const ids = { warehouse: useId(), quantity: useId(), supplier: useId(), cost: useId(), reference: useId() };
  const warehouses = useOptions("warehouse", "name");
  const suppliers = useOptions("supplier", "name");

  const [product, setProduct] = useState<PickedProduct | null>(null);
  const [warehouseId, setWarehouseId] = useState("");
  const [quantity, setQuantity] = useState("");
  const [supplierId, setSupplierId] = useState("");
  const [unitCost, setUnitCost] = useState("");
  const [reference, setReference] = useState("");
  const [problems, setProblems] = useState<string[]>([]);
  const [failure, setFailure] = useState<string | null>(null);
  const [working, setWorking] = useState(false);
  const [received, setReceived] = useState<Received | null>(null);
  // One idempotency key per *unchanged* submission: retrying after a dropped connection replays the
  // first result instead of receiving twice. Editing anything starts a new operation.
  const keyRef = useRef<string | null>(null);

  function edit<T>(setter: (value: T) => void) {
    return (value: T) => {
      keyRef.current = null;
      setFailure(null);
      setter(value);
    };
  }

  async function submit(e: FormEvent) {
    e.preventDefault();
    const found: string[] = [];
    const qty = parseQuantity(quantity);
    if (!product) found.push("Choose the product you are receiving.");
    if (!warehouseId) found.push("Choose the warehouse it is going into.");
    if (qty === null) found.push("Enter a whole quantity of at least 1.");
    let cost: number | undefined;
    if (supplierId && unitCost.trim()) {
      const cents = parseMoney(unitCost);
      if (cents === null) found.push("Enter the unit cost as an amount like 2.50.");
      else cost = cents;
    }
    setProblems(found);
    if (found.length > 0 || !product || qty === null) return;

    setWorking(true);
    setFailure(null);
    keyRef.current ??= newIdempotencyKey();
    try {
      const intent = buildReceiveIntent({
        partId: product.id,
        warehouseId,
        quantity: qty,
        supplierId: supplierId || undefined,
        unitCostCents: cost,
        reference,
      });
      const result = await postReceive(schema, intent, keyRef.current);
      // The balance is READ BACK from the server: the database ledger decided it.
      const inventory = await listRecords(schema, "inventory", {
        filters: { part: product.id, warehouse: warehouseId },
        limit: 1,
      });
      const movement = result.results.find((r) => r.model === schema.modelId("stock_movement"));
      setReceived({
        productName: product.name,
        warehouseName: warehouses.options.find((o) => o.id === warehouseId)?.label ?? "the warehouse",
        quantity: qty,
        onHand: inventory.results[0] ? cellText(schema, "inventory", inventory.results[0], "quantity_on_hand") : null,
        movementChange: movement ? signed(movement.record[schema.id("stock_movement", "quantity_delta")]) : signed(qty),
      });
    } catch (err) {
      setFailure(explainOperationError(err));
    } finally {
      setWorking(false);
    }
  }

  function startAnother() {
    keyRef.current = null;
    setReceived(null);
    setProduct(null);
    setQuantity("");
    setUnitCost("");
    setReference("");
    setProblems([]);
  }

  if (received) {
    return (
      <Card>
        <div role="status">
          <h2 className="text-base font-semibold text-slate-900">Stock received</h2>
          <p className="mt-2 text-sm text-slate-700">
            Received <strong>{received.quantity}</strong> × <strong>{received.productName}</strong> into{" "}
            <strong>{received.warehouseName}</strong>.
          </p>
          <dl className="mt-3 grid max-w-sm grid-cols-2 gap-y-1 text-sm">
            <dt className="text-slate-500">On hand now</dt>
            <dd className="font-medium tabular-nums" data-testid="on-hand-now">
              {received.onHand ?? "—"}
            </dd>
            <dt className="text-slate-500">Movement recorded</dt>
            <dd className="font-medium tabular-nums">{received.movementChange}</dd>
          </dl>
        </div>
        <div className="mt-4 flex gap-2">
          <Button onClick={startAnother}>Receive more</Button>
          <LinkButton href={`/apps/${instance.id}/inventory`} variant="secondary">
            View stock
          </LinkButton>
        </div>
      </Card>
    );
  }

  const noSetup = !warehouses.loading && warehouses.options.length === 0;

  return (
    <section aria-labelledby="receive-title">
      <h2 id="receive-title" className="text-base font-semibold text-slate-900">
        Receive stock
      </h2>
      <p className="mb-4 text-sm text-slate-500">
        Record goods arriving. The quantity is added to your stock in one step; if anything fails, nothing is changed.
      </p>
      {noSetup && (
        <div className="mb-4">
          <ErrorBanner message="Add a warehouse first, so there is somewhere to put the stock." />
          <div className="mt-2">
            <Link href={`/apps/${instance.id}/warehouses`} className="text-sm font-medium text-brand-700 hover:underline">
              Go to Warehouses
            </Link>
          </div>
        </div>
      )}
      <form onSubmit={submit} className="max-w-xl space-y-4" noValidate>
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

        <ProductPicker label="Product" value={product} onChange={edit(setProduct)} />

        <div>
          <Label htmlFor={ids.warehouse}>Warehouse</Label>
          <Select id={ids.warehouse} value={warehouseId} onChange={(e) => edit(setWarehouseId)(e.target.value)}>
            <option value="">Choose a warehouse…</option>
            {warehouses.options.map((o) => (
              <option key={o.id} value={o.id}>
                {o.label}
              </option>
            ))}
          </Select>
        </div>

        <div>
          <Label htmlFor={ids.quantity}>Quantity</Label>
          <Input
            id={ids.quantity}
            inputMode="numeric"
            value={quantity}
            onChange={(e) => edit(setQuantity)(e.target.value)}
            className="max-w-[10rem]"
          />
        </div>

        <fieldset className="space-y-3 rounded-lg border border-slate-200 p-3">
          <legend className="px-1 text-xs font-medium text-slate-500">Optional</legend>
          <div>
            <Label htmlFor={ids.supplier}>Supplier</Label>
            <Select id={ids.supplier} value={supplierId} onChange={(e) => edit(setSupplierId)(e.target.value)}>
              <option value="">No supplier</option>
              {suppliers.options.map((o) => (
                <option key={o.id} value={o.id}>
                  {o.label}
                </option>
              ))}
            </Select>
            <p className="mt-1 text-xs text-slate-500">Choosing a supplier also records a received purchase order.</p>
          </div>
          {supplierId && (
            <div>
              <Label htmlFor={ids.cost}>Unit cost</Label>
              <Input
                id={ids.cost}
                inputMode="decimal"
                value={unitCost}
                onChange={(e) => edit(setUnitCost)(e.target.value)}
                className="max-w-[10rem]"
              />
            </div>
          )}
          <div>
            <Label htmlFor={ids.reference}>Reference</Label>
            <Input
              id={ids.reference}
              value={reference}
              placeholder="Delivery note or invoice number"
              onChange={(e) => edit(setReference)(e.target.value)}
            />
          </div>
        </fieldset>

        <Button type="submit" disabled={working || noSetup}>
          {working ? "Receiving…" : "Confirm receive"}
        </Button>
      </form>
    </section>
  );
}
