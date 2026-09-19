"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { api, ApiError, type AppInstance, type RuntimeStatus } from "@/lib/api";
import { loadSchema, type BusinessSchema } from "@/lib/business";
import { Button, ErrorBanner, Input, LinkButton, PageLoading } from "@/components/ui";

type BusinessContextValue = { schema: BusinessSchema; instance: AppInstance };

const BusinessContext = createContext<BusinessContextValue | null>(null);

export function useBusiness(): BusinessContextValue {
  const value = useContext(BusinessContext);
  if (!value) throw new Error("useBusiness must be used inside <BusinessApp>.");
  return value;
}

// Grouped like the reference spare-parts application (Catalogue / Inventory / Purchasing / Sales),
// but listing ONLY what the IntraForge backend supports correctly today. Quotations, returns,
// reports and the rest of the reference app's screens are not shown until they are real.
const NAV_GROUPS: { label: string; items: { href: string; label: string }[] }[] = [
  { label: "", items: [{ href: "", label: "Overview" }] },
  {
    label: "Catalogue",
    items: [
      { href: "/products", label: "Products" },
      { href: "/part-numbers", label: "Part numbers" },
    ],
  },
  {
    label: "Inventory",
    items: [
      { href: "/inventory", label: "Stock" },
      { href: "/warehouses", label: "Warehouses" },
      { href: "/receive", label: "Receive stock" },
    ],
  },
  { label: "Purchasing", items: [{ href: "/suppliers", label: "Suppliers" }] },
  {
    label: "Sales",
    items: [
      { href: "/customers", label: "Customers" },
      { href: "/sales", label: "Sales" },
      { href: "/sales/new", label: "New sale" },
    ],
  },
];

/** The customer-facing shell for the Spare Parts / Inventory & Sales application: it loads the
 * instance and resolves every model/field/relationship id from the instance's own metadata, so the
 * screens below never hard-code an id or a table. */
export default function BusinessApp({ instanceId, children }: { instanceId: string; children: ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [searchText, setSearchText] = useState("");
  const base = `/apps/${instanceId}`;
  const [instance, setInstance] = useState<AppInstance | null>(null);
  // null until the schema has loaded; stays null when the application's setup did not finish
  const [schema, setSchema] = useState<BusinessSchema | null>(null);
  const [notReady, setNotReady] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [errorDetail, setErrorDetail] = useState<unknown>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const found = await api.get<AppInstance>(`/app-instances/${instanceId}/`);
        // Setup state is only readable by those who manage the app; anyone else just proceeds.
        const runtime = await api.get<RuntimeStatus>(`/app-instances/${instanceId}/runtime/`).catch(() => null);
        if (runtime && runtime.status !== "ready") {
          if (!cancelled) {
            setInstance(found);
            setNotReady(true);
          }
          return;
        }
        const loaded = await loadSchema(instanceId);
        if (!cancelled) {
          setInstance(found);
          setSchema(loaded);
        }
      } catch (err) {
        if (cancelled) return;
        setError(
          err instanceof ApiError && err.status === 404
            ? "That application wasn't found."
            : "The application couldn't be opened.",
        );
        setErrorDetail(err);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [instanceId]);

  if (error) return <ErrorBanner message={error} error={errorDetail} />;
  if (!instance) return <PageLoading />;

  const galleryHref = `/projects/${instance.project}/apps`;

  if (!schema && !notReady) return <PageLoading />;

  if (notReady || !schema) {
    return (
      <div className="mx-auto max-w-lg py-10 text-center">
        <h1 className="text-lg font-semibold text-slate-900">{instance.label} isn&apos;t ready yet</h1>
        <p className="mt-2 text-sm text-slate-500">
          Its setup didn&apos;t finish. Open Applications and choose &ldquo;Finish setup&rdquo;; nothing is lost.
        </p>
        <div className="mt-4">
          <LinkButton href={galleryHref} variant="primary">
            Go to Applications
          </LinkButton>
        </div>
      </div>
    );
  }

  return (
    <BusinessContext.Provider value={{ schema, instance }}>
      <div>
        <nav aria-label="Breadcrumb" className="mb-1 text-xs text-slate-400">
          <Link href={galleryHref} className="hover:text-slate-600">
            Applications
          </Link>
        </nav>
        <h1 className="text-xl font-semibold tracking-tight text-slate-900">{instance.label}</h1>
        <form
          role="search"
          className="mt-4 flex max-w-lg gap-2"
          onSubmit={(e) => {
            e.preventDefault();
            const q = searchText.trim();
            router.push(q ? `${base}/part-numbers?q=${encodeURIComponent(q)}` : `${base}/part-numbers`);
          }}
        >
          <label htmlFor="global-part-search" className="sr-only">
            Search part numbers
          </label>
          <Input
            id="global-part-search"
            type="search"
            value={searchText}
            placeholder="Search a part number, e.g. 04465-0K290"
            onChange={(e) => setSearchText(e.target.value)}
          />
          <Button type="submit" variant="secondary">
            Search
          </Button>
        </form>
        <nav aria-label="Application sections" className="mt-4 mb-6 flex flex-wrap items-center gap-x-4 gap-y-2 border-b border-slate-200 pb-2">
          {NAV_GROUPS.map((group) => (
            <div key={group.label || "root"} className="flex items-center gap-1">
              {group.label && (
                <span className="mr-1 text-[11px] font-semibold uppercase tracking-wide text-slate-400">{group.label}</span>
              )}
              {group.items.map((item) => {
                const href = `${base}${item.href}`;
                const active =
                  item.href === ""
                    ? pathname === base
                    : item.href === "/sales"
                      ? pathname === href || (pathname.startsWith(`${href}/`) && !pathname.startsWith(`${href}/new`))
                      : pathname === href || pathname.startsWith(`${href}/`);
                return (
                  <Link
                    key={item.label}
                    href={href}
                    aria-current={active ? "page" : undefined}
                    className={`rounded-lg px-3 py-1.5 text-sm font-medium transition-colors ${
                      active ? "bg-brand-50 text-brand-700" : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
                    }`}
                  >
                    {item.label}
                  </Link>
                );
              })}
            </div>
          ))}
        </nav>
        {children}
      </div>
    </BusinessContext.Provider>
  );
}
