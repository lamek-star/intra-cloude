"use client";

import * as React from "react";

// Next.js bundles a React that has <ViewTransition> (no flag needed since Next 16.4); the plain React
// the unit tests run on does not, so it falls back to rendering the page as it is.
const ViewTransition =
  (React as unknown as { ViewTransition?: React.ComponentType<{ children: React.ReactNode }> }).ViewTransition ??
  React.Fragment;

/** A short cross-fade between pages (globals.css "View transitions"): the sidebar and header stay still, only
 * the page area changes. Pages carry no transitions of their own, so this one boundary is enough. Browsers
 * without view transitions, and people who ask for reduced motion, get the change at once. */
export function PageTransition({ children }: { children: React.ReactNode }) {
  return <ViewTransition>{children}</ViewTransition>;
}
