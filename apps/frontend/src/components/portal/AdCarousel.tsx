"use client";

import { useEffect, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { portalApi, type PortalAd } from "@/lib/portal";
import { AdBanner } from "@/components/movies/AdBanner";

const ROTATE_MS = 6000;

/** The shop's ads at the top of the portal: swipe between them; they move on by themselves unless the visitor prefers
 * reduced motion or is touching them. A film ad opens the film; a web ad opens in a new tab with no referrer. */
export function AdCarousel({ shopId, shopName, onFilm }: { shopId: string; shopName: string; onFilm?: (filmId: string) => void }) {
  const ads = useQuery({ queryKey: ["portal", shopId, "ads"], queryFn: () => portalApi.ads(shopId), staleTime: 5 * 60_000 });
  const track = useRef<HTMLDivElement>(null);
  const [index, setIndex] = useState(0);
  const [held, setHeld] = useState(false);
  const list = ads.data ?? [];

  useEffect(() => {
    if (list.length < 2 || held || window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    const t = window.setInterval(() => {
      const el = track.current;
      if (!el) return;
      const next = (Math.round(el.scrollLeft / el.clientWidth) + 1) % list.length;
      el.scrollTo({ left: next * el.clientWidth, behavior: "smooth" });
    }, ROTATE_MS);
    return () => window.clearInterval(t);
  }, [list.length, held]);

  if (list.length === 0) return null;

  async function tap(ad: PortalAd) {
    const target = await portalApi.tapAd(shopId, ad.id).catch(() => null);
    if (!target) return;
    if (target.film) onFilm?.(target.film);
    else if (target.link && /^https?:\/\//.test(target.link)) window.open(target.link, "_blank", "noopener,noreferrer");
  }

  return (
    <section aria-label="Ads" aria-roledescription="carousel" className="mb-4">
      <div
        ref={track}
        onScroll={(e) => setIndex(Math.round(e.currentTarget.scrollLeft / Math.max(1, e.currentTarget.clientWidth)))}
        onPointerDown={() => setHeld(true)}
        onPointerUp={() => setHeld(false)}
        onPointerLeave={() => setHeld(false)}
        className="flex snap-x snap-mandatory overflow-x-auto [scrollbar-width:none] [&::-webkit-scrollbar]:hidden"
      >
        {list.map((ad, i) => (
          <div key={ad.id} className="w-full shrink-0 snap-center" aria-roledescription="slide" aria-label={`${i + 1} of ${list.length}`}>
            <AdBanner
              ad={ad}
              shopName={shopName}
              src={portalApi.adPictureUrl(shopId, ad)}
              onTap={ad.film || ad.link ? () => void tap(ad) : undefined}
            />
          </div>
        ))}
      </div>
      {list.length > 1 && (
        <div className="mt-2 flex justify-center gap-1.5">
          {list.map((ad, i) => (
            <button
              key={ad.id}
              aria-label={`Show ad ${i + 1}`}
              aria-current={i === index}
              onClick={() => track.current?.scrollTo({ left: i * track.current.clientWidth, behavior: "smooth" })}
              className={`h-1.5 rounded-full transition-all ${i === index ? "w-5 bg-amber-400" : "w-1.5 bg-slate-600"}`}
            />
          ))}
        </div>
      )}
    </section>
  );
}
