"use client";

import { useEffect } from "react";
import { rememberTourRequest, tourRequestFrom } from "@/lib/tour";

/** Keeps Setup's "show me a quick tour" wish (`?tour=1` / `?tour=off`) until the person is signed in (lib/tour.ts). */
export function TourRequestCapture() {
  useEffect(() => {
    rememberTourRequest(tourRequestFrom(window.location.search));
  }, []);
  return null;
}
