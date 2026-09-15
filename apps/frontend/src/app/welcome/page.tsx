"use client";

import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Building2, LogIn, PartyPopper } from "lucide-react";
import { useAuth } from "@/lib/auth-context";
import { isSafeNextPath } from "@/lib/safe-next";
import { Button, Card, PageLoading } from "@/components/ui";

/**
 * One-time step shown right after registration (see register/page.tsx's
 * redirect). Never shown again automatically — there is nothing that
 * re-prompts a user who already chose to continue without an
 * organization, so there is nothing here to "dismiss permanently" or
 * persist. An organization is optional account state, not a required
 * step every user must clear.
 */
export default function WelcomePage() {
  return (
    <Suspense
      fallback={
        <div className="flex min-h-screen items-center justify-center bg-surface-canvas">
          <PageLoading />
        </div>
      }
    >
      <WelcomePageInner />
    </Suspense>
  );
}

function WelcomePageInner() {
  const { user, loading } = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();
  const next = searchParams.get("next");
  const [showJoinInfo, setShowJoinInfo] = useState(false);

  useEffect(() => {
    if (!loading && !user) router.replace(isSafeNextPath(next) ? `/login?next=${encodeURIComponent(next)}` : "/login");
  }, [loading, user, router, next]);

  if (loading || !user) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-surface-canvas">
        <PageLoading />
      </div>
    );
  }

  function continueOn() {
    if (isSafeNextPath(next)) {
      window.location.assign(next);
    } else {
      router.push("/dashboard");
    }
  }

  function createOrganization() {
    router.push(isSafeNextPath(next) ? `/orgs?next=${encodeURIComponent(next)}` : "/orgs");
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-surface-canvas px-4">
      <div className="w-full max-w-md">
        <div className="mb-6 flex flex-col items-center text-center">
          <PartyPopper className="mb-3 h-8 w-8 text-brand-600" />
          <h1 className="text-lg font-semibold text-text-primary">Welcome to IntraForge</h1>
          <p className="mt-1 text-sm text-slate-500">
            Your account is ready, {user.first_name || user.email}. What would you like to do?
          </p>
        </div>

        <div className="space-y-3">
          <Card className="flex items-center justify-between gap-3">
            <div>
              <p className="text-sm font-medium text-slate-900">Continue without an organization</p>
              <p className="mt-0.5 text-xs text-slate-500">
                Use your personal account now. Create or join an organization any time later.
              </p>
            </div>
            <Button onClick={continueOn}>Continue</Button>
          </Card>

          <Card className="flex items-center justify-between gap-3">
            <div className="flex items-center gap-2.5">
              <Building2 className="h-4 w-4 shrink-0 text-slate-400" />
              <div>
                <p className="text-sm font-medium text-slate-900">Create an organization</p>
                <p className="mt-0.5 text-xs text-slate-500">
                  For a team or business — workspaces, storage, and databases live here.
                </p>
              </div>
            </div>
            <Button variant="secondary" onClick={createOrganization}>
              Create
            </Button>
          </Card>

          <Card>
            <div className="flex items-center justify-between gap-3">
              <div className="flex items-center gap-2.5">
                <LogIn className="h-4 w-4 shrink-0 text-slate-400" />
                <div>
                  <p className="text-sm font-medium text-slate-900">Join an organization</p>
                  <p className="mt-0.5 text-xs text-slate-500">Already invited somewhere?</p>
                </div>
              </div>
              <Button variant="secondary" onClick={() => setShowJoinInfo((v) => !v)}>
                {showJoinInfo ? "Hide" : "How?"}
              </Button>
            </div>
            {showJoinInfo && (
              <p className="mt-3 border-t border-slate-100 pt-3 text-xs text-slate-500">
                Ask that organization&apos;s administrator to add you by your account email (
                {user.email}). It will appear under{" "}
                <button
                  type="button"
                  onClick={() => router.push("/orgs")}
                  className="text-brand-600 underline underline-offset-2 hover:text-brand-500"
                >
                  Organizations
                </button>{" "}
                as soon as they do — no action needed from you until then.
              </p>
            )}
          </Card>
        </div>
      </div>
    </div>
  );
}
