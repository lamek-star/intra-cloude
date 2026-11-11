"use client";

import { useEffect, useRef, useState } from "react";
import { ApiError } from "@/lib/api";
import { openServiceApp } from "@/lib/service-apps";
import { ErrorBanner, LinkButton, PageLoading } from "@/components/ui";

/** Where an application sends someone who is not signed in to it: IntraForge (already signed in,
 * or after its own sign-in page) opens the application again for them. */
export default function OpenClient({ appId }: { appId: string }) {
  const [error, setError] = useState<string | null>(null);
  const started = useRef(false);

  useEffect(() => {
    if (started.current) return;
    started.current = true;
    openServiceApp(appId).catch((err: unknown) => {
      if (err instanceof ApiError && err.status === 404)
        setError("This application is not available to you, or it has been removed.");
      else if (err instanceof ApiError && err.status === 403)
        setError("You don't have access to this application. Ask an administrator to give you a Spare Parts role.");
      else setError(err instanceof ApiError ? err.message : "The application could not be opened.");
    });
  }, [appId]);

  if (!error) return <PageLoading />;
  return (
    <div className="mx-auto max-w-lg">
      <ErrorBanner message={error} />
      <div className="mt-4">
        <LinkButton href="/apps">Back to Apps</LinkButton>
      </div>
    </div>
  );
}
