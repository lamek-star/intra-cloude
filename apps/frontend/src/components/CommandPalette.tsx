"use client";

import { useRouter } from "next/navigation";
import { useEffect, useMemo, useRef, useState } from "react";
import { Building2, LayoutDashboard, LogOut, Search } from "lucide-react";
import { api, ApiError, type Organization } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";

type Item = {
  id: string;
  label: string;
  hint?: string;
  icon: React.ComponentType<{ className?: string }>;
  action: () => void;
};

/** Ctrl/Cmd+K global search (Section 51 of the professionalization
 * brief). Kept to real, currently-reachable destinations plus the
 * user's actual organizations fetched live -- not a speculative list of
 * every conceivable future action, since only Dashboard/Organizations
 * exist as top-level nav today. */
export function CommandPalette({ open, setOpen }: { open: boolean; setOpen: (open: boolean) => void }) {
  const router = useRouter();
  const { logout } = useAuth();
  const [query, setQuery] = useState("");
  const [orgs, setOrgs] = useState<Organization[] | null>(null);
  const [activeIndex, setActiveIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    function onKeyDown(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setOpen(!open);
      } else if (e.key === "Escape") {
        setOpen(false);
      }
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [open, setOpen]);

  useEffect(() => {
    // Reset the form each time the palette opens, not a state-sync loop.
    if (!open) return;
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setQuery("");
    setActiveIndex(0);
    inputRef.current?.focus();
    if (orgs === null) {
      api
        .get<Organization[]>("/organizations/")
        .then(setOrgs)
        .catch((err) => {
          if (!(err instanceof ApiError)) setOrgs([]);
        });
    }
  }, [open, orgs]);

  const items = useMemo<Item[]>(() => {
    const base: Item[] = [
      { id: "dashboard", label: "Dashboard", icon: LayoutDashboard, action: () => router.push("/dashboard") },
      { id: "orgs", label: "Organizations", icon: Building2, action: () => router.push("/orgs") },
      ...(orgs ?? []).map((org) => ({
        id: `org-${org.id}`,
        label: org.name,
        hint: `/${org.slug}`,
        icon: Building2,
        action: () => router.push(`/orgs/${org.id}`),
      })),
      { id: "logout", label: "Log out", icon: LogOut, action: () => logout().then(() => router.push("/login")) },
    ];
    if (!query.trim()) return base;
    const q = query.toLowerCase();
    return base.filter((i) => i.label.toLowerCase().includes(q));
  }, [orgs, query, router, logout]);

  function select(item: Item) {
    setOpen(false);
    item.action();
  }

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-[60] flex items-start justify-center p-4 pt-24">
      <div className="absolute inset-0 bg-slate-900/40" onClick={() => setOpen(false)} />
      <div className="relative w-full max-w-lg overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-2xl">
        <div className="flex items-center gap-2.5 border-b border-slate-100 px-4 py-3">
          <Search className="h-4 w-4 shrink-0 text-slate-400" />
          <input
            ref={inputRef}
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              setActiveIndex(0);
            }}
            onKeyDown={(e) => {
              if (e.key === "ArrowDown") {
                e.preventDefault();
                setActiveIndex((i) => Math.min(i + 1, items.length - 1));
              } else if (e.key === "ArrowUp") {
                e.preventDefault();
                setActiveIndex((i) => Math.max(i - 1, 0));
              } else if (e.key === "Enter" && items[activeIndex]) {
                select(items[activeIndex]);
              }
            }}
            placeholder="Search Intra-Cloud…"
            className="w-full text-sm text-slate-900 outline-none placeholder:text-slate-400"
          />
          <kbd className="shrink-0 rounded border border-slate-200 bg-slate-50 px-1.5 py-0.5 text-[10px] text-slate-400">
            Esc
          </kbd>
        </div>
        <div className="max-h-80 overflow-y-auto p-1.5">
          {items.length === 0 ? (
            <p className="px-3 py-6 text-center text-sm text-slate-400">No matches.</p>
          ) : (
            items.map((item, i) => (
              <button
                key={item.id}
                onClick={() => select(item)}
                onMouseEnter={() => setActiveIndex(i)}
                className={`flex w-full items-center gap-2.5 rounded-lg px-3 py-2 text-left text-sm ${
                  i === activeIndex ? "bg-indigo-50 text-indigo-700" : "text-slate-700"
                }`}
              >
                <item.icon className="h-4 w-4 shrink-0 text-slate-400" />
                <span className="min-w-0 flex-1 truncate">{item.label}</span>
                {item.hint && <span className="shrink-0 text-xs text-slate-400">{item.hint}</span>}
              </button>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
