"use client";

import { useId, useRef, useState } from "react";
import { useDialogA11y } from "@/lib/use-dialog-a11y";
import { useQuery } from "@tanstack/react-query";
import { Check, Plus, Search, Star, X } from "lucide-react";
import { formatBytes } from "@/lib/movies";
import { portalApi, type PortalTitle } from "@/lib/portal";
import { MovieCover } from "@/components/movies/MovieCover";
import { portalStyle as ui } from "./Portal";

const PAGE = 48;

/** The shop's catalogue: categories, search, covers; a tap opens the title with "Add to cart". */
export function Browse({ shopId, inCart, onToggle }: { shopId: string; inCart: (id: string) => boolean; onToggle: (t: PortalTitle) => void }) {
  const [category, setCategory] = useState<string | null>(null);
  const [q, setQ] = useState("");
  const [query, setQuery] = useState("");
  const [limit, setLimit] = useState(PAGE);
  const [open, setOpen] = useState<PortalTitle | null>(null);
  const searchId = useId();
  const categories = useQuery({ queryKey: ["portal", shopId, "categories"], queryFn: () => portalApi.categories(shopId) });
  const titles = useQuery({
    queryKey: ["portal", shopId, "titles", category, query, limit],
    queryFn: () => portalApi.titles(shopId, { category: category ?? undefined, q: query || undefined, limit }),
  });

  return (
    <div>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          setQuery(q.trim());
          setLimit(PAGE);
        }}
        className="relative"
      >
        <label htmlFor={searchId} className="sr-only">
          Search
        </label>
        <Search className="pointer-events-none absolute top-1/2 left-4 h-5 w-5 -translate-y-1/2 text-slate-500" />
        <input id={searchId} type="search" className={`${ui.input} pl-12`} placeholder="Search films and series" value={q} onChange={(e) => setQ(e.target.value)} />
      </form>

      <div className="-mx-4 mt-3 flex gap-2 overflow-x-auto px-4 pb-1" role="tablist" aria-label="Categories">
        {[{ name: null as string | null, count: categories.data?.reduce((a, c) => a + c.count, 0) ?? 0 }, ...(categories.data ?? [])].map((c) => (
          <button
            key={c.name ?? "all"}
            role="tab"
            aria-selected={category === c.name}
            onClick={() => {
              setCategory(c.name);
              setLimit(PAGE);
            }}
            className={`shrink-0 rounded-full border px-4 py-2 text-sm font-semibold ${category === c.name ? "border-amber-400 bg-amber-400 text-amber-950" : "border-[#323c5a] bg-[#141a2b] text-slate-200"}`}
          >
            {c.name ?? "All"} <span className="opacity-60">{c.count}</span>
          </button>
        ))}
      </div>

      {titles.isLoading && <p className="mt-8 text-center text-sm text-slate-500">Loading...</p>}
      {titles.data && titles.data.results.length === 0 && <p className="mt-8 text-center text-sm text-slate-500">Nothing found.</p>}
      <div className="mt-4 grid grid-cols-3 gap-x-3 gap-y-4 sm:grid-cols-4">
        {titles.data?.results.map((t) => (
          <button key={t.id} onClick={() => setOpen(t)} className="relative text-left">
            <MovieCover title={t} src={portalApi.coverUrl(shopId, t.id)} />
            {inCart(t.id) && (
              <span className="absolute right-1.5 bottom-12 grid h-7 w-7 place-items-center rounded-full bg-emerald-400 text-emerald-950 shadow-lg">
                <Check className="h-4 w-4" strokeWidth={3} />
              </span>
            )}
            <p className="mt-1.5 truncate text-[13px] font-semibold">{t.title}</p>
            <p className="truncate text-[11px] text-slate-500">{[t.year, t.kind === "series" ? `${t.episodes} ep.` : null].filter(Boolean).join(" · ") || t.category}</p>
          </button>
        ))}
      </div>
      {titles.data && titles.data.count > titles.data.results.length && (
        <button className={`${ui.secondary} mt-6 w-full`} onClick={() => setLimit(limit + PAGE)}>
          Show more
        </button>
      )}

      {open && <TitleSheet shopId={shopId} title={open} added={inCart(open.id)} onToggle={() => onToggle(open)} onClose={() => setOpen(null)} />}
    </div>
  );
}

function TitleSheet({ shopId, title, added, onToggle, onClose }: { shopId: string; title: PortalTitle; added: boolean; onToggle: () => void; onClose: () => void }) {
  const ref = useRef<HTMLDivElement>(null);
  useDialogA11y(true, onClose, ref);
  return (
    <div className="fixed inset-0 z-30 flex items-end justify-center">
      <div className="absolute inset-0 bg-black/70" onClick={onClose} />
      <div ref={ref} role="dialog" aria-modal="true" aria-label={title.title} className="relative w-full max-w-xl rounded-t-3xl border-t border-[#323c5a] bg-[#111626] p-5 pb-[calc(env(safe-area-inset-bottom)+20px)]">
        <button onClick={onClose} className="absolute top-4 right-4 rounded-lg p-1.5 text-slate-400 hover:text-white" aria-label="Close">
          <X className="h-5 w-5" />
        </button>
        <div className="flex gap-4">
          <MovieCover title={title} src={portalApi.coverUrl(shopId, title.id)} className="w-28 shrink-0" />
          <div className="min-w-0 pt-1">
            <h2 className="pr-8 text-xl font-bold">{title.title}</h2>
            <p className="mt-1 flex flex-wrap items-center gap-1.5 text-sm text-slate-400">
              <Star className="h-4 w-4 fill-amber-300 text-amber-300" />
              {[title.category, title.year, title.kind === "series" ? `${title.episodes} episodes` : null, formatBytes(title.size_bytes)].filter(Boolean).join(" · ")}
            </p>
            {title.description && <p className="mt-3 line-clamp-4 text-sm leading-relaxed text-slate-300">{title.description}</p>}
            <p className="mt-3 text-2xl font-extrabold text-amber-200">
              {title.price} <span className="text-sm font-semibold text-slate-400">credits</span>
            </p>
          </div>
        </div>
        <button
          className={added ? `${ui.secondary} mt-5 h-12 w-full` : `${ui.primary} mt-5`}
          onClick={() => {
            onToggle();
            onClose();
          }}
        >
          {added ? (
            <>
              <X className="h-5 w-5" /> Remove from cart
            </>
          ) : (
            <>
              <Plus className="h-5 w-5" strokeWidth={2.6} /> Add to cart
            </>
          )}
        </button>
      </div>
    </div>
  );
}
