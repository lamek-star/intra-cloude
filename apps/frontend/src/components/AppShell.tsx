"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useState } from "react";
import { Building2, ChevronDown, LayoutDashboard, LogOut, Search, type LucideIcon } from "lucide-react";
import { useAuth } from "@/lib/auth-context";
import { ConfirmProvider } from "@/components/ConfirmProvider";
import { CommandPalette } from "@/components/CommandPalette";

export function AppShell({ children }: { children: React.ReactNode }) {
  const { user, logout } = useAuth();
  const router = useRouter();
  const [menuOpen, setMenuOpen] = useState(false);
  const [paletteOpen, setPaletteOpen] = useState(false);

  async function handleLogout() {
    setMenuOpen(false);
    await logout();
    router.push("/login");
  }

  return (
    <ConfirmProvider>
      <CommandPalette open={paletteOpen} setOpen={setPaletteOpen} />
      <div className="flex min-h-screen bg-[#F5F6FB] text-slate-900">
        <aside className="hidden w-60 shrink-0 flex-col bg-gradient-to-b from-[#12163A] to-[#0B0E24] p-4 sm:flex">
          <div className="mb-6 flex items-center gap-2.5 px-1">
            <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-indigo-500 text-sm font-bold text-white">
              P
            </div>
            <span className="text-sm font-semibold text-white">Private Data Cloud</span>
          </div>

          <button
            onClick={() => setPaletteOpen(true)}
            className="mb-3 flex items-center gap-2.5 rounded-xl bg-white/5 px-3 py-2 text-left text-sm text-slate-400 hover:bg-white/10 hover:text-slate-200"
          >
            <Search className="h-4 w-4" />
            <span className="flex-1">Search…</span>
            <kbd className="rounded border border-white/10 bg-black/20 px-1.5 py-0.5 text-[10px]">Ctrl K</kbd>
          </button>

          <nav className="flex flex-1 flex-col gap-1 text-sm">
            <SidebarLink href="/dashboard" icon={LayoutDashboard}>
              Dashboard
            </SidebarLink>
            <SidebarLink href="/orgs" icon={Building2}>
              Organizations
            </SidebarLink>
          </nav>

          {user && (
            <div className="mt-4 space-y-1 border-t border-white/10 pt-4">
              <div className="flex items-center gap-2.5 rounded-xl bg-white/5 px-2.5 py-2.5">
                <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-indigo-500/25 text-xs font-semibold text-indigo-200">
                  {user.email.slice(0, 1).toUpperCase()}
                </span>
                <div className="min-w-0 flex-1">
                  <p className="truncate text-xs font-medium text-white">
                    {user.first_name || "Account"}
                  </p>
                  <p className="truncate text-[11px] text-slate-400">{user.email}</p>
                </div>
              </div>
              <button
                onClick={handleLogout}
                className="flex w-full items-center gap-2.5 rounded-xl px-2.5 py-2 text-xs font-medium text-red-300 hover:bg-white/5 hover:text-red-200"
              >
                <LogOut className="h-3.5 w-3.5" />
                Log out
              </button>
            </div>
          )}
        </aside>

        <div className="flex min-w-0 flex-1 flex-col">
          <header className="flex h-14 shrink-0 items-center justify-between border-b border-slate-200 bg-white px-4 sm:hidden">
            <Link href="/orgs" className="text-sm font-semibold text-slate-900">
              Private Data Cloud
            </Link>
            <div className="relative">
              <button
                onClick={() => setMenuOpen((v) => !v)}
                className="flex items-center gap-2 rounded-lg px-2 py-1.5 text-sm text-slate-600 hover:bg-slate-100"
              >
                <span className="flex h-6 w-6 items-center justify-center rounded-full bg-indigo-50 text-xs font-medium text-indigo-600">
                  {user?.email.slice(0, 1).toUpperCase()}
                </span>
                <ChevronDown className="h-3.5 w-3.5 text-slate-400" />
              </button>
              {menuOpen && (
                <>
                  <div className="fixed inset-0 z-10" onClick={() => setMenuOpen(false)} />
                  <div className="absolute right-0 z-20 mt-1 w-48 rounded-xl border border-slate-200 bg-white py-1 shadow-xl">
                    <div className="border-b border-slate-100 px-3 py-2 text-xs text-slate-400">
                      Signed in as
                      <div className="truncate text-slate-700">{user?.email}</div>
                    </div>
                    <button
                      onClick={handleLogout}
                      className="block w-full px-3 py-2 text-left text-sm text-slate-600 hover:bg-slate-50 hover:text-slate-900"
                    >
                      Log out
                    </button>
                  </div>
                </>
              )}
            </div>
          </header>
          <main className="flex-1 overflow-y-auto p-4 sm:p-8">
            <div className="mx-auto max-w-6xl">{children}</div>
          </main>
        </div>
      </div>
    </ConfirmProvider>
  );
}

function SidebarLink({
  href,
  icon: Icon,
  children,
}: {
  href: string;
  icon: LucideIcon;
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  const active = pathname === href || pathname?.startsWith(`${href}/`);
  return (
    <Link
      href={href}
      className={`flex items-center gap-2.5 rounded-xl px-3 py-2.5 transition-colors ${
        active ? "bg-indigo-500 text-white shadow-sm" : "text-slate-300 hover:bg-white/5 hover:text-white"
      }`}
    >
      <Icon className="h-4 w-4" strokeWidth={2} />
      {children}
    </Link>
  );
}
