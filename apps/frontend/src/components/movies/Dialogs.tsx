"use client";

import { useEffect, useId, useMemo, useRef, useState, type ReactNode } from "react";
import { Check, Copy, HardDrive, ImagePlus, KeyRound, Server, Usb, X } from "lucide-react";
import { agentOnline, formatBytes, movies, pairCommand, titlesLabel, type AgentReport, type MovieCategory, type MovieShop, type MovieTitle } from "@/lib/movies";
import { useDialogA11y } from "@/lib/use-dialog-a11y";
import { MovieCover } from "./MovieCover";

export const dark = {
  input: "h-10 w-full rounded-lg border border-[#323c5a] bg-[#0f1422] px-3 text-sm text-slate-100 placeholder:text-slate-500 outline-none focus:border-amber-400 focus:ring-2 focus:ring-amber-400/20",
  label: "mb-1.5 block text-xs font-semibold text-slate-300",
  btn: "inline-flex h-10 items-center justify-center gap-2 rounded-lg border border-[#323c5a] bg-[#1b2236] px-4 text-sm font-semibold text-slate-100 transition hover:bg-[#232c45] disabled:opacity-50",
  amber: "inline-flex h-10 items-center justify-center gap-2 rounded-lg bg-amber-400 px-4 text-sm font-bold text-amber-950 shadow-[0_8px_20px_-10px_rgba(245,165,36,.8)] transition hover:bg-amber-300 active:scale-[0.98] disabled:opacity-50",
};

export function message(err: unknown): string {
  // ApiError already carries the server's own words (including a field's validation message).
  return err instanceof Error ? err.message : "Something went wrong.";
}

/** The Movie Shop's dark dialog. */
export function DarkDialog({ title, onClose, children, wide = false }: { title: string; onClose: () => void; children: ReactNode; wide?: boolean }) {
  const ref = useRef<HTMLDivElement>(null);
  const titleId = useId();
  useDialogA11y(true, onClose, ref);
  return (
    <div data-theme="light" className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="dialog-backdrop absolute inset-0 bg-[#05070d]/70 backdrop-blur-[2px]" onClick={onClose} />
      <div
        ref={ref}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        tabIndex={-1}
        className={`dialog-panel relative max-h-[90vh] w-full overflow-y-auto rounded-2xl border border-[#323c5a] bg-[#141a2b] text-slate-100 shadow-[0_40px_90px_-20px_rgba(0,0,0,.95)] outline-none ${wide ? "max-w-3xl" : "max-w-lg"}`}
      >
        <div className="flex items-center justify-between border-b border-[#252e47] px-5 py-4">
          <h2 id={titleId} className="text-base font-bold">
            {title}
          </h2>
          <button onClick={onClose} aria-label="Close" className="rounded-lg p-1.5 text-slate-400 hover:bg-white/5 hover:text-white">
            <X className="h-4 w-4" />
          </button>
        </div>
        <div className="p-5">{children}</div>
      </div>
    </div>
  );
}

const KIND_ICON = { fixed: HardDrive, removable: Usb, network: Server };

/** Connect the media agent on the shop PC, then pick the folders that hold the films. */
export function SetupDialog({ shop, onClose, onChanged }: { shop: MovieShop; onClose: () => void; onChanged: () => void }) {
  const [token, setToken] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const [report, setReport] = useState<AgentReport | null>(null);
  const [path, setPath] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const pathId = useId();

  useEffect(() => {
    let alive = true;
    const load = () => movies.drives(shop.id).then((r) => alive && setReport(r)).catch(() => undefined);
    load();
    const t = window.setInterval(load, 5000);
    return () => {
      alive = false;
      window.clearInterval(t);
    };
  }, [shop.id]);

  const online = agentOnline(report?.agent_seen_at ?? null);
  const command = token ? pairCommand(token, window.location.origin) : "";

  async function connect() {
    setError(null);
    try {
      setToken((await movies.agentCredential(shop.id)).token);
    } catch (err) {
      setError(message(err));
    }
  }

  async function add(folder: string, kind: "fixed" | "removable" | "network", label: string) {
    setBusy(true);
    setError(null);
    try {
      const name = folder.split("\\").filter(Boolean).pop() ?? folder;
      await movies.addLibrary(shop.id, folder, label ? `${name} (${label})` : name, kind);
      onChanged();
      setPath("");
    } catch (err) {
      setError(message(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <DarkDialog title="Connect the shop's drives" onClose={onClose} wide>
      <ol className="flex flex-col gap-5">
        <li>
          <p className="flex items-center gap-2 text-sm font-semibold">
            <span className="grid h-6 w-6 place-items-center rounded-full bg-amber-400 text-xs font-bold text-amber-950">1</span>
            Connect the media agent on the shop PC
            {online ? (
              <span className="ml-auto inline-flex items-center gap-1.5 rounded-full border border-emerald-400/30 bg-emerald-400/10 px-2.5 py-0.5 text-xs font-semibold text-emerald-200">
                <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" /> Connected · {report?.computer || "this PC"}
              </span>
            ) : (
              <span className="ml-auto rounded-full border border-[#323c5a] px-2.5 py-0.5 text-xs text-slate-400">Not connected</span>
            )}
          </p>
          <p className="mt-2 text-sm leading-relaxed text-slate-400">
            The media agent reads the folders on this PC&apos;s drives (and later copies sold films onto a customer&apos;s USB). It runs
            on the shop PC only and never opens it to the network.
          </p>
          {!token ? (
            <button className={`${dark.btn} mt-3`} onClick={() => void connect()}>
              <KeyRound className="h-4 w-4" /> {shop.agent_seen_at ? "Connect again (new key)" : "Create the connection key"}
            </button>
          ) : (
            <div className="mt-3 rounded-xl border border-[#323c5a] bg-[#0f1422] p-3">
              <p className="text-xs text-slate-400">On the shop PC, open PowerShell and run this once (the key is shown only now):</p>
              <code className="mt-2 block break-all font-mono text-xs leading-relaxed text-amber-200">{command}</code>
              <button
                className={`${dark.btn} mt-2 h-8 px-3 text-xs`}
                onClick={() => {
                  void navigator.clipboard?.writeText(command).then(() => {
                    setCopied(true);
                    window.setTimeout(() => setCopied(false), 2500);
                  });
                }}
              >
                {copied ? <Check className="h-3.5 w-3.5" /> : <Copy className="h-3.5 w-3.5" />} {copied ? "Copied" : "Copy command"}
              </button>
            </div>
          )}
        </li>
        <li>
          <p className="flex items-center gap-2 text-sm font-semibold">
            <span className="grid h-6 w-6 place-items-center rounded-full bg-amber-400 text-xs font-bold text-amber-950">2</span>
            Choose the folders that hold your films and series
          </p>
          <p className="mt-2 text-sm text-slate-400">Each folder inside becomes a category (Action, Series, Comedy...). The agent scans it in a few seconds.</p>
          <div className="mt-3 flex flex-col gap-2">
            {(report?.drives ?? []).map((d) => {
              const Icon = KIND_ICON[d.kind];
              return (
                <div key={d.root} className="rounded-xl border border-[#252e47] bg-[#0f1422] p-3">
                  <p className="flex items-center gap-2 text-sm font-semibold">
                    <Icon className="h-4 w-4 text-slate-400" /> {d.label ? `${d.label} (${d.root.replace("\\", "")})` : d.root}
                    <span className="ml-auto text-xs font-normal text-slate-500">
                      {formatBytes(d.free_bytes)} free of {formatBytes(d.total_bytes)}
                    </span>
                  </p>
                  <div className="mt-2 flex flex-wrap gap-1.5">
                    {d.folders.length === 0 && <span className="text-xs text-slate-500">No folders on this drive.</span>}
                    {d.folders.map((f) => (
                      <button key={f} disabled={busy} onClick={() => void add(f, d.kind, d.label)} className="rounded-full border border-[#323c5a] bg-[#1b2236] px-3 py-1 text-xs font-medium text-slate-200 hover:border-amber-400 hover:text-amber-200">
                        + {f.split("\\").filter(Boolean).pop()}
                      </button>
                    ))}
                  </div>
                </div>
              );
            })}
            {!report?.drives?.length && <p className="text-sm text-slate-500">The drives appear here once the media agent is connected.</p>}
          </div>
          <div className="mt-3 flex gap-2">
            <label htmlFor={pathId} className="sr-only">
              Folder path
            </label>
            <input id={pathId} className={dark.input} placeholder="Or type a folder, e.g. D:\Movies" value={path} onChange={(e) => setPath(e.target.value)} />
            <button className={dark.btn} disabled={!path.trim() || busy} onClick={() => void add(path.trim(), path.startsWith("\\\\") ? "network" : "fixed", "")}>
              Add
            </button>
          </div>
        </li>
      </ol>
      {error && <p className="mt-4 text-sm text-red-300">{error}</p>}
      <p className="mt-5 border-t border-[#252e47] pt-4 text-xs text-slate-500">
        Sell only films and series you hold the rights or a licence to sell.
      </p>
    </DarkDialog>
  );
}

/** The shop's prices: one default, and one per category. A title can still set its own. */
export function PricesDialog({ shop, categories, onClose, onSaved }: { shop: MovieShop; categories: MovieCategory[]; onClose: () => void; onSaved: () => void }) {
  const [def, setDef] = useState(String(shop.default_price));
  const [cats, setCats] = useState<Record<string, string>>(() => Object.fromEntries(categories.map((c) => [c.name, shop.category_prices[c.name] != null ? String(shop.category_prices[c.name]) : ""])));
  const [error, setError] = useState<string | null>(null);
  const defId = useId();

  async function save() {
    setError(null);
    const parsed: Record<string, number> = {};
    for (const [k, v] of Object.entries(cats)) if (v.trim() !== "") parsed[k] = Math.max(0, Math.round(Number(v)));
    try {
      await movies.setPrices(shop.id, Math.max(0, Math.round(Number(def) || 0)), parsed);
      onSaved();
      onClose();
    } catch (err) {
      setError(message(err));
    }
  }

  return (
    <DarkDialog title="Prices (IF Pay credits)" onClose={onClose}>
      <label htmlFor={defId} className={dark.label}>
        Every title (default)
      </label>
      <input id={defId} className={dark.input} inputMode="numeric" value={def} onChange={(e) => setDef(e.target.value.replace(/[^0-9]/g, ""))} />
      <p className="mt-5 mb-2 text-xs font-semibold tracking-wider text-slate-500 uppercase">By category</p>
      <div className="flex flex-col gap-2">
        {categories.map((c) => (
          <div key={c.name} className="grid grid-cols-[1fr_7rem] items-center gap-3">
            <span className="min-w-0 truncate text-sm">
              {c.name} <span className="text-xs text-slate-500">· {titlesLabel(c.count)}</span>
            </span>
            <input
              aria-label={`Price for ${c.name}`}
              className={dark.input}
              inputMode="numeric"
              placeholder={def}
              value={cats[c.name] ?? ""}
              onChange={(e) => setCats({ ...cats, [c.name]: e.target.value.replace(/[^0-9]/g, "") })}
            />
          </div>
        ))}
        {categories.length === 0 && <p className="text-sm text-slate-500">Categories appear after the first scan.</p>}
      </div>
      {error && <p className="mt-3 text-sm text-red-300">{error}</p>}
      <div className="mt-5 flex justify-end gap-2">
        <button className={dark.btn} onClick={onClose}>
          Cancel
        </button>
        <button className={dark.amber} onClick={() => void save()}>
          <Check className="h-4 w-4" /> Save prices
        </button>
      </div>
    </DarkDialog>
  );
}

/** Correct a title's name, year or category, set its own price, or hide it from the catalogue. */
export function EditTitleDialog({ title, onClose, onSaved }: { title: MovieTitle; onClose: () => void; onSaved: (t: MovieTitle) => void }) {
  const [name, setName] = useState(title.title);
  const [year, setYear] = useState(title.year ? String(title.year) : "");
  const [category, setCategory] = useState(title.category);
  const [price, setPrice] = useState(title.own_price != null ? String(title.own_price) : "");
  const [hidden, setHidden] = useState(title.hidden);
  const [description, setDescription] = useState(title.description);
  // The poster: a new picture to upload, or back to the folder's own picture.
  const [poster, setPoster] = useState<File | null>(null);
  const [clearPoster, setClearPoster] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const ids = { name: useId(), year: useId(), category: useId(), price: useId(), description: useId(), poster: useId() };
  const preview = useMemo(() => (poster ? URL.createObjectURL(poster) : null), [poster]);
  useEffect(() => () => void (preview && URL.revokeObjectURL(preview)), [preview]);

  async function save() {
    setError(null);
    setBusy(true);
    try {
      let saved = await movies.editTitle(title.id, {
        title: name,
        year: year ? Number(year) : null,
        category,
        price: price ? Number(price) : null,
        hidden,
        description,
      });
      if (poster) saved = await movies.setPoster(title.id, poster);
      else if (clearPoster) saved = await movies.clearPoster(title.id);
      onSaved(saved);
      onClose();
    } catch (err) {
      setError(message(err));
    } finally {
      setBusy(false);
    }
  }

  const shown = { ...title, title: name, has_cover: preview ? true : clearPoster ? false : title.has_cover };
  return (
    <DarkDialog title="Edit title" onClose={onClose} wide>
      <p className="mb-4 truncate font-mono text-xs text-slate-500" title={title.relative_path}>
        {title.relative_path}
      </p>
      <div className="grid gap-5 sm:grid-cols-[150px_1fr]">
        <div>
          <MovieCover title={shown} src={preview ?? undefined} />
          <label htmlFor={ids.poster} className={`${dark.btn} mt-2 h-9 w-full cursor-pointer text-xs`}>
            <ImagePlus className="h-3.5 w-3.5" /> {title.has_cover || preview ? "Change poster" : "Add a poster"}
          </label>
          <input
            id={ids.poster}
            type="file"
            accept="image/jpeg,image/png,image/webp"
            className="sr-only"
            onChange={(e) => {
              setPoster(e.target.files?.[0] ?? null);
              setClearPoster(false);
            }}
          />
          {(title.cover_locked || poster) && !clearPoster && (
            <button
              type="button"
              className="mt-1.5 w-full text-[11px] text-slate-400 hover:text-white"
              onClick={() => {
                setPoster(null);
                setClearPoster(Boolean(title.cover_locked));
              }}
            >
              {poster ? "Undo the new poster" : "Use the folder's picture"}
            </button>
          )}
          <p className="mt-1 text-[10.5px] leading-snug text-slate-500">JPEG, PNG or WebP up to 3 MB. Your poster stays when the folder is scanned again.</p>
        </div>
        <div>
          <div className="grid grid-cols-[1fr_110px] gap-3">
            <div>
              <label htmlFor={ids.name} className={dark.label}>
                Title
              </label>
              <input id={ids.name} className={dark.input} value={name} onChange={(e) => setName(e.target.value)} />
            </div>
            <div>
              <label htmlFor={ids.year} className={dark.label}>
                Year
              </label>
              <input id={ids.year} className={dark.input} inputMode="numeric" value={year} onChange={(e) => setYear(e.target.value.replace(/[^0-9]/g, "").slice(0, 4))} />
            </div>
            <div>
              <label htmlFor={ids.category} className={dark.label}>
                Category
              </label>
              <input id={ids.category} className={dark.input} value={category} onChange={(e) => setCategory(e.target.value)} />
            </div>
            <div>
              <label htmlFor={ids.price} className={dark.label}>
                Own price
              </label>
              <input id={ids.price} className={dark.input} inputMode="numeric" placeholder="Category" value={price} onChange={(e) => setPrice(e.target.value.replace(/[^0-9]/g, ""))} />
            </div>
          </div>
          <label htmlFor={ids.description} className={`${dark.label} mt-3`}>
            Short description
          </label>
          <textarea id={ids.description} className={`${dark.input} h-24 py-2`} maxLength={2000} value={description} onChange={(e) => setDescription(e.target.value)} />
          <label className="mt-3 flex items-center gap-2 text-sm text-slate-300">
            <input type="checkbox" checked={hidden} onChange={(e) => setHidden(e.target.checked)} className="h-4 w-4 accent-amber-400" />
            Hide from the catalogue
          </label>
        </div>
      </div>
      {error && <p className="mt-3 text-sm text-red-300">{error}</p>}
      <div className="mt-5 flex justify-end gap-2">
        <button className={dark.btn} onClick={onClose} disabled={busy}>
          Cancel
        </button>
        <button className={dark.amber} onClick={() => void save()} disabled={busy}>
          <Check className="h-4 w-4" /> {busy ? "Saving..." : "Save"}
        </button>
      </div>
    </DarkDialog>
  );
}

/** Renames something (a shop, a library): its current name, Save or Cancel. */
export function RenameDialog({ title, label, current, onSave, onClose }: { title: string; label: string; current: string; onSave: (name: string) => Promise<unknown>; onClose: () => void }) {
  const [name, setName] = useState(current);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const id = useId();
  async function save() {
    setBusy(true);
    setError(null);
    try {
      await onSave(name.trim());
      onClose();
    } catch (err) {
      setError(message(err));
    } finally {
      setBusy(false);
    }
  }
  return (
    <DarkDialog title={title} onClose={onClose}>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          void save();
        }}
      >
        <label htmlFor={id} className={dark.label}>
          {label}
        </label>
        <input id={id} className={dark.input} maxLength={120} value={name} onChange={(e) => setName(e.target.value)} autoFocus />
        {error && <p className="mt-3 text-sm text-red-300">{error}</p>}
        <div className="mt-5 flex justify-end gap-2">
          <button type="button" className={dark.btn} onClick={onClose} disabled={busy}>
            Cancel
          </button>
          <button className={dark.amber} disabled={busy || !name.trim() || name.trim() === current}>
            <Check className="h-4 w-4" /> Save
          </button>
        </div>
      </form>
    </DarkDialog>
  );
}
