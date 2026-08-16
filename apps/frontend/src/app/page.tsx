"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { useAuth } from "@/lib/auth-context";
import { PageLoading } from "@/components/ui";

export default function Home() {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (loading) return;
    router.replace(user ? "/orgs" : "/login");
  }, [loading, user, router]);

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-950">
      <PageLoading />
    </div>
  );
}
