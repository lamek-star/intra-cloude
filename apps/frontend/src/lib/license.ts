// This installation's licence (ADR-0023): a 30-day trial, then read-only until a serial number is activated for this
// PC with the activation code the vendor sends back.

import { api } from "./api";

export type Licence = {
  state: "trial" | "active" | "expired" | "not_enforced";
  enforced: boolean;
  trial_days: number;
  trial_ends: string;
  days_left: number;
  clock_back: boolean;
  pc_code: string | null;
  serial: string | null;
  kind: "standard" | "master" | null;
  activated_at: string | null;
  can_activate: boolean;
};

export const licenceApi = {
  get: () => api.get<Licence>("/license/"),
  activate: (serial: string, activation_code: string) =>
    api.post<Licence>("/license/activate/", { serial, activation_code }),
};

/** The banner's words, or null when nothing needs saying. */
export function licenceNotice(
  l: Licence | undefined,
): { tone: "info" | "warning" | "danger"; text: string } | null {
  if (!l || !l.enforced || l.state === "active" || l.state === "not_enforced")
    return null;
  if (l.state === "expired")
    return {
      tone: "danger",
      text: l.clock_back
        ? "This PC's clock was set back, so IntraForge is read-only. Enter your serial number to continue."
        : "The trial has ended: IntraForge is read-only. Your data is safe; enter your serial number to continue.",
    };
  const days = `${l.days_left} ${l.days_left === 1 ? "day" : "days"}`;
  return {
    tone: l.days_left <= 7 ? "warning" : "info",
    text: `Trial: ${days} left. Enter your serial number any time.`,
  };
}
