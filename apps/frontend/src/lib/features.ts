// Feature groups (backend system/features.py): which parts of IntraForge this installation shows. Chosen in Setup,
// changed by the Super Administrator on the Features page. The server refuses a switched-off group (403
// feature_disabled), so hiding here is for a clean screen, never the protection itself.

import { useQuery } from "@tanstack/react-query";

import { api, ApiError } from "./api";

export type FeatureGroup =
  "business_apps" | "pay_media" | "websites_developer" | "files_data";

export type Features = {
  groups: { key: FeatureGroup; label: string; enabled: boolean }[];
  app_types: Record<string, boolean>;
  updated_at: string | null;
  /** Who may create an account (ADR-0026). */
  registration: "closed" | "requests" | "open";
  registration_choices: { key: "closed" | "requests" | "open"; label: string }[];
  /** Only the Super Administrator may change the groups. */
  can_change: boolean;
};

/** What each group covers, in the shop owner's words (the Features page and Setup say the same). */
export const FEATURE_DESCRIPTIONS: Record<FeatureGroup, string> = {
  business_apps:
    "Spare Parts, Pharmacy and the business apps built in IntraForge (App templates).",
  pay_media:
    "IntraForge Pay (wallets, counters, the phone app) and the Movie Shop with its customer portal.",
  websites_developer:
    "Hosted websites, internet access, and the Developer section (applications, API keys, logs, sign-in for other software).",
  files_data:
    "Storage, databases and the data tools: import, analytics, dashboards and sharing.",
};

export const featuresApi = {
  get: () => api.get<Features>("/system/features/"),
  set: (enabled: FeatureGroup[]) =>
    api.patch<Features>("/system/features/", { enabled }),
  setRegistration: (registration: Features["registration"]) =>
    api.patch<Features>("/system/features/", { registration }),
};

export const featuresQueryKey = ["system", "features"] as const;

/**
 * `on(group)`: true while loading (the server still refuses what is off), so the screen never jumps from empty to
 * full on every page; false once the server says the group is off.
 */
export function useFeatures() {
  const query = useQuery({
    queryKey: featuresQueryKey,
    queryFn: featuresApi.get,
    staleTime: 60_000,
  });
  const enabled = new Set(
    query.data?.groups.filter((g) => g.enabled).map((g) => g.key),
  );
  return {
    data: query.data,
    loading: query.isLoading,
    on: (group: FeatureGroup) => !query.data || enabled.has(group),
  };
}

/** A request refused because its feature group is switched off. */
export function isFeatureDisabled(err: unknown): boolean {
  return err instanceof ApiError && err.code === "feature_disabled";
}

/** Resolve to `fallback` when the group is switched off; any other error still throws. */
export async function unlessDisabled<T>(
  request: Promise<T>,
  fallback: T,
): Promise<T> {
  try {
    return await request;
  } catch (err) {
    if (isFeatureDisabled(err)) return fallback;
    throw err;
  }
}
