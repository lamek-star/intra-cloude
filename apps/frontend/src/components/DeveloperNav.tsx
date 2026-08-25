"use client";

import Link from "next/link";
import { useEffect, useRef } from "react";
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

const TABS: { key: string; label: string; icon: LucideIcon }[] = [
  { key: "", label: "Overview", icon: Gauge },
  { key: "applications", label: "Applications", icon: AppWindow },
  { key: "environments", label: "Environments", icon: Layers3 },
  { key: "api-keys", label: "API Keys", icon: KeyRound },
  { key: "storage", label: "Storage", icon: HardDrive },
  { key: "database", label: "Database", icon: Database },
  { key: "auth", label: "Auth", icon: ShieldCheck },
  { key: "webhooks", label: "Webhooks", icon: Webhook },
  { key: "api-logs", label: "API Logs", icon: ScrollText },
  { key: "usage", label: "Usage", icon: BarChart3 },
  { key: "sdks", label: "SDKs", icon: Package },
  { key: "docs", label: "Docs", icon: BookOpen },
];

/** The Developer portal's sub-nav (Section 6 of the professionalization
 * brief). Every organization member can see it; individual actions
 * inside each tab still enforce real permissions server-side same as
 * everywhere else -- this only organizes navigation, never authorizes. */
export function DeveloperNav({ orgId, active }: { orgId: string; active: string }) {
  const base = `/orgs/${orgId}/developer`;
  const activeRef = useRef<HTMLAnchorElement>(null);

  useEffect(() => {
    activeRef.current?.scrollIntoView({ block: "nearest", inline: "nearest" });
  }, [active]);

  return (
    <nav className="mb-6 flex gap-1 overflow-x-auto border-b border-slate-200 pb-px">
      {TABS.map((tab) => {
        const href = tab.key ? `${base}/${tab.key}` : base;
        const isActive = tab.key === active;
        return (
          <Link
            key={tab.key}
            ref={isActive ? activeRef : undefined}
            href={href}
            className={`flex shrink-0 items-center gap-1.5 border-b-2 px-3 py-2.5 text-sm font-medium transition-colors ${
              isActive
                ? "border-indigo-600 text-indigo-600"
                : "border-transparent text-slate-500 hover:border-slate-200 hover:text-slate-800"
            }`}
          >
            <tab.icon className="h-3.5 w-3.5" />
            {tab.label}
          </Link>
        );
      })}
    </nav>
  );
}
