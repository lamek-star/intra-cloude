"use client";

import { useEffect, useState, type FormEvent } from "react";
import {
  api,
  ApiError,
  type AuditEvent,
  type Organization,
  type Paginated,
} from "@/lib/api";
import {
  Badge,
  Button,
  Card,
  EmptyState,
  ErrorBanner,
  Input,
  Label,
  PageHeader,
  PageLoading,
  Select,
  Spinner,
  Table,
  Td,
  Th,
  THead,
  TRow,
} from "@/components/ui";

const PAGE_SIZE = 50;

type Filters = {
  resource_type: string;
  action: string;
  result: "" | "success" | "denied" | "error";
};

const EMPTY_FILTERS: Filters = { resource_type: "", action: "", result: "" };

export default function AuditLogClient({ orgId }: { orgId: string }) {
  const [org, setOrg] = useState<Organization | null>(null);
  const [events, setEvents] = useState<AuditEvent[] | null>(null);
  const [count, setCount] = useState(0);
  const [offset, setOffset] = useState(0);
  const [filters, setFilters] = useState<Filters>(EMPTY_FILTERS);
  const [pendingFilters, setPendingFilters] = useState<Filters>(EMPTY_FILTERS);
  const [error, setError] = useState<string | null>(null);
  const [forbidden, setForbidden] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get<Organization>(`/organizations/${orgId}/`).then(setOrg).catch(() => {});
  }, [orgId]);

  async function load(currentOffset: number, currentFilters: Filters) {
    setLoading(true);
    setError(null);
    setForbidden(false);
    const params = new URLSearchParams();
    params.set("limit", String(PAGE_SIZE));
    params.set("offset", String(currentOffset));
    if (currentFilters.resource_type) params.set("resource_type", currentFilters.resource_type);
    if (currentFilters.action) params.set("action", currentFilters.action);
    if (currentFilters.result) params.set("result", currentFilters.result);
    try {
      const page = await api.get<Paginated<AuditEvent>>(
        `/organizations/${orgId}/audit/?${params.toString()}`,
      );
      setEvents(page.results);
      setCount(page.count);
    } catch (err) {
      if (err instanceof ApiError && err.status === 403) {
        setForbidden(true);
        setEvents([]);
      } else {
        setError(err instanceof ApiError ? err.message : "Failed to load the audit log.");
      }
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    // One-shot fetch-on-mount/param-change, not a state-sync loop.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    load(0, EMPTY_FILTERS);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [orgId]);

  function applyFilters(e: FormEvent) {
    e.preventDefault();
    setFilters(pendingFilters);
    setOffset(0);
    load(0, pendingFilters);
  }

  function clearFilters() {
    setPendingFilters(EMPTY_FILTERS);
    setFilters(EMPTY_FILTERS);
    setOffset(0);
    load(0, EMPTY_FILTERS);
  }

  function goTo(newOffset: number) {
    setOffset(newOffset);
    load(newOffset, filters);
  }

  if (events === null && !error && !forbidden) return <PageLoading />;

  return (
    <div>
      <PageHeader
        title="Audit log"
        breadcrumbs={[
          { label: "Organizations", href: "/orgs" },
          ...(org ? [{ label: org.name, href: `/orgs/${orgId}` }] : []),
          { label: "Audit log" },
        ]}
        description="A record of security-relevant actions taken in this organization."
      />

      {forbidden ? (
        <ErrorBanner message="You don't have permission to view this organization's audit log (requires audit.read)." />
      ) : (
        <>
          <Card className="mb-6">
            <form onSubmit={applyFilters} className="grid grid-cols-1 gap-3 sm:grid-cols-4">
              <div>
                <Label htmlFor="filter-resource-type">Resource type</Label>
                <Input
                  id="filter-resource-type"
                  placeholder="e.g. bucket, file, organization"
                  value={pendingFilters.resource_type}
                  onChange={(e) =>
                    setPendingFilters((f) => ({ ...f, resource_type: e.target.value }))
                  }
                />
              </div>
              <div>
                <Label htmlFor="filter-action">Action</Label>
                <Input
                  id="filter-action"
                  placeholder="e.g. file.upload"
                  value={pendingFilters.action}
                  onChange={(e) => setPendingFilters((f) => ({ ...f, action: e.target.value }))}
                />
              </div>
              <div>
                <Label htmlFor="filter-result">Result</Label>
                <Select
                  id="filter-result"
                  value={pendingFilters.result}
                  onChange={(e) =>
                    setPendingFilters((f) => ({
                      ...f,
                      result: e.target.value as Filters["result"],
                    }))
                  }
                >
                  <option value="">Any</option>
                  <option value="success">Success</option>
                  <option value="denied">Denied</option>
                  <option value="error">Error</option>
                </Select>
              </div>
              <div className="flex items-end gap-2">
                <Button type="submit" size="sm">
                  Apply
                </Button>
                <Button type="button" variant="ghost" size="sm" onClick={clearFilters}>
                  Clear
                </Button>
              </div>
            </form>
          </Card>

          {error && (
            <div className="mb-4">
              <ErrorBanner message={error} />
            </div>
          )}

          {loading ? (
            <Card>
              <div className="flex items-center gap-2 text-sm text-slate-500">
                <Spinner className="h-4 w-4" /> Loading...
              </div>
            </Card>
          ) : events && events.length === 0 ? (
            <EmptyState
              title="No matching events"
              description="Try widening or clearing the filters above."
            />
          ) : (
            <>
              <Table>
                <THead>
                  <Th>Time</Th>
                  <Th>Action</Th>
                  <Th>Resource</Th>
                  <Th>Result</Th>
                  <Th>Request ID</Th>
                </THead>
                <tbody>
                  {events?.map((event) => (
                    <TRow key={event.id}>
                      <Td className="whitespace-nowrap text-slate-400">
                        {new Date(event.timestamp).toLocaleString()}
                      </Td>
                      <Td className="font-medium text-white">{event.action}</Td>
                      <Td className="text-slate-400">
                        {event.resource_type}
                        {event.resource_id && (
                          <span className="text-slate-600"> · {event.resource_id.slice(0, 8)}</span>
                        )}
                      </Td>
                      <Td>
                        <Badge
                          tone={
                            event.result === "success"
                              ? "success"
                              : event.result === "denied"
                                ? "warning"
                                : "danger"
                          }
                        >
                          {event.result}
                        </Badge>
                      </Td>
                      <Td className="text-slate-600">{event.request_id.slice(0, 8)}</Td>
                    </TRow>
                  ))}
                </tbody>
              </Table>

              <div className="mt-4 flex items-center justify-between text-sm text-slate-500">
                <span>
                  {count === 0
                    ? "0 events"
                    : `${offset + 1}-${Math.min(offset + PAGE_SIZE, count)} of ${count}`}
                </span>
                <div className="flex gap-2">
                  <Button
                    variant="secondary"
                    size="sm"
                    disabled={offset === 0}
                    onClick={() => goTo(Math.max(0, offset - PAGE_SIZE))}
                  >
                    Previous
                  </Button>
                  <Button
                    variant="secondary"
                    size="sm"
                    disabled={offset + PAGE_SIZE >= count}
                    onClick={() => goTo(offset + PAGE_SIZE)}
                  >
                    Next
                  </Button>
                </div>
              </div>
            </>
          )}
        </>
      )}
    </div>
  );
}
