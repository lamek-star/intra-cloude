"use client";

import { usePathname, useRouter } from "next/navigation";
import { useEffect } from "react";
import { useAuth } from "@/lib/auth-context";
import { AppShell } from "@/components/AppShell";
import { Spinner } from "@/components/ui";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
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

  return <AppShell>{children}</AppShell>;
}
