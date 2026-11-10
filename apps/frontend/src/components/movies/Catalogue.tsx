"use client";

import Link from "next/link";
import { useEffect, useId, useMemo, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { ChevronLeft, Coins, Folder, HardDrive, Pencil, Play, Plus, Receipt, RefreshCw, Search, Server, ShoppingCart, Star, Tag, Megaphone, Trash2, Usb, Users } from "lucide-react";
import { agentOnline, formatBytes, movies, titlesLabel, type MovieLibrary, type MovieTitle, type Sale } from "@/lib/movies";
import { PageLoading, ErrorBanner } from "@/components/ui";
import { useConfirm } from "@/components/ConfirmProvider";
import { MovieCover } from "./MovieCover";
import { dark, EditTitleDialog, message, PricesDialog, SetupDialog } from "./Dialogs";
import { CartPanel, SaleDialog } from "./Checkout";
import { SalesDialog } from "./SalesList";
import { CustomersDialog } from "./Customers";
import { AdsDialog } from "./Ads";

const KIND_ICON = { fixed: HardDrive, removable: Usb, network: Server };
const PAGE = 60;

/** The owner's Movie Shop (design: design-references/movie-shop-mockups/1-catalogue): the storage on the left, the
 * folders as categories across the top (A), the titles of the chosen folder below (B). */
export function Catalogue({ shopId }: { shopId: string }) {
  const qc = useQueryClient();
  const confirm = useConfirm();
  const [library, setLibrary] = useState<string | null>(null);
  const [category, setCategory] = useState<string | null>(null);
  const [q, setQ] = useState("");
  const [query, setQuery] = useState("");
  const [limit, setLimit] = useState(PAGE);
  const [dialog, setDialog] = useState<"setup" | "prices" | "sales" | "customers" | "ads" | null>(null);
  const [cart, setCart] = useState<MovieTitle[]>([]);
  const [openSale, setOpenSale] = useState<{ id: string; initial?: Sale } | null>(null);
  const [editing, setEditing] = useState<MovieTitle | null>(null);
  const [error, setError] = useState<string | null>(null);
  const searchId = useId();

  const shop = useQuery({ queryKey: ["movies", shopId, "shop"], queryFn: () => movies.shop(shopId), refetchInterval: 15000 });
  const libraries = useQuery({
    queryKey: ["movies", shopId, "libraries"],
    queryFn: () => movies.libraries(shopId),
    refetchInterval: (query) => (query.state.data?.some((l) => l.scan_requested) ? 3000 : 20000),
  });
  const portalInfo = useQuery({
    queryKey: ["movies", shopId, "portal"],
    queryFn: () => movies.portal(shopId),
    enabled: shop.data?.can_manage === true,
    refetchInterval: 30000,
  });
  const categories = useQuery({ queryKey: ["movies", shopId, "categories", library], queryFn: () => movies.categories(shopId, library ?? undefined) });
  const titles = useQuery({
    queryKey: ["movies", shopId, "titles", library, category, query, limit],
    queryFn: () => movies.titles(shopId, { library: library ?? undefined, category: category ?? undefined, q: query || undefined, limit }),
  });

  const scanning = libraries.data?.some((l) => l.scan_requested) ?? false;
  // While a scan runs, refresh the categories and titles when it ends.
  const [wasScanning, setWasScanning] = useState(false);
  useEffect(() => {
    if (wasScanning && !scanning) void qc.invalidateQueries({ queryKey: ["movies", shopId] });
  }, [scanning, wasScanning, qc, shopId]);
  if (scanning !== wasScanning) setWasScanning(scanning);

  const refresh = () => void qc.invalidateQueries({ queryKey: ["movies", shopId] });
  const cats = categories.data ?? [];
  const currentLibrary = useMemo(() => libraries.data?.find((l) => l.id === library) ?? null, [libraries.data, library]);

  if (shop.isError) return <ErrorBanner message={message(shop.error)} />;
  if (!shop.data) return <PageLoading />;
  const s = shop.data;
  const online = agentOnline(s.agent_seen_at);
  const empty = (libraries.data?.length ?? 0) === 0;

  async function removeLibrary(lib: MovieLibrary) {
    const ok = await confirm({ title: `Remove ${lib.name}?`, description: "Its titles leave the catalogue. The files on the drive are not touched.", confirmLabel: "Remove", danger: true });
    if (!ok) return;
    try {
      await movies.removeLibrary(lib.id);
      if (library === lib.id) setLibrary(null);
      refresh();
    } catch (err) {
      setError(message(err));
    }
  }

  return (
    <div className="-m-4 min-h-[calc(100vh)] bg-[#0a0d16] bg-[radial-gradient(900px_500px_at_85%_-10%,rgba(245,165,36,.10),transparent_60%),radial-gradient(700px_500px_at_10%_110%,rgba(45,212,191,.07),transparent_60%)] p-4 text-slate-100 sm:-m-8 sm:p-6">
      {/* Header */}
      <div className="flex flex-wrap items-center gap-4 border-b border-[#252e47] pb-4">
        <Link href="/movies" className="rounded-lg p-1.5 text-slate-400 hover:bg-white/5 hover:text-white" aria-label="All movie shops">
          <ChevronLeft className="h-5 w-5" />
        </Link>
        <div className="flex items-center gap-3">
          <span className="grid h-9 w-9 place-items-center rounded-[10px] bg-[radial-gradient(circle_at_30%_25%,#ffd27a,#f5a524_60%,#c97b05)] text-amber-950 shadow-[0_6px_18px_-6px_rgba(245,165,36,.6)]">
            <Play className="h-4 w-4" strokeWidth={2.6} />
          </span>
          <div>
            <h1 className="text-xl font-semibold tracking-wide uppercase" style={{ fontFamily: "var(--font-display), sans-serif" }}>
              {s.name}
            </h1>
            <p className="text-[11px] tracking-wider text-slate-500 uppercase">Movie Shop · {s.titles.toLocaleString()} titles</p>
          </div>
        </div>
        <div className="ml-auto flex flex-wrap items-center gap-2">
          <span
            className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-semibold ${online ? "border-emerald-400/30 bg-emerald-400/10 text-emerald-200" : "border-[#323c5a] text-slate-400"}`}
          >
            <span className={`h-1.5 w-1.5 rounded-full ${online ? "bg-emerald-400" : "bg-slate-500"}`} />
            {online ? `Media agent on ${s.agent.computer || "the shop PC"}` : "Media agent not running"}
          </span>
          {s.can_sell && (
            <button className={dark.btn} onClick={() => setDialog("sales")}>
              <Receipt className="h-4 w-4" /> Sales
            </button>
          )}
          {s.can_manage && (
            <>
              <button className={`${dark.btn} relative`} onClick={() => setDialog("customers")}>
                <Users className="h-4 w-4" /> Customers
                {(portalInfo.data?.waiting ?? 0) > 0 && (
                  <span className="absolute -top-1.5 -right-1.5 grid h-5 min-w-5 place-items-center rounded-full bg-amber-400 px-1 text-[11px] font-bold text-amber-950">
                    {portalInfo.data?.waiting}
                  </span>
                )}
              </button>
              <button className={dark.btn} onClick={() => setDialog("ads")}>
                <Megaphone className="h-4 w-4" /> Ads
              </button>
              <button className={dark.btn} onClick={() => setDialog("prices")}>
                <Tag className="h-4 w-4" /> Prices
              </button>
              <button className={dark.amber} onClick={() => setDialog("setup")}>
                <Plus className="h-4 w-4" strokeWidth={2.6} /> Add storage
              </button>
            </>
          )}
        </div>
      </div>
      {error && <p className="mt-3 text-sm text-red-300">{error}</p>}

      {empty ? (
        <div className="mx-auto mt-16 max-w-xl text-center">
          <span className="mx-auto grid h-14 w-14 place-items-center rounded-2xl bg-amber-400/10 text-amber-300">
            <Folder className="h-7 w-7" />
          </span>
          <h2 className="mt-4 text-xl font-bold">Connect the drives that hold your films</h2>
          <p className="mt-2 text-sm leading-relaxed text-slate-400">
            Run the media agent on the shop PC once, then pick the folders. Every folder inside becomes a category, every video a title, with its
            cover when a picture sits beside it.
          </p>
          {s.can_manage && (
            <button className={`${dark.amber} mt-6`} onClick={() => setDialog("setup")}>
              <Plus className="h-4 w-4" strokeWidth={2.6} /> Connect the shop&apos;s drives
            </button>
          )}
        </div>
      ) : (
        <div className={`mt-5 grid gap-6 ${cart.length ? "lg:grid-cols-[220px_1fr_300px]" : "lg:grid-cols-[240px_1fr]"}`}>
          {/* Storage */}
          <aside aria-label="Storage" className="flex flex-col gap-1.5">
            <p className="px-2 pb-1 text-[11px] font-semibold tracking-[.08em] text-slate-500 uppercase">Storage</p>
            <button
              onClick={() => {
                setLibrary(null);
                setCategory(null);
              }}
              className={`rounded-xl px-3 py-2 text-left text-sm font-semibold ${library === null ? "bg-[#1b2236] ring-1 ring-[#323c5a]" : "text-slate-300 hover:bg-white/5"}`}
            >
              All storage
            </button>
            {libraries.data?.map((lib) => {
              const Icon = KIND_ICON[lib.kind];
              const used = lib.total_bytes && lib.free_bytes != null ? 1 - lib.free_bytes / lib.total_bytes : null;
              return (
                <div key={lib.id} className={`group rounded-xl p-2.5 ${library === lib.id ? "bg-[#1b2236] ring-1 ring-[#323c5a]" : "hover:bg-white/5"}`}>
                  <button
                    className="flex w-full items-start gap-2.5 text-left"
                    onClick={() => {
                      setLibrary(lib.id);
                      setCategory(null);
                    }}
                  >
                    <span className={`grid h-8 w-8 shrink-0 place-items-center rounded-lg bg-[#0f1422] ${library === lib.id ? "text-amber-300" : "text-slate-400"}`}>
                      <Icon className="h-4 w-4" />
                    </span>
                    <span className="min-w-0 flex-1">
                      <span className="block truncate text-[13px] font-semibold">{lib.name}</span>
                      <span className="block text-[11px] text-slate-500">
                        {lib.scan_requested ? "Scanning..." : titlesLabel(lib.titles)}
                        {lib.free_bytes != null && ` · ${formatBytes(lib.free_bytes)} free`}
                      </span>
                      {used != null && (
                        <span className="mt-1.5 block h-1.5 overflow-hidden rounded-full bg-[#252e47]">
                          <span className="block h-full rounded-full bg-gradient-to-r from-amber-400 to-amber-300" style={{ width: `${Math.round(used * 100)}%` }} />
                        </span>
                      )}
                    </span>
                  </button>
                  {s.can_manage && (
                    <div className="mt-1.5 hidden gap-1 pl-10 group-hover:flex group-focus-within:flex">
                      <button className="inline-flex items-center gap-1 rounded-md px-2 py-1 text-[11px] text-slate-400 hover:bg-white/5 hover:text-white" onClick={() => void movies.scan(lib.id).then(refresh)}>
                        <RefreshCw className="h-3 w-3" /> Scan again
                      </button>
                      <button className="inline-flex items-center gap-1 rounded-md px-2 py-1 text-[11px] text-slate-400 hover:bg-white/5 hover:text-red-300" onClick={() => void removeLibrary(lib)}>
                        <Trash2 className="h-3 w-3" /> Remove
                      </button>
                    </div>
                  )}
                </div>
              );
            })}
          </aside>

          <section className="min-w-0">
            {/* A: folders */}
            <div className="flex flex-wrap items-end justify-between gap-3">
              <div>
                <p className="text-[11px] font-semibold tracking-[.08em] text-amber-300 uppercase">Folders</p>
                <h2 className="mt-1 text-lg font-bold">{currentLibrary?.name ?? "All storage"}</h2>
                <p className="text-xs text-slate-500">
                  {currentLibrary ? `Arranged from the folder names in ${currentLibrary.path}` : "Arranged from the folder names in every library"}
                  {currentLibrary?.last_scan_at && ` · scanned ${new Date(currentLibrary.last_scan_at).toLocaleString()}`}
                </p>
              </div>
              <form
                className="flex items-center gap-2"
                onSubmit={(e) => {
                  e.preventDefault();
                  setQuery(q.trim());
                  setLimit(PAGE);
                }}
              >
                <label htmlFor={searchId} className="sr-only">
                  Search titles
                </label>
                <div className="relative">
                  <Search className="pointer-events-none absolute top-1/2 left-3 h-4 w-4 -translate-y-1/2 text-slate-500" />
                  <input id={searchId} className={`${dark.input} w-64 pl-9`} placeholder="Search titles..." value={q} onChange={(e) => setQ(e.target.value)} />
                </div>
              </form>
            </div>
            <div className="mt-3 flex gap-2.5 overflow-x-auto pb-2">
              <FolderTile name="Everything" count={cats.reduce((a, c) => a + c.count, 0)} active={category === null} onClick={() => setCategory(null)} />
              {cats.map((c) => (
                <FolderTile key={c.name} name={c.name} count={c.count} active={category === c.name} onClick={() => setCategory(c.name)} />
              ))}
            </div>

            {/* B: titles */}
            <div className="mt-5 flex items-center gap-3">
              <p className="text-[11px] font-semibold tracking-[.08em] text-amber-300 uppercase">Inside the folder</p>
              <span className="text-base font-bold">{category ?? "Everything"}</span>
              {titles.data && <span className="rounded-full border border-[#252e47] bg-[#1b2236] px-2.5 py-0.5 text-xs text-slate-300">{titles.data.count.toLocaleString()}</span>}
            </div>
            {titles.isLoading ? (
              <p className="mt-6 text-sm text-slate-500">Loading titles...</p>
            ) : titles.data && titles.data.results.length === 0 ? (
              <p className="mt-6 text-sm text-slate-500">{scanning ? "The media agent is scanning the folders..." : "No titles here yet."}</p>
            ) : (
              <div className={`mt-4 grid grid-cols-2 gap-x-4 gap-y-5 sm:grid-cols-3 md:grid-cols-4 ${cart.length ? "xl:grid-cols-5" : "xl:grid-cols-6"}`}>
                {titles.data?.results.map((t) => (
                  <TitleCard
                    key={t.id}
                    title={t}
                    canManage={s.can_manage}
                    canSell={s.can_sell}
                    inCart={cart.some((c) => c.id === t.id)}
                    onEdit={() => setEditing(t)}
                    onToggleCart={() => setCart((c) => (c.some((x) => x.id === t.id) ? c.filter((x) => x.id !== t.id) : [...c, t]))}
                  />
                ))}
              </div>
            )}
            {titles.data && titles.data.count > titles.data.results.length && (
              <div className="mt-6 flex justify-center">
                <button className={dark.btn} onClick={() => setLimit(limit + PAGE)}>
                  Show more ({(titles.data.count - titles.data.results.length).toLocaleString()} left)
                </button>
              </div>
            )}
          </section>
          {cart.length > 0 && (
            <CartPanel
              shop={s}
              items={cart}
              onRemove={(id) => setCart((c) => c.filter((x) => x.id !== id))}
              onClear={() => setCart([])}
              onSold={(sale) => {
                setCart([]);
                setOpenSale({ id: sale.id, initial: sale });
              }}
            />
          )}
        </div>
      )}

      {dialog === "setup" && <SetupDialog shop={s} onClose={() => setDialog(null)} onChanged={refresh} />}
      {dialog === "prices" && <PricesDialog shop={s} categories={cats} onClose={() => setDialog(null)} onSaved={refresh} />}
      {editing && <EditTitleDialog title={editing} onClose={() => setEditing(null)} onSaved={refresh} />}
      {dialog === "ads" && <AdsDialog shopId={s.id} shopName={s.name} onClose={() => setDialog(null)} />}
      {dialog === "customers" && <CustomersDialog shopId={s.id} onClose={() => setDialog(null)} onChanged={refresh} />}
      {dialog === "sales" && <SalesDialog shopId={s.id} onClose={() => setDialog(null)} onOpen={(id) => setOpenSale({ id })} />}
      {openSale && <SaleDialog saleId={openSale.id} initial={openSale.initial} onClose={() => setOpenSale(null)} />}
    </div>
  );
}

function FolderTile({ name, count, active, onClick }: { name: string; count: number; active: boolean; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      aria-pressed={active}
      className={`flex min-w-[150px] items-center gap-3 rounded-2xl border p-3 text-left transition ${active ? "border-amber-400 bg-gradient-to-b from-amber-400/10 to-[#141a2b] shadow-[0_0_0_3px_rgba(245,165,36,.15)]" : "border-[#252e47] bg-[#141a2b] hover:border-[#323c5a]"}`}
    >
      <span className={`grid h-10 w-10 place-items-center rounded-xl ${active ? "bg-amber-400 text-amber-950" : "bg-[#1b2236] text-slate-300"}`}>
        <Folder className="h-5 w-5" />
      </span>
      <span>
        <span className="block text-sm font-semibold">{name}</span>
        <span className="block text-xs text-slate-500">{titlesLabel(count)}</span>
      </span>
    </button>
  );
}

type TitleCardProps = {
  title: MovieTitle;
  canManage: boolean;
  canSell: boolean;
  inCart: boolean;
  onEdit: () => void;
  onToggleCart: () => void;
};

function TitleCard({ title, canManage, canSell, inCart, onEdit, onToggleCart }: TitleCardProps) {
  return (
    <div className="group relative">
      <div className="relative transition duration-300 group-hover:-translate-y-1.5 group-hover:scale-[1.04] group-hover:drop-shadow-[0_24px_30px_rgba(0,0,0,.6)]">
        <MovieCover title={title} />
        {inCart && (
          <span className="absolute right-2 bottom-2 grid h-7 w-7 place-items-center rounded-full bg-emerald-400 text-emerald-950 shadow-lg" aria-hidden>
            <ShoppingCart className="h-3.5 w-3.5" />
          </span>
        )}
        <div className="absolute inset-0 flex flex-col justify-end rounded-xl bg-gradient-to-t from-black/95 via-black/75 to-transparent p-2.5 opacity-0 transition duration-200 group-hover:opacity-100 group-focus-within:opacity-100">
          <p className="truncate text-[11px] font-semibold text-white">{title.title}</p>
          <p className="mt-0.5 flex items-center gap-1 truncate text-[10.5px] text-slate-300">
            <Star className="h-3 w-3 shrink-0 fill-amber-300 text-amber-300" />
            {[title.category, title.year, title.kind === "series" ? `${title.episodes} episodes` : null].filter(Boolean).join(" · ")}
          </p>
          {title.description && <p className="mt-1 line-clamp-2 text-[10.5px] leading-snug text-slate-400">{title.description}</p>}
          <div className="mt-2 flex items-center gap-1.5">
            <span className="inline-flex h-7 items-center gap-1 rounded-md bg-amber-400/15 px-2 text-[11px] font-bold text-amber-200" title={title.relative_path}>
              <Coins className="h-3 w-3" /> {title.price}
            </span>
            <span className="ml-auto" />
            {canManage && (
              <button
                onClick={onEdit}
                aria-label={`Edit ${title.title}`}
                className="inline-flex h-7 items-center rounded-md bg-white/10 px-2 text-[11px] font-semibold text-white hover:bg-white/20"
              >
                <Pencil className="h-3 w-3" />
              </button>
            )}
          </div>
          {canSell && (
            <button
              onClick={onToggleCart}
              aria-pressed={inCart}
              className={`mt-1.5 inline-flex h-7 w-full items-center justify-center gap-1 rounded-md text-[11px] font-bold ${inCart ? "bg-emerald-400 text-emerald-950" : "bg-amber-400 text-amber-950"}`}
            >
              {inCart ? (
                <>
                  <ShoppingCart className="h-3 w-3" /> In cart
                </>
              ) : (
                <>
                  <Plus className="h-3 w-3" strokeWidth={3} /> Add
                </>
              )}
            </button>
          )}
        </div>
      </div>
      <p className="mt-2 truncate text-[13px] font-semibold">{title.title}</p>
      <p className="text-[11px] text-slate-500">
        {[title.year, title.kind === "series" ? `${title.episodes} ep.` : null, formatBytes(title.size_bytes)].filter(Boolean).join(" · ")}
        {title.hidden && " · hidden"}
      </p>
    </div>
  );
}
