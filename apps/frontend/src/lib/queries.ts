import { queryOptions } from "@tanstack/react-query";
import { api, type Organization } from "@/lib/api";
import type { ServiceApp, ServiceAppList } from "@/lib/service-apps";

/** The cached reads shared by several pages. A change invalidates the key it affects (for example an app's
 * settings invalidate both that app and the Apps list). */
export const keys = {
  serviceApps: ["service-apps"] as const,
  serviceApp: (id: string) => ["service-apps", id] as const,
  organizations: ["organizations"] as const,
};

export const serviceAppsQuery = queryOptions({
  queryKey: keys.serviceApps,
  queryFn: () => api.get<ServiceAppList>("/service-apps/"),
});

export function serviceAppQuery(id: string) {
  return queryOptions({ queryKey: keys.serviceApp(id), queryFn: () => api.get<ServiceApp>(`/service-apps/${id}/`) });
}

export const organizationsQuery = queryOptions({
  queryKey: keys.organizations,
  queryFn: () => api.get<Organization[]>("/organizations/"),
});
