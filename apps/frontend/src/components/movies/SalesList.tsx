"use client";

import { useEffect, useState } from "react";
import { Banknote, Wallet } from "lucide-react";
import { copyProgress, movies, SALE_STATUS, type Sale } from "@/lib/movies";
import { dark, DarkDialog, message } from "./Dialogs";

const TONE: Record<Sale["status"], string> = {
  ordered: "border-violet-400/30 bg-violet-400/10 text-violet-200",
  awaiting_payment: "border-amber-400/30 bg-amber-400/10 text-amber-200",
  paid: "border-sky-400/30 bg-sky-400/10 text-sky-200",
  done: "border-emerald-400/30 bg-emerald-400/10 text-emerald-200",
  cancelled: "border-[#323c5a] text-slate-400",
};
const FAILED_TONE = "border-red-400/30 bg-red-400/10 text-red-200";
const failed = (sale: Sale) => sale.status === "paid" && sale.lines.some((l) => l.copy_status === "failed");

/** The shop's sales, newest first; opening one shows its payment and copy progress again. */
export function SalesDialog({ shopId, onClose, onOpen }: { shopId: string; onClose: () => void; onOpen: (id: string) => void }) {
  const [sales, setSales] = useState<Sale[] | null>(null);
  const [count, setCount] = useState(0);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let live = true;
    movies
      .sales(shopId)
      .then((page) => {
        if (!live) return;
        setSales(page.results);
        setCount(page.count);
      })
      .catch((err) => live && setError(message(err)));
    return () => {
      live = false;
    };
  }, [shopId]);

  return (
    <DarkDialog title={count ? `Sales · ${count}` : "Sales"} onClose={onClose} wide>
      {error && <p className="text-sm text-red-300">{error}</p>}
      {!sales && !error && <p className="text-sm text-slate-500">Loading sales...</p>}
      {sales && sales.length === 0 && <p className="text-sm text-slate-400">No sales yet. Add titles to the cart from the catalogue.</p>}
      <ul className="flex max-h-[60vh] flex-col overflow-y-auto">
        {sales?.map((sale) => (
          <li key={sale.id}>
            <button
              onClick={() => {
                onClose();
                onOpen(sale.id);
              }}
              className="flex w-full items-center gap-3 border-b border-[#252e47] px-1 py-3 text-left hover:bg-white/5"
            >
              <span className="grid h-9 w-9 shrink-0 place-items-center rounded-lg bg-[#0f1422] text-slate-300">
                {sale.method === "cash" ? <Banknote className="h-4 w-4" /> : <Wallet className="h-4 w-4" />}
              </span>
              <span className="min-w-0 flex-1">
                <span className="block truncate text-sm font-semibold">
                  {sale.customer?.name || sale.customer_name || "Customer"} · {sale.lines.length} title{sale.lines.length === 1 ? "" : "s"}
                  {sale.customer && <span className="ml-2 text-[10.5px] font-semibold text-violet-300">PORTAL</span>}
                </span>
                <span className="block font-mono text-[11px] text-slate-500">
                  {sale.number} · {new Date(sale.created_at).toLocaleString()}
                </span>
              </span>
              <span className={`shrink-0 rounded-full border px-2.5 py-0.5 text-[11px] font-semibold ${failed(sale) ? FAILED_TONE : TONE[sale.status]}`}>
                {failed(sale) ? "Copy failed" : sale.status === "paid" ? `Copying ${Math.round(copyProgress(sale) * 100)}%` : SALE_STATUS[sale.status]}
              </span>
              <span className="w-14 shrink-0 text-right text-sm font-extrabold">{sale.total}</span>
            </button>
          </li>
        ))}
      </ul>
      <div className="mt-4 flex justify-end">
        <button className={dark.btn} onClick={onClose}>
          Close
        </button>
      </div>
    </DarkDialog>
  );
}
