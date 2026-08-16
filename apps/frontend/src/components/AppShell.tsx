"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { useAuth } from "@/lib/auth-context";

export function AppShell({ children }: { children: React.ReactNode }) {
  const { user, logout } = useAuth();
  const router = useRouter();
  const [menuOpen, setMenuOpen] = useState(false);

  return (
    <div className="flex min-h-screen bg-slate-950 text-slate-100">
      <aside className="hidden w-56 shrink-0 border-r border-white/10 bg-slate-950/60 sm:flex sm:flex-col">
        <div className="flex h-14 items-center gap-2 border-b border-white/10 px-4">
          <div className="flex h-6 w-6 items-center justify-center rounded bg-indigo-500 text-xs font-bold text-white">
            P
          </div>
          <span className="text-sm font-semibold text-white">Private Data Cloud</span>
        </div>
        <nav className="flex flex-1 flex-col gap-0.5 p-3 text-sm">
          <SidebarLink href="/orgs" icon="🏢">
            Organizations
          </SidebarLink>
        </nav>
        <div className="border-t border-white/10 p-3 text-[11px] text-slate-600">
          Self-hosted · local-first
        </div>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-14 shrink-0 items-center justify-between border-b border-white/10 px-4 sm:px-6">
          <Link href="/orgs" className="text-sm font-semibold text-white sm:hidden">
            Private Data Cloud
          </Link>
          <div className="hidden sm:block" />
          <div className="relative">
            <button
              onClick={() => setMenuOpen((v) => !v)}
              className="flex items-center gap-2 rounded-md px-2 py-1.5 text-sm text-slate-300 hover:bg-white/5"
            >
              <span className="flex h-6 w-6 items-center justify-center rounded-full bg-indigo-500/20 text-xs font-medium text-indigo-300">
                {user?.email.slice(0, 1).toUpperCase()}
              </span>
              <span className="hidden sm:inline">{user?.email}</span>
              <span className="text-slate-600">▾</span>
            </button>
            {menuOpen && (
              <>
                <div className="fixed inset-0 z-10" onClick={() => setMenuOpen(false)} />
                <div className="absolute right-0 z-20 mt-1 w-48 rounded-md border border-white/10 bg-slate-900 py-1 shadow-xl">
                  <div className="border-b border-white/10 px-3 py-2 text-xs text-slate-500">
                    Signed in as
                    <div className="truncate text-slate-300">{user?.email}</div>
                  </div>
                  <button
                    onClick={async () => {
                      setMenuOpen(false);
                      await logout();
                      router.push("/login");
                    }}
                    className="block w-full px-3 py-2 text-left text-sm text-slate-300 hover:bg-white/5 hover:text-white"
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
  );
}

function SidebarLink({
  href,
  icon,
  children,
}: {
  href: string;
  icon: string;
  children: React.ReactNode;
}) {
  return (
    <Link
      href={href}
      className="flex items-center gap-2.5 rounded-md px-2.5 py-2 text-slate-300 hover:bg-white/5 hover:text-white"
    >
      <span className="text-base leading-none">{icon}</span>
      {children}
    </Link>
  );
}
