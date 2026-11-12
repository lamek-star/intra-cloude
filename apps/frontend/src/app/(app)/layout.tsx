"use client";

import { usePathname, useRouter } from "next/navigation";
import { useEffect } from "react";
import { useAuth } from "@/lib/auth-context";
import { AppShell } from "@/components/AppShell";
import { PasswordForm } from "@/components/PasswordForm";
import { Spinner } from "@/components/ui";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const { user, loading, refresh, logout } = useAuth();
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    // Come back here after signing in (e.g. an application's "open" page); the login page
    // validates the path before following it.
    if (!loading && !user)
      router.replace(pathname && pathname !== "/" ? `/login?next=${encodeURIComponent(pathname)}` : "/login");
  }, [loading, user, router, pathname]);

  if (loading || !user) {
    return (
      <div role="status" className="flex min-h-screen items-center justify-center bg-surface-canvas text-text-muted">
        <span className="sr-only">Loading…</span>
        <Spinner className="h-6 w-6" />
      </div>
    );
  }

  if (user.must_change_password) {
    return (
      <main className="grid min-h-screen place-items-center bg-surface-canvas p-6">
        <div className="w-full max-w-md space-y-4 rounded-2xl border border-border-subtle bg-white p-6 shadow-sm">
          <h1 className="text-lg font-semibold text-slate-900">Choose your own password</h1>
          <p className="text-sm text-slate-600">
            An administrator gave you a temporary password. Choose your own now; nothing else opens until you do.
          </p>
          <PasswordForm currentLabel="Temporary password" onDone={refresh} />
          <button type="button" onClick={() => void logout()} className="text-xs text-text-muted hover:underline">
            Sign out
          </button>
        </div>
      </main>
    );
  }

  return <AppShell>{children}</AppShell>;
}
