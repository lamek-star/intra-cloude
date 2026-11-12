import { api } from "./api";

export type HealthAlert = { check: string; label: string; detail: string; opened_at: string; closed_at: string | null };
export type HealthSummary = {
  latest: { at: string | null; checks: { check: string; label: string; ok: boolean }[] };
  hours: { check: string; label: string; hours: { hour: string; ok: number; failed: number }[] }[];
  alerts: HealthAlert[];
  open_alerts: number;
};

/** This installation's health history and alerts (the Super Administrator only; others get a 403). */
export const healthSummary = () => api.get<HealthSummary>("/system/health/");
