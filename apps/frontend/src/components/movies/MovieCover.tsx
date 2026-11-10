"use client";

import { useState } from "react";
import { Coins } from "lucide-react";
import { drawnCover, movies, type MovieTitle } from "@/lib/movies";

function Motif({ motif, accent }: { motif: ReturnType<typeof drawnCover>["motif"]; accent: string }) {
  switch (motif) {
    case "sun":
      return (
        <>
          <circle cx="100" cy="128" r="46" fill={accent} opacity=".9" />
          <path d="M0 190 Q60 150 100 175 T200 160 V300 H0Z" fill="#000" opacity=".55" />
          <path d="M0 215 Q70 180 120 205 T200 195 V300 H0Z" fill="#000" opacity=".7" />
        </>
      );
    case "mountain":
      return (
        <>
          <path d="M0 230 L60 130 L95 175 L140 95 L200 200 V300 H0Z" fill="#000" opacity=".55" />
          <circle cx="160" cy="55" r="16" fill={accent} opacity=".8" />
        </>
      );
    case "wave":
      return (
        <>
          <path d="M0 170 Q50 140 100 170 T200 170 V300 H0Z" fill={accent} opacity=".45" />
          <path d="M0 200 Q50 170 100 200 T200 200 V300 H0Z" fill="#000" opacity=".45" />
        </>
      );
    case "city":
      return (
        <>
          {[0, 26, 48, 80, 104, 130, 158, 178].map((x, i) => (
            <rect key={x} x={x} y={120 + ((i * 37) % 60)} width={22 + (i % 3) * 6} height="200" fill="#000" opacity=".6" />
          ))}
          {[30, 60, 95, 140, 170].map((x, i) => (
            <rect key={x} x={x} y={150 + i * 9} width="4" height="4" fill={accent} />
          ))}
        </>
      );
    case "moon":
      return (
        <>
          <circle cx="130" cy="80" r="34" fill={accent} opacity=".9" />
          <circle cx="144" cy="72" r="30" fill="#000" opacity=".35" />
          <path d="M0 220 Q100 180 200 225 V300 H0Z" fill="#000" opacity=".6" />
        </>
      );
    case "road":
      return (
        <>
          <path d="M0 300 L95 150 H105 L200 300Z" fill="#000" opacity=".45" />
          <path d="M90 300 L98 150 H102 L110 300Z" fill={accent} opacity=".7" />
        </>
      );
    default:
      return (
        <>
          <circle cx="100" cy="120" r="70" fill="none" stroke={accent} strokeWidth="10" opacity=".8" />
          <circle cx="100" cy="120" r="44" fill={accent} opacity=".25" />
        </>
      );
  }
}

/** A title's cover: the picture found beside it, or a drawn one, with its price and the title over a dark fade. */
type CoverTitle = Pick<MovieTitle, "id" | "title" | "has_cover" | "price" | "kind" | "episodes">;

/** A title's cover: the shop's picture when there is one (from `src`, or the owner's cover address), else a cover
 * drawn from the title. */
export function MovieCover({ title, showPrice = true, className = "", src }: { title: CoverTitle; showPrice?: boolean; className?: string; src?: string }) {
  const [broken, setBroken] = useState(false);
  const drawn = drawnCover(title.title);
  const picture = title.has_cover && !broken;
  return (
    <div
      className={`relative aspect-[2/3] overflow-hidden rounded-xl shadow-[0_10px_24px_-12px_rgba(0,0,0,.8),inset_0_0_0_1px_rgba(255,255,255,.06)] ${className}`}
      style={{ background: `linear-gradient(165deg, ${drawn.from}, ${drawn.to})` }}
    >
      {picture ? (
        // eslint-disable-next-line @next/next/no-img-element -- the shop's own cover, served by IntraForge
        <img src={src ?? movies.coverUrl(title.id)} alt="" loading="lazy" onError={() => setBroken(true)} className="absolute inset-0 h-full w-full object-cover" />
      ) : (
        <svg viewBox="0 0 200 300" preserveAspectRatio="xMidYMid slice" className="absolute inset-0 h-full w-full" aria-hidden="true">
          <Motif motif={drawn.motif} accent={drawn.accent} />
        </svg>
      )}
      <div className="absolute inset-0 bg-gradient-to-b from-transparent from-45% to-black/75" />
      {showPrice && (
        <span className="absolute top-2 left-2 inline-flex items-center gap-1 rounded-full bg-amber-400 px-2 py-0.5 text-[11px] font-extrabold text-amber-950">
          <Coins className="h-3 w-3" strokeWidth={2.6} aria-hidden="true" />
          {title.price}
        </span>
      )}
      {title.kind === "series" && (
        <span className="absolute top-2 right-2 rounded border border-white/25 bg-black/55 px-1.5 py-0.5 text-[10px] font-extrabold tracking-wide text-white backdrop-blur-sm">
          {title.episodes} EP
        </span>
      )}
      {!picture && (
        <div
          className="absolute inset-x-2.5 bottom-2.5 font-semibold tracking-wide text-white uppercase [text-shadow:0_2px_8px_rgba(0,0,0,.6)]"
          style={{ fontFamily: "var(--font-display), Impact, 'Arial Narrow', sans-serif", fontSize: title.title.length > 14 ? 15 : 18, lineHeight: 1.05 }}
        >
          {title.title}
        </div>
      )}
    </div>
  );
}
