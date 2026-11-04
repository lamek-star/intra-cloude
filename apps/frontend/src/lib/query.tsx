"use client";

import { useState, type ReactNode } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ApiError } from "@/lib/api";

/** Page data kept between visits (replica/design/frontend-smoothness.md step C): a page seen before shows
 * at once and refreshes in the background. The cache lives in this browser tab's memory only and is cleared
 * whenever the signed-in person changes (auth-context.tsx), so one person's data never shows to another. */
export function makeQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: {
        // Shown at once on a revisit; refreshed in the background once older than this.
        staleTime: 30_000,
        gcTime: 5 * 60_000,
        // A refusal (403, 404...) is an answer, not a hiccup: never retried. A network failure or 5xx once.
        retry: (failures, error) => !(error instanceof ApiError && error.status < 500) && failures < 1,
      },
    },
  });
}

export function QueryProvider({ children }: { children: ReactNode }) {
  const [client] = useState(makeQueryClient);
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}
