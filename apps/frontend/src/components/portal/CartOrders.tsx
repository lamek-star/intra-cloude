"use client";

import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Clock, Coins, Film, Gift, ShoppingBag, Trash2, Usb } from "lucide-react";
import { formatBytes } from "@/lib/movies";
import { portalApi, type OrderPreview, type PortalMe, type PortalOrder, type PortalTitle } from "@/lib/portal";
import { portalMessage, portalStyle as ui } from "./Portal";

/** The cart: what the customer wants, the price with their rewards, and "Order". The counter copies it to their USB. */
export function CartScreen({
  shopId,
  customer,
  items,
  onRemove,
  onOrdered,
  onBrowse,
}: {
  shopId: string;
  customer: PortalMe;
  items: PortalTitle[];
  onRemove: (id: string) => void;
  onOrdered: () => void;
  onBrowse: () => void;
}) {
  const [usePoints, setUsePoints] = useState(customer.points > 0);
  const [preview, setPreview] = useState<OrderPreview | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const ids = items.map((t) => t.id).join(",");

  useEffect(() => {
    if (!ids) return;
    let live = true;
    portalApi
      .preview(shopId, ids.split(","), usePoints)
      .then((p) => live && setPreview(p))
      .catch((err) => live && setError(portalMessage(err)));
    return () => {
      live = false;
    };
  }, [shopId, ids, usePoints]);

  if (items.length === 0) {
    return (
      <div className="mt-16 text-center">
        <span className="mx-auto grid h-14 w-14 place-items-center rounded-2xl bg-[#141a2b] text-slate-400">
          <ShoppingBag className="h-7 w-7" />
        </span>
        <p className="mt-4 font-semibold">Your cart is empty</p>
        <p className="mt-1 text-sm text-slate-400">Tap a cover, then Add to cart.</p>
        <button className={`${ui.secondary} mt-5`} onClick={onBrowse}>
          <Film className="h-4 w-4" /> Browse the films
        </button>
      </div>
    );
  }

  const size = items.reduce((a, t) => a + t.size_bytes, 0);
  async function order() {
    setBusy(true);
    setError(null);
    try {
      await portalApi.order(shopId, items.map((t) => t.id), usePoints);
      onOrdered();
    } catch (err) {
      setError(portalMessage(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <h2 className="text-lg font-bold">Your cart</h2>
      <ul className="mt-3 flex flex-col divide-y divide-[#252e47] rounded-2xl border border-[#252e47] bg-[#141a2b]">
        {items.map((t) => {
          const free = preview?.free_titles.includes(t.title);
          return (
            <li key={t.id} className="flex items-center gap-3 px-4 py-3">
              <span className="min-w-0 flex-1">
                <span className="block truncate font-semibold">{t.title}</span>
                <span className="block text-xs text-slate-500">
                  {t.category} · {formatBytes(t.size_bytes)}
                </span>
              </span>
              {free ? <span className="rounded-full bg-emerald-400/15 px-2.5 py-0.5 text-xs font-bold text-emerald-200">FREE</span> : <span className="font-bold text-amber-200">{t.price}</span>}
              <button onClick={() => onRemove(t.id)} className="rounded-lg p-2 text-slate-500 hover:text-red-300" aria-label={`Remove ${t.title}`}>
                <Trash2 className="h-4 w-4" />
              </button>
            </li>
          );
        })}
      </ul>

      {customer.points > 0 && (
        <label className="mt-3 flex items-center gap-3 rounded-2xl border border-[#252e47] bg-[#141a2b] px-4 py-3">
          <input type="checkbox" className="h-5 w-5 accent-amber-400" checked={usePoints} onChange={(e) => setUsePoints(e.target.checked)} />
          <span className="flex-1 text-sm">
            Use my points <span className="text-slate-500">({customer.points} available, 1 point = 1 credit)</span>
          </span>
          <Coins className="h-5 w-5 text-amber-300" />
        </label>
      )}

      {preview && (
        <dl className="mt-3 grid grid-cols-[1fr_auto] gap-y-1.5 rounded-2xl border border-[#252e47] bg-[#141a2b] px-4 py-3 text-sm">
          <dt className="text-slate-400">Titles</dt>
          <dd>{preview.subtotal}</dd>
          {preview.discount > 0 && (
            <>
              <dt className="flex items-center gap-1.5 text-emerald-300">
                <Gift className="h-4 w-4" /> Free title{preview.free_titles.length > 1 ? "s" : ""}
              </dt>
              <dd className="text-emerald-300">-{preview.discount}</dd>
            </>
          )}
          {preview.points_used > 0 && (
            <>
              <dt className="text-amber-200">Points</dt>
              <dd className="text-amber-200">-{preview.points_used}</dd>
            </>
          )}
          <dt className="mt-1 border-t border-[#252e47] pt-2 font-bold">To pay at the counter</dt>
          <dd className="mt-1 border-t border-[#252e47] pt-2 text-xl font-extrabold">
            {preview.total} <span className="text-xs font-semibold text-slate-400">credits</span>
          </dd>
        </dl>
      )}
      <p className="mt-3 flex items-start gap-2 text-xs text-slate-400">
        <Usb className="mt-0.5 h-4 w-4 shrink-0" /> Bring a USB drive with {formatBytes(size)} free. Pay with your IF Pay wallet or cash at the counter; the
        shop copies the films for you.
      </p>
      {error && (
        <p className="mt-3 rounded-xl bg-red-400/10 px-4 py-3 text-sm text-red-200" role="alert">
          {error}
        </p>
      )}
      <button className={`${ui.primary} mt-4`} disabled={busy || customer.status !== "approved"} onClick={() => void order()}>
        {customer.status !== "approved" ? "Waiting for the shop to approve you" : busy ? "Ordering..." : "Order"}
      </button>
    </div>
  );
}

const ORDER_STATUS: Record<PortalOrder["status"], [string, string]> = {
  ordered: ["Waiting at the counter", "border-violet-400/30 bg-violet-400/10 text-violet-200"],
  awaiting_payment: ["Paying at the counter", "border-amber-400/30 bg-amber-400/10 text-amber-200"],
  paid: ["Copying to your USB", "border-sky-400/30 bg-sky-400/10 text-sky-200"],
  done: ["Ready", "border-emerald-400/30 bg-emerald-400/10 text-emerald-200"],
  cancelled: ["Cancelled", "border-[#323c5a] text-slate-400"],
};

/** The customer's orders: show the number at the counter; cancel one still waiting. */
export function OrdersScreen({ shopId, onChanged }: { shopId: string; onChanged: () => void }) {
  const orders = useQuery({
    queryKey: ["portal", shopId, "orders"],
    queryFn: () => portalApi.orders(shopId),
    refetchInterval: (q) => (q.state.data?.some((o) => o.status !== "done" && o.status !== "cancelled") ? 4000 : false),
  });
  const [error, setError] = useState<string | null>(null);

  async function cancel(id: string) {
    setError(null);
    try {
      await portalApi.cancelOrder(shopId, id);
      await orders.refetch();
      onChanged();
    } catch (err) {
      setError(portalMessage(err));
    }
  }

  if (orders.isLoading) return <p className="mt-8 text-center text-sm text-slate-500">Loading...</p>;
  if (!orders.data?.length) return <p className="mt-16 text-center text-sm text-slate-400">No orders yet.</p>;
  return (
    <div>
      <h2 className="text-lg font-bold">Your orders</h2>
      {error && <p className="mt-2 text-sm text-red-300">{error}</p>}
      <ul className="mt-3 flex flex-col gap-3">
        {orders.data.map((o) => {
          const [label, tone] = ORDER_STATUS[o.status];
          return (
            <li key={o.id} className="rounded-2xl border border-[#252e47] bg-[#141a2b] p-4">
              <div className="flex items-center gap-2">
                <span className="font-mono text-sm font-bold tracking-wider">{o.number}</span>
                <span className={`ml-auto rounded-full border px-2.5 py-0.5 text-[11px] font-semibold ${tone}`}>{label}</span>
              </div>
              <p className="mt-2 text-sm text-slate-300">{o.lines.map((l) => l.title + (l.free ? " (free)" : "")).join(", ")}</p>
              <p className="mt-2 flex items-center gap-2 text-xs text-slate-500">
                <Clock className="h-3.5 w-3.5" /> {new Date(o.created_at).toLocaleString()}
                <span className="ml-auto text-sm font-bold text-slate-100">
                  {o.total} credits{o.status === "ordered" ? " (estimate)" : ""}
                </span>
              </p>
              {o.status === "ordered" && (
                <>
                  <p className="mt-3 rounded-xl bg-[#0f1422] px-3 py-2 text-xs text-slate-300">Show this number at the counter with your USB drive.</p>
                  <button className="mt-2 text-xs text-slate-400 hover:text-red-300" onClick={() => void cancel(o.id)}>
                    Cancel this order
                  </button>
                </>
              )}
            </li>
          );
        })}
      </ul>
    </div>
  );
}
