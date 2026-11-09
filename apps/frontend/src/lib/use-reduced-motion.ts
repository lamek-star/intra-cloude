import { useSyncExternalStore } from "react";

const QUERY = "(prefers-reduced-motion: reduce)";

function subscribe(onChange: () => void) {
  const q = window.matchMedia(QUERY);
  q.addEventListener("change", onChange);
  return () => q.removeEventListener("change", onChange);
}

/** Whether the person asked their system for less motion (Windows: Settings > Accessibility > Visual effects). */
export function usePrefersReducedMotion(): boolean {
  return useSyncExternalStore(
    subscribe,
    () => window.matchMedia(QUERY).matches,
    () => false,
  );
}
