/**
 * When the welcome tour shows: once per person on this browser, the first time they reach the app. Setup's last screen opens
 * IntraForge with `?tour=1` ("Show me a quick tour" ticked) or `?tour=off` (unticked); that wish is kept on this browser until
 * the person is signed in, because the address they land on is the sign-in or registration page, not the app.
 *
 * Browser storage only: whether someone has seen the tour is a convenience, not data anyone else needs.
 */
export const TOUR_REQUEST_KEY = "intraforge.tour.request";
export const tourSeenKey = (userId: string) => `intraforge.tour.v1.seen.${userId}`;

export type TourRequest = "show" | "off" | null;

/** Setup's wish in a query string (`?tour=1` / `?tour=off`), or null when there is none. */
export function tourRequestFrom(search: string): TourRequest {
  const value = new URLSearchParams(search).get("tour");
  if (value === "1" || value === "show") return "show";
  if (value === "off" || value === "0") return "off";
  return null;
}

/** Whether to open the tour now. An explicit "show" opens it even for someone who has seen it (a fresh installation). */
export function shouldShowTour(seen: boolean, request: TourRequest): boolean {
  if (request === "show") return true;
  if (request === "off") return false;
  return !seen;
}

function storage(): Storage | null {
  try {
    return typeof window === "undefined" ? null : window.localStorage;
  } catch {
    return null;
  }
}

export function rememberTourRequest(request: TourRequest) {
  if (!request) return;
  try {
    storage()?.setItem(TOUR_REQUEST_KEY, request);
  } catch {
    /* private window or blocked storage: the tour simply follows the default */
  }
}

export function readTourState(userId: string): { seen: boolean; request: TourRequest } {
  const s = storage();
  try {
    const request = s?.getItem(TOUR_REQUEST_KEY);
    return {
      seen: s?.getItem(tourSeenKey(userId)) === "1",
      request: request === "show" || request === "off" ? request : null,
    };
  } catch {
    return { seen: true, request: null };
  }
}

/** The tour was shown (or declined): never again automatically for this person, and Setup's wish is used up. */
export function markTourSeen(userId: string) {
  const s = storage();
  try {
    s?.setItem(tourSeenKey(userId), "1");
    s?.removeItem(TOUR_REQUEST_KEY);
  } catch {
    /* see rememberTourRequest */
  }
}
