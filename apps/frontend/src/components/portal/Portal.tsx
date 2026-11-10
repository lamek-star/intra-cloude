"use client";

import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Clapperboard, Coins, Film, LogOut, Receipt, ShoppingBag, UserRound } from "lucide-react";
import { ApiError } from "@/lib/api";
import { portalApi, type PortalTitle } from "@/lib/portal";
import { AuthScreen } from "./AuthScreen";
import { Browse } from "./Browse";
import { CartScreen, OrdersScreen } from "./CartOrders";
import { MeScreen } from "./MeScreen";

type Tab = "browse" | "cart" | "orders" | "me";

export const portalStyle = {
  input:
    "h-12 w-full rounded-xl border border-[#323c5a] bg-[#0f1422] px-4 text-base text-slate-100 placeholder:text-slate-500 outline-none focus:border-amber-400 focus:ring-2 focus:ring-amber-400/20",
  label: "mb-1.5 block text-sm font-semibold text-slate-300",
  primary:
    "inline-flex h-12 w-full items-center justify-center gap-2 rounded-xl bg-amber-400 px-5 text-base font-bold text-amber-950 shadow-[0_10px_24px_-12px_rgba(245,165,36,.9)] transition active:scale-[0.98] disabled:opacity-50",
  secondary:
    "inline-flex h-11 items-center justify-center gap-2 rounded-xl border border-[#323c5a] bg-[#1b2236] px-4 text-sm font-semibold text-slate-100 transition hover:bg-[#232c45] disabled:opacity-50",
};

export function portalMessage(err: unknown): string {
  return err instanceof Error ? err.message : "Something went wrong.";
}

/** The customer portal: sign in or sign up, then browse, the cart, orders and points. Built for a phone. */
export function Portal({ shopId }: { shopId: string }) {
  const qc = useQueryClient();
  // Refreshed every 20 s and on every tab change: the header's points and the approval banner follow the counter.
  const home = useQuery({ queryKey: ["portal", shopId, "home"], queryFn: () => portalApi.home(shopId), retry: false, refetchInterval: 20000 });
  const [tab, setTabState] = useState<Tab>("browse");
  const [cart, setCart] = useState<PortalTitle[]>([]);

  const refresh = () => void qc.invalidateQueries({ queryKey: ["portal", shopId] });
  const setTab = (next: Tab) => {
    setTabState(next);
    void qc.invalidateQueries({ queryKey: ["portal", shopId, "home"] });
  };

  if (home.isError) {
    const closed = home.error instanceof ApiError && home.error.status === 404;
    return (
      <Shell>
        <div className="mx-auto mt-24 max-w-sm px-6 text-center">
          <span className="mx-auto grid h-14 w-14 place-items-center rounded-2xl bg-amber-400/10 text-amber-300">
            <Clapperboard className="h-7 w-7" />
          </span>
          <h1 className="mt-4 text-xl font-bold">{closed ? "This portal is closed" : "The shop is not answering"}</h1>
          <p className="mt-2 text-sm text-slate-400">
            {closed ? "Ask at the counter: the shop opens its portal from IntraForge." : "Check that you are on the shop's Wi-Fi and try again."}
          </p>
        </div>
      </Shell>
    );
  }
  if (!home.data) {
    return (
      <Shell>
        <p className="mt-24 text-center text-sm text-slate-500" role="status">
          Opening the shop...
        </p>
      </Shell>
    );
  }

  const { shop, customer } = home.data;
  if (!customer) return <AuthScreen shop={shop} onSignedIn={refresh} />;

  const inCart = (id: string) => cart.some((t) => t.id === id);
  const toggle = (t: PortalTitle) => setCart((c) => (c.some((x) => x.id === t.id) ? c.filter((x) => x.id !== t.id) : [...c, t]));

  async function signOut() {
    await portalApi.signOut(shopId).catch(() => undefined);
    setCart([]);
    refresh();
  }

  const tabs: { id: Tab; label: string; icon: typeof Film; badge?: number }[] = [
    { id: "browse", label: "Browse", icon: Film },
    { id: "cart", label: "Cart", icon: ShoppingBag, badge: cart.length },
    { id: "orders", label: "Orders", icon: Receipt },
    { id: "me", label: "Me", icon: UserRound },
  ];

  return (
    <Shell>
      <header className="sticky top-0 z-20 flex items-center gap-3 border-b border-[#252e47] bg-[#0a0d16]/90 px-4 py-3 backdrop-blur">
        <span className="grid h-9 w-9 shrink-0 place-items-center rounded-[10px] bg-[radial-gradient(circle_at_30%_25%,#ffd27a,#f5a524_60%,#c97b05)] text-amber-950">
          <Clapperboard className="h-4 w-4" strokeWidth={2.4} />
        </span>
        <div className="min-w-0 flex-1">
          <p className="truncate text-base font-semibold tracking-wide uppercase" style={{ fontFamily: "var(--font-display), sans-serif" }}>
            {shop.name}
          </p>
          <p className="truncate text-[11px] text-slate-500">Hello, {customer.name.split(" ")[0]}</p>
        </div>
        <button onClick={() => setTab("me")} className="inline-flex items-center gap-1 rounded-full bg-amber-400/15 px-3 py-1.5 text-sm font-bold text-amber-200">
          <Coins className="h-4 w-4" /> {customer.points}
        </button>
        <button onClick={() => void signOut()} className="rounded-lg p-2 text-slate-400 hover:bg-white/5 hover:text-white" aria-label="Sign out">
          <LogOut className="h-5 w-5" />
        </button>
      </header>

      {customer.status === "pending" && (
        <div className="mx-4 mt-3 rounded-xl border border-amber-400/30 bg-amber-400/10 px-4 py-3 text-sm text-amber-100">
          <b>Almost there.</b> The shop approves new customers at the counter and adds them to IF Pay. You can look around now and order once you are approved.
        </div>
      )}

      <main className="flex-1 px-4 pt-4 pb-28">
        {tab === "browse" && <Browse shopId={shopId} inCart={inCart} onToggle={toggle} />}
        {tab === "cart" && (
          <CartScreen
            shopId={shopId}
            customer={customer}
            items={cart}
            onRemove={(id) => setCart((c) => c.filter((x) => x.id !== id))}
            onOrdered={() => {
              setCart([]);
              refresh();
              setTab("orders");
            }}
            onBrowse={() => setTab("browse")}
          />
        )}
        {tab === "orders" && <OrdersScreen shopId={shopId} onChanged={refresh} />}
        {tab === "me" && <MeScreen shopId={shopId} rules={shop.rules} />}
      </main>

      <nav aria-label="Portal" className="fixed inset-x-0 bottom-0 z-20 border-t border-[#252e47] bg-[#0d111c]/95 pb-[env(safe-area-inset-bottom)] backdrop-blur">
        <div className="mx-auto grid max-w-xl grid-cols-4">
          {tabs.map(({ id, label, icon: Icon, badge }) => (
            <button
              key={id}
              onClick={() => setTab(id)}
              aria-current={tab === id ? "page" : undefined}
              className={`relative flex flex-col items-center gap-1 py-2.5 text-[11px] font-semibold ${tab === id ? "text-amber-300" : "text-slate-400"}`}
            >
              <Icon className="h-5 w-5" />
              {label}
              {badge ? (
                <span className="absolute top-1.5 left-1/2 ml-2 grid h-4 min-w-4 place-items-center rounded-full bg-amber-400 px-1 text-[10px] font-bold text-amber-950">{badge}</span>
              ) : null}
            </button>
          ))}
        </div>
      </nav>
    </Shell>
  );
}

function Shell({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen flex-col bg-[#0a0d16] bg-[radial-gradient(700px_400px_at_90%_-10%,rgba(245,165,36,.12),transparent_60%),radial-gradient(600px_400px_at_0%_110%,rgba(45,212,191,.08),transparent_60%)] text-slate-100">
      <div className="mx-auto flex w-full max-w-xl flex-1 flex-col">{children}</div>
    </div>
  );
}
