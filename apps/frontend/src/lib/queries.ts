import { queryOptions, type QueryClient } from "@tanstack/react-query";
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

/** What a page reads first, so pointing at (or focusing) its link can start the request before the click. Data
 * still fresh in the cache is not asked for again. */
const ROUTE_DATA: Record<string, (client: QueryClient) => Promise<void>[]> = {
  "/dashboard": (c) => [c.prefetchQuery(organizationsQuery), c.prefetchQuery(serviceAppsQuery)],
  "/apps": (c) => [c.prefetchQuery(serviceAppsQuery), c.prefetchQuery(organizationsQuery)],
  "/orgs": (c) => [c.prefetchQuery(organizationsQuery)],
};

export function prefetchRoute(client: QueryClient, href: string): void {
  ROUTE_DATA[href]?.(client);
}
