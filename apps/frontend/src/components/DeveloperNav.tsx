"use client";

import Link from "next/link";
import {
  AppWindow,
  BarChart3,
  BookOpen,
  Database,
  Gauge,
  HardDrive,
  KeyRound,
  Layers3,
  Package,
  ScrollText,
  ShieldCheck,
  Webhook,
  type LucideIcon,
} from "lucide-react";

type Tab = { key: string; label: string; icon: LucideIcon };

// Grouped instead of one flat row (Section 12 of the Environment
// Management brief): the previous single `overflow-x-auto` row went
// wider than the viewport at any width below ~1024px, producing a
// horizontal scrollbar that hid Usage/SDKs/Docs entirely from anyone
// who didn't think to scroll a *tab bar* sideways. Grouping into
// semantic clusters and letting the whole nav wrap (`flex-wrap`, no
// horizontal scroll) keeps every tab visible and reachable at any
// width without hiding anything behind a "More" menu.
const GROUPS: Tab[][] = [
  [
    { key: "", label: "Overview", icon: Gauge },
    { key: "applications", label: "Applications", icon: AppWindow },
    { key: "environments", label: "Environments", icon: Layers3 },
  ],
  [
    { key: "api-keys", label: "API Keys", icon: KeyRound },
    { key: "auth", label: "Auth", icon: ShieldCheck },
    { key: "webhooks", label: "Webhooks", icon: Webhook },
  ],
  [
    { key: "storage", label: "Storage", icon: HardDrive },
    { key: "database", label: "Database", icon: Database },
  ],
  [
    { key: "api-logs", label: "API Logs", icon: ScrollText },
    { key: "usage", label: "Usage", icon: BarChart3 },
  ],
  [
    { key: "sdks", label: "SDKs", icon: Package },
    { key: "docs", label: "Docs", icon: BookOpen },
  ],
];

/** The Developer portal's sub-nav (Section 6 of the professionalization
 * brief). Every organization member can see it; individual actions
 * inside each tab still enforce real permissions server-side same as
 * everywhere else -- this only organizes navigation, never authorizes. */
export function DeveloperNav({ orgId, active }: { orgId: string; active: string }) {
  const base = `/orgs/${orgId}/developer`;

  return (
    <nav
      aria-label="Developer sections"
      className="mb-6 flex flex-wrap items-center gap-x-1 gap-y-1.5 border-b border-slate-200 pb-2"
    >
      {GROUPS.map((group, i) => (
        <div key={i} className="flex flex-wrap items-center gap-1">
          {i > 0 && (
            <span aria-hidden="true" className="mx-1.5 hidden h-4 w-px bg-slate-200 sm:inline-block" />
          )}
          {group.map((tab) => {
            const href = tab.key ? `${base}/${tab.key}` : base;
            const isActive = tab.key === active;
            return (
              <Link
                key={tab.key}
                href={href}
                aria-current={isActive ? "page" : undefined}
                className={`flex shrink-0 items-center gap-1.5 rounded-md px-2.5 py-1.5 text-sm font-medium transition-colors ${
                  isActive
                    ? "bg-indigo-50 text-indigo-600"
                    : "text-slate-500 hover:bg-slate-100 hover:text-slate-800"
                }`}
              >
                <tab.icon aria-hidden="true" className="h-3.5 w-3.5" />
                {tab.label}
              </Link>
            );
          })}
        </div>
      ))}
    </nav>
  );
}
