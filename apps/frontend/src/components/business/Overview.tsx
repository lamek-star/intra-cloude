"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { listRecords } from "@/lib/business";
import { Card, PageLoading } from "@/components/ui";
import { useBusiness } from "./BusinessApp";

const COUNTS: { key: string; label: string; href: string }[] = [
  { key: "part", label: "Products", href: "/products" },
  { key: "part_number", label: "Part numbers", href: "/part-numbers" },
  { key: "warehouse", label: "Warehouses", href: "/warehouses" },
  { key: "supplier", label: "Suppliers", href: "/suppliers" },
  { key: "customer", label: "Customers", href: "/customers" },
  { key: "sales_order", label: "Sales", href: "/sales" },
];

const ACTIONS: { label: string; hint: string; href: string }[] = [
  { label: "Receive stock", hint: "Goods have arrived", href: "/receive" },
  { label: "New sale", hint: "Sell to a customer", href: "/sales/new" },
  { label: "Search a part number", hint: "Find a product by its number", href: "/part-numbers" },
];

/** A plain starting point: how much is recorded and the three things a shop does all day. The
 * counts are the server's own totals; nothing is summed or derived in the browser. */
export default function Overview() {
  const { schema, instance } = useBusiness();
  const [counts, setCounts] = useState<Record<string, number> | null>(null);

  useEffect(() => {
    let cancelled = false;
    Promise.all(
      COUNTS.map(async (c) => [c.key, (await listRecords(schema, c.key, { limit: 1 })).count] as const),
    )
      .then((pairs) => {
        if (!cancelled) setCounts(Object.fromEntries(pairs));
      })
      .catch(() => {
        if (!cancelled) setCounts({});
      });
    return () => {
      cancelled = true;
    };
  }, [schema]);

  const base = `/apps/${instance.id}`;
  return (
    <div className="space-y-8">
      <section aria-labelledby="quick-title">
        <h2 id="quick-title" className="mb-3 text-sm font-semibold text-slate-600">
          What would you like to do?
        </h2>
        <div className="grid gap-3 sm:grid-cols-3">
          {ACTIONS.map((a) => (
            <Link key={a.href} href={`${base}${a.href}`} className="block">
              <Card className="h-full transition-colors hover:border-brand-400/40 hover:bg-slate-50">
                <p className="font-medium text-slate-900">{a.label}</p>
                <p className="mt-1 text-xs text-slate-500">{a.hint}</p>
              </Card>
            </Link>
          ))}
        </div>
      </section>

      <section aria-labelledby="counts-title">
        <h2 id="counts-title" className="mb-3 text-sm font-semibold text-slate-600">
          At a glance
        </h2>
        {!counts ? (
          <PageLoading />
        ) : (
          <ul className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
            {COUNTS.map((c) => (
              <li key={c.key}>
                <Link href={`${base}${c.href}`} className="block">
                  <Card className="transition-colors hover:border-brand-400/40 hover:bg-slate-50">
                    <span className="block text-xs text-slate-500">{c.label}</span>
                    <span className="mt-1 block text-2xl font-semibold tabular-nums text-slate-900">{counts[c.key] ?? "—"}</span>
                  </Card>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
