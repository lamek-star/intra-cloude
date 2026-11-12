"use client";

import { useEffect, useId, useState } from "react";
import { Banknote, Check, CircleAlert, Clock, Coins, RefreshCw, ShieldCheck, Trash2, Usb, Wallet, X } from "lucide-react";
import { copyProgress, formatBytes, movies, qrDataUrl, type CounterCustomer, type Destination, type MovieShop, type MovieTitle, type Sale } from "@/lib/movies";
import { dark, DarkDialog, message } from "./Dialogs";

/** The drives a sold title can go to, as the media agent sees them now (refreshed every 5 s): plug in, it appears. */
function useDestinations(shopId: string) {
  const [drives, setDrives] = useState<Destination[]>([]);
  const [destination, setDestination] = useState("");
  useEffect(() => {
    let alive = true;
    const load = () =>
      movies
        .destinations(shopId)
        .then((r) => {
          if (!alive) return;
          setDrives(r.drives);
          setDestination((current) => (r.drives.some((d) => d.root === current) ? current : (r.drives[0]?.root ?? "")));
        })
        .catch(() => undefined);
    load();
    const t = window.setInterval(load, 5000);
    return () => {
      alive = false;
      window.clearInterval(t);
    };
  }, [shopId]);
  return { drives, destination, setDestination };
}

function driveLabel(d: Destination): string {
  return `${d.label ? `${d.label} (${d.root.replace("\\", "")})` : d.root} · ${formatBytes(d.free_bytes)} free${d.kind === "removable" ? " · USB" : ""}`;
}

/** The cart: the titles chosen for one customer, their drive, how they pay. Docked on the right of the catalogue. */
export function CartPanel({
  shop,
  items,
  onRemove,
  onClear,
  onSold,
}: {
  shop: MovieShop;
  items: MovieTitle[];
  onRemove: (id: string) => void;
  onClear: () => void;
  onSold: (sale: Sale) => void;
}) {
  const { drives, destination, setDestination } = useDestinations(shop.id);
  const [customer, setCustomer] = useState("");
  const [phone, setPhone] = useState("");
  const [matches, setMatches] = useState<CounterCustomer[]>([]);
  const [member, setMember] = useState<CounterCustomer | null>(null);
  const [usePoints, setUsePoints] = useState(false);
  const [method, setMethod] = useState<Sale["method"]>("ifpay");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const ids = { drive: useId(), customer: useId(), phone: useId() };

  // The portal customer, found by phone number as the person at the counter types it.
  useEffect(() => {
    const digits = phone.replace(/\D/g, "");
    if (member || digits.length < 6) return;
    let alive = true;
    const timer = window.setTimeout(() => {
      movies
        .findCustomer(shop.id, digits)
        .then((r) => alive && setMatches(r.results))
        .catch(() => alive && setMatches([]));
    }, 300);
    return () => {
      alive = false;
      window.clearTimeout(timer);
    };
  }, [phone, member, shop.id]);

  // Matches show only for the number typed now (6 digits or more) and while no customer is chosen.
  const shown = member || phone.replace(/\D/g, "").length < 6 ? [] : matches;
  const total = items.reduce((a, t) => a + t.price, 0);
  const size = items.reduce((a, t) => a + t.size_bytes, 0);
  const drive = drives.find((d) => d.root === destination);
  const tooBig = drive?.free_bytes != null && size > drive.free_bytes;

  async function charge() {
    setBusy(true);
    setError(null);
    try {
      const sale = await movies.createSale(shop.id, {
        titles: items.map((t) => t.id),
        destination,
        method,
        customer_name: customer.trim(),
        ...(member ? { customer: member.id, use_points: usePoints } : {}),
      });
      onSold(sale);
      setCustomer("");
      setPhone("");
      setMember(null);
      setUsePoints(false);
    } catch (err) {
      setError(message(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <aside aria-label="Cart" className="flex flex-col self-start rounded-2xl border border-[#252e47] bg-[#141a2b] p-4 lg:sticky lg:top-4">
      <div className="flex items-center justify-between">
        <p className="text-sm font-bold">
          Cart <span className="ml-1 rounded-full bg-amber-400 px-2 py-0.5 text-xs text-amber-950">{items.length}</span>
        </p>
        <button onClick={onClear} className="text-xs text-slate-400 hover:text-white">
          Clear
        </button>
      </div>
      <ul className="mt-3 flex max-h-64 flex-col gap-1 overflow-y-auto">
        {items.map((t) => (
          <li key={t.id} className="flex items-center gap-2 rounded-lg px-1 py-1.5 text-sm hover:bg-white/5">
            <span className="min-w-0 flex-1 truncate">{t.title}</span>
            <span className="text-xs font-bold text-amber-200">{t.price}</span>
            <button onClick={() => onRemove(t.id)} aria-label={`Remove ${t.title}`} className="rounded p-1 text-slate-500 hover:text-red-300">
              <Trash2 className="h-3.5 w-3.5" />
            </button>
          </li>
        ))}
      </ul>
      <div className="mt-3 flex items-baseline justify-between border-t border-[#252e47] pt-3">
        <span className="text-xs text-slate-400">{formatBytes(size)}</span>
        <span className="text-lg font-extrabold">
          {total} <span className="text-xs font-semibold text-slate-400">credits</span>
        </span>
      </div>
      <label htmlFor={ids.drive} className={`${dark.label} mt-3`}>
        Copy to the customer&apos;s drive
      </label>
      <select id={ids.drive} className={dark.input} value={destination} onChange={(e) => setDestination(e.target.value)}>
        {drives.length === 0 && <option value="">Plug in the customer&apos;s USB...</option>}
        {drives.map((d) => (
          <option key={d.root} value={d.root}>
            {driveLabel(d)}
          </option>
        ))}
      </select>
      {tooBig && <p className="mt-1 text-xs text-red-300">Not enough room on this drive.</p>}
      <label htmlFor={ids.phone} className={`${dark.label} mt-3`}>
        Portal customer (optional)
      </label>
      {member ? (
        <div className="rounded-lg border border-teal-400/40 bg-teal-400/10 p-2.5 text-sm">
          <div className="flex items-center gap-2">
            <span className="min-w-0 flex-1 truncate font-semibold text-teal-100">
              {member.name} <span className="font-normal text-slate-400">· ...{member.phone_end}</span>
            </span>
            <button onClick={() => setMember(null)} className="text-xs text-slate-400 hover:text-white">
              Change
            </button>
          </div>
          <label className="mt-2 flex items-center gap-2 text-xs text-slate-300">
            <input type="checkbox" checked={usePoints} disabled={member.points === 0} onChange={(e) => setUsePoints(e.target.checked)} />
            Use their {member.points} points
          </label>
          <p className="mt-1 text-[11px] text-slate-500">Their free titles and points are worked out when you charge.</p>
        </div>
      ) : (
        <>
          <input
            id={ids.phone}
            className={dark.input}
            inputMode="tel"
            maxLength={20}
            value={phone}
            onChange={(e) => setPhone(e.target.value)}
            placeholder="Phone number, for their points"
          />
          {shown.length > 0 && (
            <ul className="mt-1 overflow-hidden rounded-lg border border-[#323c5a]" aria-label="Matching customers">
              {shown.map((m) => (
                <li key={m.id}>
                  <button
                    className="flex w-full items-center gap-2 px-2.5 py-2 text-left text-sm hover:bg-white/5"
                    onClick={() => {
                      setMember(m);
                      setMatches([]);
                    }}
                  >
                    <span className="min-w-0 flex-1 truncate">{m.name}</span>
                    <span className="text-xs text-slate-500">...{m.phone_end}</span>
                    <span className="text-xs font-bold text-amber-200">{m.points} pts</span>
                  </button>
                </li>
              ))}
            </ul>
          )}
          <label htmlFor={ids.customer} className={`${dark.label} mt-3`}>
            Or just a name (optional)
          </label>
          <input id={ids.customer} className={dark.input} maxLength={120} value={customer} onChange={(e) => setCustomer(e.target.value)} placeholder="Name" />
        </>
      )}
      <div className="mt-3 grid grid-cols-2 gap-2" role="radiogroup" aria-label="Payment">
        {(
          [
            ["ifpay", Wallet, "IF Pay"],
            ["cash", Banknote, "Cash"],
          ] as const
        ).map(([value, Icon, label]) => (
          <button
            key={value}
            role="radio"
            aria-checked={method === value}
            onClick={() => setMethod(value)}
            className={`inline-flex h-10 items-center justify-center gap-2 rounded-lg border text-sm font-semibold ${method === value ? (value === "ifpay" ? "border-teal-400 bg-teal-400/10 text-teal-200" : "border-amber-400 bg-amber-400/10 text-amber-200") : "border-[#323c5a] text-slate-300"}`}
          >
            <Icon className="h-4 w-4" /> {label}
          </button>
        ))}
      </div>
      {error && <p className="mt-3 text-sm text-red-300">{error}</p>}
      <button className={`${dark.amber} mt-4 h-11 w-full`} disabled={busy || !destination || items.length === 0 || tooBig} onClick={() => void charge()}>
        <Coins className="h-4 w-4" /> {busy ? "Starting..." : member ? "Charge with their rewards" : method === "ifpay" ? `Charge ${total} credits` : `Take ${total} in cash`}
      </button>
    </aside>
  );
}

const COPY_LABEL = { waiting: "Waiting", copying: "Copying", copied: "Copied", failed: "Failed" } as const;

/** One sale from payment to copied: the IF Pay QR code while it waits, then each title's copy. */
export function SaleDialog({ saleId, initial, onClose }: { saleId: string; initial?: Sale; onClose: () => void }) {
  const [sale, setSale] = useState<Sale | null>(initial ?? null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    let timer = 0;
    const load = async () => {
      try {
        const s = await movies.sale(saleId);
        if (!alive) return;
        setSale(s);
        if (s.status === "ordered" || s.status === "awaiting_payment" || s.status === "paid") timer = window.setTimeout(load, 2000);
      } catch (err) {
        if (alive) setError(message(err));
      }
    };
    timer = window.setTimeout(load, initial ? 1500 : 0);
    return () => {
      alive = false;
      window.clearTimeout(timer);
    };
  }, [saleId, initial]);

  async function act(action: "cash" | "cancel" | "retry") {
    setError(null);
    try {
      setSale(await movies.saleAction(saleId, action));
    } catch (err) {
      setError(message(err));
    }
  }

  if (!sale) return null;
  const progress = copyProgress(sale);
  const qr = sale.pay?.qr_svg ? qrDataUrl(sale.pay.qr_svg) : null;
  return (
    <DarkDialog title={`Sale ${sale.number}`} onClose={onClose} wide>
      <div className="grid gap-6 md:grid-cols-[1fr_260px]">
        <div>
          <p className="text-xs font-semibold tracking-wider text-slate-500 uppercase">Titles</p>
          <ul className="mt-2 flex flex-col">
            {sale.lines.map((l) => {
              const pct = l.copy_status === "copied" ? 1 : l.size_bytes ? Math.min(1, l.copied_bytes / l.size_bytes) : 0;
              return (
                <li key={l.id} className="border-b border-[#252e47] py-2.5">
                  <div className="flex items-center gap-2 text-sm">
                    <span className="min-w-0 flex-1 truncate font-semibold">
                      {l.title}
                      {l.free && <span className="ml-2 rounded-full bg-emerald-400/15 px-2 py-px text-[10.5px] font-bold text-emerald-200">FREE</span>}
                    </span>
                    <span className="text-xs text-slate-500">
                      {l.category} · {formatBytes(l.size_bytes)} · <b className="text-amber-200">{l.price}</b>
                    </span>
                  </div>
                  {sale.status !== "ordered" && sale.status !== "awaiting_payment" && sale.status !== "cancelled" && (
                    <div className="mt-1.5 flex items-center gap-2">
                      <span className="h-1.5 flex-1 overflow-hidden rounded-full bg-[#252e47]">
                        <span
                          className={`block h-full rounded-full transition-all ${l.copy_status === "failed" ? "bg-red-400" : l.copy_status === "copied" ? "bg-emerald-400" : "bg-amber-400"}`}
                          style={{ width: `${Math.round(pct * 100)}%` }}
                        />
                      </span>
                      <span className={`w-20 text-right text-[11px] font-semibold ${l.copy_status === "failed" ? "text-red-300" : l.copy_status === "copied" ? "text-emerald-300" : "text-amber-200"}`}>
                        {l.copy_status === "copying" ? `${Math.round(pct * 100)}%` : COPY_LABEL[l.copy_status]}
                      </span>
                    </div>
                  )}
                  {l.copy_message && <p className="mt-1 text-xs text-red-300">{l.copy_message}</p>}
                </li>
              );
            })}
          </ul>
          <p className="mt-3 flex items-center gap-2 font-mono text-xs text-slate-400">
            <Usb className="h-3.5 w-3.5" /> {sale.destination}
            {sale.folder}\
          </p>
        </div>

        <div className="flex flex-col gap-3">
          <div className="rounded-xl border border-[#252e47] bg-[#0f1422] p-3">
            <p className="text-xs text-slate-500">
              {sale.customer ? `${sale.customer.name} · ${sale.customer.phone} · portal customer` : sale.customer_name || "Customer"}
            </p>
            <p className="text-2xl font-extrabold">
              {sale.total} <span className="text-xs font-semibold text-slate-400">credits{sale.status === "ordered" ? " (estimate)" : ""}</span>
            </p>
            {(sale.discount > 0 || sale.points_used > 0 || (sale.status === "ordered" && sale.use_points)) && (
              <p className="mt-1 text-[11px] text-amber-200">
                {[
                  sale.discount > 0 ? `${sale.discount} off for free titles` : null,
                  sale.points_used > 0 ? `${sale.points_used} points used` : null,
                  sale.status === "ordered" && sale.use_points ? "uses their points when charged" : null,
                ]
                  .filter(Boolean)
                  .join(" · ")}
              </p>
            )}
          </div>

          {sale.status === "ordered" && <ChargeOrder sale={sale} onCharged={setSale} />}
          {sale.status === "ordered" && (
            <button className="text-xs text-slate-400 hover:text-red-300" onClick={() => void act("cancel")}>
              Cancel this order (points are given back)
            </button>
          )}
          {sale.status === "awaiting_payment" && sale.pay && (
            <div className="rounded-xl border border-teal-400/30 bg-teal-400/5 p-3 text-center">
              <p className="text-xs font-semibold text-teal-200">Scan with the IF Pay wallet</p>
              {qr ? (
                // eslint-disable-next-line @next/next/no-img-element -- Pay's QR code, drawn as a picture
                <img src={qr} alt="IF Pay payment QR code" className="mx-auto mt-2 h-44 w-44 rounded-lg bg-white p-2" />
              ) : null}
              <p className="mt-2 text-[11px] text-slate-400">Payment code</p>
              <p className="mt-1 rounded-md bg-[#0f1422] px-2 py-1.5 font-mono text-[10.5px] break-all text-slate-200 select-all">{sale.pay.code}</p>
              <p className="mt-1 flex items-center justify-center gap-1 text-[11px] text-slate-400">
                <Clock className="h-3 w-3" /> Waiting for the customer to confirm...
              </p>
            </div>
          )}
          {sale.status === "awaiting_payment" && (
            <div className="flex flex-col gap-2">
              <button className={dark.btn} onClick={() => void act("cash")}>
                <Banknote className="h-4 w-4" /> {sale.method === "cash" ? "Paid in cash" : "Paid in cash instead"}
              </button>
              <button className="text-xs text-slate-400 hover:text-red-300" onClick={() => void act("cancel")}>
                Cancel this sale
              </button>
            </div>
          )}
          {(sale.status === "paid" || sale.status === "done") && (
            <div className="rounded-xl border border-emerald-400/30 bg-emerald-400/10 p-3 text-sm text-emerald-100">
              <p className="flex items-center gap-2 font-bold">
                <ShieldCheck className="h-4 w-4" /> {sale.method === "cash" ? "Paid in cash" : "Paid with IF Pay"}
              </p>
              {sale.receipt_number && <p className="mt-1 text-xs">Receipt {sale.receipt_number}</p>}
            </div>
          )}
          {sale.status === "paid" && (
            <div>
              <p className="text-xs text-slate-400">Copying {Math.round(progress * 100)}%</p>
              <span className="mt-1 block h-2 overflow-hidden rounded-full bg-[#252e47]">
                <span className="block h-full rounded-full bg-gradient-to-r from-amber-400 to-amber-300 transition-all" style={{ width: `${Math.round(progress * 100)}%` }} />
              </span>
              {sale.lines.some((l) => l.copy_status === "failed") && (
                <button className={`${dark.btn} mt-3 w-full`} onClick={() => void act("retry")}>
                  <RefreshCw className="h-4 w-4" /> Copy the failed titles again
                </button>
              )}
            </div>
          )}
          {sale.status === "done" && (
            <p className="flex items-center gap-2 rounded-xl bg-[#0f1422] p-3 text-sm font-semibold text-emerald-200">
              <Check className="h-4 w-4 shrink-0" /> Everything is copied. The drive is safe to remove.
            </p>
          )}
          {sale.status === "cancelled" && (
            <p className="flex items-center gap-2 rounded-xl bg-[#0f1422] p-3 text-sm text-slate-300">
              <X className="h-4 w-4 shrink-0" /> Cancelled. Nothing was charged or copied.
            </p>
          )}
          {error && (
            <p className="flex items-center gap-1.5 text-sm text-red-300">
              <CircleAlert className="h-4 w-4" /> {error}
            </p>
          )}
        </div>
      </div>
    </DarkDialog>
  );
}

/** A portal order at the counter: the customer's drive and how they pay; their rewards apply when charged. */
function ChargeOrder({ sale, onCharged }: { sale: Sale; onCharged: (sale: Sale) => void }) {
  const { drives, destination, setDestination } = useDestinations(sale.shop);
  const [method, setMethod] = useState<Sale["method"]>("ifpay");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const driveId = useId();
  async function charge() {
    setBusy(true);
    setError(null);
    try {
      onCharged(await movies.charge(sale.id, destination, method));
    } catch (err) {
      setError(message(err));
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="flex flex-col gap-2 rounded-xl border border-amber-400/30 bg-amber-400/5 p-3">
      <p className="text-xs font-semibold text-amber-200">Ordered on the portal: plug in the customer&apos;s drive, then charge.</p>
      <label htmlFor={driveId} className={dark.label}>
        Copy to
      </label>
      <select id={driveId} className={dark.input} value={destination} onChange={(e) => setDestination(e.target.value)}>
        {drives.length === 0 && <option value="">Plug in the customer&apos;s USB...</option>}
        {drives.map((d) => (
          <option key={d.root} value={d.root}>
            {driveLabel(d)}
          </option>
        ))}
      </select>
      <div className="grid grid-cols-2 gap-2" role="radiogroup" aria-label="Payment">
        {(
          [
            ["ifpay", Wallet, "IF Pay"],
            ["cash", Banknote, "Cash"],
          ] as const
        ).map(([value, Icon, label]) => (
          <button
            key={value}
            role="radio"
            aria-checked={method === value}
            onClick={() => setMethod(value)}
            className={`inline-flex h-9 items-center justify-center gap-2 rounded-lg border text-sm font-semibold ${method === value ? "border-amber-400 bg-amber-400/10 text-amber-200" : "border-[#323c5a] text-slate-300"}`}
          >
            <Icon className="h-4 w-4" /> {label}
          </button>
        ))}
      </div>
      {error && <p className="text-xs text-red-300">{error}</p>}
      <button className={dark.amber} disabled={busy || !destination} onClick={() => void charge()}>
        <Coins className="h-4 w-4" /> {busy ? "Charging..." : "Charge this order"}
      </button>
    </div>
  );
}
