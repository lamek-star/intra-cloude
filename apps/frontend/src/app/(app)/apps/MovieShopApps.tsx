"use client";

import { useState } from "react";
import { useQueries } from "@tanstack/react-query";
import { Clapperboard, ExternalLink } from "lucide-react";
import type { Organization } from "@/lib/api";
import { agentOnline, movies, titlesLabel } from "@/lib/movies";
import { CreateShopDialog } from "@/components/movies/MovieShops";
import { Badge, Button, Card, LinkButton } from "@/components/ui";

/** The Movie Shop on the Apps page, like every other app: each shop is an installed application, and "Movie Shop" is
 * offered under "Available to install" (needs movies.manage in an organization, checked by the server). */
export function useMovieShops(orgs: Organization[]) {
  const results = useQueries({
    queries: orgs.map((o) => ({ queryKey: ["movies", "shops", o.id], queryFn: () => movies.shops(o.id), retry: false })),
  });
  return results.flatMap((r, i) => (r.data ?? []).map((shop) => ({ shop, org: orgs[i] })));
}

export function MovieShopCards({ shops, showOrganization }: { shops: ReturnType<typeof useMovieShops>; showOrganization: boolean }) {
  return (
    <>
      {shops.map(({ shop, org }) => {
        const online = agentOnline(shop.agent_seen_at);
        return (
          <li key={shop.id}>
            <Card className="flex h-full flex-col gap-3">
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <h3 className="truncate text-base font-semibold text-slate-900">{shop.name}</h3>
                  <p className="text-sm text-slate-500">
                    Movie Shop{showOrganization ? ` · ${org.name}` : ""}
                  </p>
                </div>
                <Badge tone={online ? "success" : "warning"}>{online ? "Running" : "Media agent off"}</Badge>
              </div>
              <p className="text-xs text-slate-500">
                {titlesLabel(shop.titles)}
                {online ? ` · on ${shop.agent.computer || "the shop PC"}` : " · the catalogue still works; start the media agent to scan and copy"}
              </p>
              <div className="mt-auto flex flex-wrap gap-2 pt-1">
                <LinkButton href={`/movies/${shop.id}`}>
                  <ExternalLink className="h-4 w-4" />
                  Open
                </LinkButton>
              </div>
            </Card>
          </li>
        );
      })}
    </>
  );
}

export function MovieShopInstallCard({ orgs }: { orgs: Organization[] }) {
  const [creating, setCreating] = useState(false);
  return (
    <li>
      <Card className="flex h-full flex-col gap-3">
        <div className="flex items-center gap-2">
          <Clapperboard className="h-5 w-5 text-brand-600" aria-hidden="true" />
          <h3 className="text-base font-semibold text-slate-900">Movie Shop</h3>
        </div>
        <p className="text-sm text-slate-500">
          Sell films, series and music from the shop PC&apos;s own drives: copied to the customer&apos;s USB, paid with IF Pay or cash, with a customer
          portal on the shop Wi-Fi.
        </p>
        <div className="mt-auto">
          <Button onClick={() => setCreating(true)} disabled={orgs.length === 0} aria-label="Install Movie Shop">
            Install
          </Button>
        </div>
      </Card>
      {creating && <CreateShopDialog organizations={orgs} onClose={() => setCreating(false)} />}
    </li>
  );
}
