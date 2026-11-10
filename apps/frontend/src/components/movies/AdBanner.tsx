"use client";

import { ExternalLink, Play } from "lucide-react";
import { drawnCover } from "@/lib/movies";

export type BannerAd = {
  title: string;
  text: string;
  advertiser: string;
  film: string | null;
  link: string;
  has_picture: boolean;
};

/** One ad as customers see it on the portal (and as the owner previews it): the picture, or a drawn background, with
 * an "Ad" label naming who it is for. */
export function AdBanner({
  ad,
  src,
  shopName,
  onTap,
  compact = false,
}: {
  ad: BannerAd;
  src?: string;
  shopName: string;
  onTap?: () => void;
  compact?: boolean;
}) {
  const drawn = drawnCover(ad.title || "Ad");
  const action = ad.film ? "Watch" : ad.link ? "Open" : null;
  const body = (
    <div
      className="relative aspect-[16/9] w-full overflow-hidden sm:aspect-[16/7] rounded-2xl text-left shadow-[0_14px_30px_-16px_rgba(0,0,0,.9),inset_0_0_0_1px_rgba(255,255,255,.06)]"
      style={{
        background: `linear-gradient(120deg, ${drawn.from}, ${drawn.to})`,
      }}
    >
      {ad.has_picture && src && (
        // eslint-disable-next-line @next/next/no-img-element -- the shop's own ad picture, served by IntraForge
        <img
          src={src}
          alt=""
          className="absolute inset-0 h-full w-full object-cover"
        />
      )}
      <div className="absolute inset-0 bg-gradient-to-r from-black/85 via-black/45 to-transparent" />
      {compact ? (
        // A thumbnail (the owner's list): the picture and a short title only.
        <p
          className="relative flex h-full items-end p-2 text-[11px] leading-tight font-semibold text-white uppercase"
          style={{ fontFamily: "var(--font-display), sans-serif" }}
        >
          <span className="line-clamp-2">{ad.title}</span>
        </p>
      ) : (
        <div className="relative flex h-full flex-col justify-end p-4 text-white">
          <span className="mb-auto inline-flex w-fit items-center gap-1 rounded-full bg-black/55 px-2 py-0.5 text-[10px] font-bold tracking-wider uppercase backdrop-blur-sm">
            Ad · {ad.advertiser || shopName}
          </span>
          <p
            className={`${ad.has_picture ? "max-w-[62%]" : "max-w-[80%]"} line-clamp-2 text-lg leading-tight font-semibold tracking-wide uppercase [text-shadow:0_2px_10px_rgba(0,0,0,.7)] sm:text-xl`}
            style={{ fontFamily: "var(--font-display), sans-serif" }}
          >
            {ad.title || "Your ad's title"}
          </p>
          {ad.text && (
            <p
              className={`mt-1 line-clamp-1 sm:line-clamp-2 ${ad.has_picture ? "max-w-[62%]" : "max-w-[85%]"} text-xs text-slate-200`}
            >
              {ad.text}
            </p>
          )}
          {action && (
            <span className="mt-2 inline-flex w-fit items-center gap-1.5 rounded-lg bg-amber-400 px-3 py-1.5 text-xs font-bold text-amber-950">
              {ad.film ? (
                <Play className="h-3.5 w-3.5" strokeWidth={2.6} />
              ) : (
                <ExternalLink className="h-3.5 w-3.5" />
              )}{" "}
              {action}
            </span>
          )}
        </div>
      )}
    </div>
  );
  return onTap ? (
    <button
      type="button"
      onClick={onTap}
      className="block w-full"
      aria-label={`Ad: ${ad.title}`}
    >
      {body}
    </button>
  ) : (
    body
  );
}
