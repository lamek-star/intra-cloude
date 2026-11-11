"use client";

import { useState } from "react";
import { Check, ExternalLink } from "lucide-react";

/** ToyoDIY's public parts cross-reference: the person types (pastes) a full part number there and sees the vehicles
 * it fits. IntraForge copies nothing from the site: it opens the page in the person's own browser with the number on
 * the clipboard. (The site does not allow automated collection, so there is no lookup behind the scenes.) */
export const TOYODIY_XREF_URL = "https://www.toyodiy.com/parts/xref";

/** The number as ToyoDIY's box expects it: letters and digits only, upper case (04465-0K290 -> 044650K290). */
export function toyoDiyNumber(number: string): string {
  return number.replace(/[^0-9A-Za-z]/g, "").toUpperCase();
}

/** Toyota/Lexus part numbers are 10 to 12 letters and digits; the cross-reference refuses anything else. */
export function looksLikeToyotaNumber(number: string): boolean {
  return /^[0-9A-Z]{10,12}$/.test(toyoDiyNumber(number));
}

export function ToyoDiyLookup({ number }: { number: string }) {
  const [copied, setCopied] = useState(false);
  if (!looksLikeToyotaNumber(number)) return null;
  const clean = toyoDiyNumber(number);
  return (
    <a
      href={TOYODIY_XREF_URL}
      target="_blank"
      rel="noopener noreferrer"
      title={`Opens ToyoDIY's cross-reference with ${clean} copied: paste it into the box to see the cars it fits`}
      aria-label={`Look up ${clean} on ToyoDIY (opens a new tab; the number is copied)`}
      className="ml-2 inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-xs font-medium text-brand-700 hover:bg-brand-50 hover:underline"
      onClick={() => {
        // Opening the page never waits on the clipboard; if copying is refused, the number is still in the tooltip.
        void navigator.clipboard?.writeText(clean).then(
          () => {
            setCopied(true);
            setTimeout(() => setCopied(false), 4000);
          },
          () => undefined,
        );
      }}
    >
      {copied ? <Check className="h-3.5 w-3.5" aria-hidden="true" /> : <ExternalLink className="h-3.5 w-3.5" aria-hidden="true" />}
      {copied ? "Copied, paste on ToyoDIY" : "ToyoDIY"}
    </a>
  );
}
