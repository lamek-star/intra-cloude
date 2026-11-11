import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClientProvider, useQuery } from "@tanstack/react-query";

const { get, post } = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn() }));
vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return { ...actual, ensureCsrfCookie: vi.fn(async () => {}), api: { ...actual.api, get, post } };
});

import { ApiError } from "@/lib/api";
import { AuthProvider, useAuth } from "@/lib/auth-context";
import { makeQueryClient } from "@/lib/query";
import { organizationsQuery, prefetchRoute, serviceAppsQuery } from "@/lib/queries";

function Orgs() {
  const { data } = useQuery(organizationsQuery);
  return <p>{data ? data.map((o) => o.name).join(", ") : "loading"}</p>;
}

function SignInAsB() {
  const { login } = useAuth();
  return <button onClick={() => void login("b@test.local", "secret")}>Sign in as B</button>;
}

beforeEach(() => {
  get.mockReset();
  post.mockReset();
});

describe("page data cache", () => {
  it("shows a page seen before at once, without waiting for the server again", async () => {
    get.mockResolvedValue([{ id: "o1", name: "Test Shop" }]);
    const client = makeQueryClient();
    const first = render(
      <QueryClientProvider client={client}>
        <Orgs />
      </QueryClientProvider>,
    );
    expect(await screen.findByText("Test Shop")).toBeInTheDocument();
    first.unmount();

    get.mockImplementation(() => new Promise(() => {})); // the server never answers this time
    render(
      <QueryClientProvider client={client}>
        <Orgs />
      </QueryClientProvider>,
    );
    expect(screen.getByText("Test Shop")).toBeInTheDocument();
  });

  it("preloads a page's data on hover, once while it is fresh, and nothing for other pages", async () => {
    get.mockImplementation(async (path: string) => (path === "/service-apps/" ? { results: [], available: [] } : []));
    const client = makeQueryClient();
    prefetchRoute(client, "/apps");
    await waitFor(() => expect(client.getQueryData(serviceAppsQuery.queryKey)).toBeDefined());
    expect(get.mock.calls.map((c) => c[0]).sort()).toEqual(["/organizations/", "/service-apps/"]);

    prefetchRoute(client, "/apps");
    prefetchRoute(client, "/orgs");
    prefetchRoute(client, "/somewhere-else");
    await new Promise((r) => setTimeout(r, 20));
    expect(get).toHaveBeenCalledTimes(2);
  });

  it("never retries a refusal", async () => {
    get.mockRejectedValue(new ApiError(403, {}));
    const client = makeQueryClient();
    await expect(client.fetchQuery(organizationsQuery)).rejects.toBeInstanceOf(ApiError);
    expect(get).toHaveBeenCalledTimes(1);
  });

  it("is emptied when a different person signs in", async () => {
    get.mockImplementation(async (path: string) => {
      if (path === "/auth/me/") return { id: "u1", email: "a@test.local" };
      return [{ id: "o1", name: "Shop of person A" }];
    });
    const client = makeQueryClient();
    render(
      <QueryClientProvider client={client}>
        <AuthProvider>
          <SignInAsB />
          <Orgs />
        </AuthProvider>
      </QueryClientProvider>,
    );
    expect(await screen.findByText("Shop of person A")).toBeInTheDocument();

    post.mockResolvedValue({ id: "u2", email: "b@test.local" });
    await userEvent.click(screen.getByRole("button", { name: "Sign in as B" }));
    await waitFor(() => expect(client.getQueryData(organizationsQuery.queryKey)).toBeUndefined());
  });
});
