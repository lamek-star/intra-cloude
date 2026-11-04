import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { renderWithQuery } from "@/test/render";

const { get } = vi.hoisted(() => ({ get: vi.fn() }));
vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return { ...actual, api: { ...actual.api, get } };
});
vi.mock("@/lib/auth-context", () => ({ useAuth: () => ({ user: { email: "owner@test.local", first_name: "" } }) }));

import DashboardPage from "./page";
import { PageLoading } from "@/components/ui";

const ORG = { id: "o1", name: "Test Shop", slug: "ts", external_sharing_enabled: false, created_at: "", created_by: "" };

function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((r) => (resolve = r));
  return { promise, resolve };
}

beforeEach(() => {
  get.mockReset();
  vi.stubGlobal(
    "fetch",
    vi.fn(async () => new Response(JSON.stringify({ checks: { database: "ok" } }), { status: 200 })),
  );
});
afterEach(() => vi.unstubAllGlobals());

describe("Dashboard loading", () => {
  it("asks for the installed apps and the audit log without waiting on slower answers", async () => {
    const orgs = deferred<unknown>();
    const workspaces = deferred<unknown>();
    get.mockImplementation((path: string) => {
      if (path === "/organizations/") return orgs.promise;
      if (path === "/organizations/o1/workspaces/") return workspaces.promise;
      if (path === "/service-apps/") return Promise.resolve({ results: [], available: [] });
      if (path.startsWith("/organizations/o1/audit/")) return Promise.resolve({ count: 0, results: [] });
      throw new Error(`unexpected GET ${path}`);
    });
    renderWithQuery(<DashboardPage />);

    // Installed apps go out with the organizations, not after them.
    await waitFor(() => expect(get).toHaveBeenCalledWith("/service-apps/"));
    orgs.resolve([ORG]);
    // The audit log goes out alongside the workspace counts, while they are still unanswered.
    await waitFor(() => expect(get).toHaveBeenCalledWith("/organizations/o1/audit/?limit=8"));
    workspaces.resolve([{ id: "w1" }]);
    expect(await screen.findByRole("heading", { name: /Welcome/ })).toBeInTheDocument();
  });
});

describe("PageLoading", () => {
  it("is a page-shaped placeholder announced to screen readers, not a bare spinner", () => {
    render(<PageLoading />);
    const status = screen.getByRole("status");
    expect(status).toHaveTextContent("Loading…");
    expect(status.querySelector("svg.animate-spin")).toBeNull();
  });
});
