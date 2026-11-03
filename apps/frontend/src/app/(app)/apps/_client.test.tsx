import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

const { get, post } = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn() }));
vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return { ...actual, api: { ...actual.api, get, post } };
});

import { ApiError } from "@/lib/api";
import AppsClient from "./_client";

const ORG = { id: "o1", name: "Harbour Motors LLC", slug: "hm", external_sharing_enabled: false, created_at: "", created_by: "" };

function installed(overrides: Record<string, unknown> = {}) {
  return {
    id: "a1",
    app_type: "spare_parts",
    name: "Spare Parts",
    display_name: "Harbour Motors",
    organization: { id: "o1", name: ORG.name },
    version: "0.2.0",
    enabled: true,
    removed: false,
    launch: { path: "/apps/spare-parts/", requires: "spareparts.view" },
    required_capabilities: ["spareparts.view"],
    config: null,
    health: { state: "running", reachable: true, checked_at: "" },
    can_open: true,
    can_configure: false,
    can_manage: false,
    created_at: "",
    ...overrides,
  };
}

function serve(results: unknown[], available: unknown[] = []) {
  get.mockImplementation(async (path: string) => {
    if (path === "/service-apps/") return { results, available };
    if (path === "/organizations/") return [ORG];
    throw new Error(`unexpected GET ${path}`);
  });
}

beforeEach(() => {
  get.mockReset();
  post.mockReset();
});

describe("Apps", () => {
  it("shows the configured shop name, never a hard-coded one, with its live status", async () => {
    serve([installed()]);
    render(<AppsClient />);
    expect(await screen.findByRole("heading", { name: "Harbour Motors" })).toBeInTheDocument();
    expect(screen.getByText("Spare Parts")).toBeInTheDocument();
    expect(screen.getByText("Running")).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /Settings/ })).not.toBeInTheDocument();
  });

  it("Open asks IntraForge for an application session and goes to the launch path", async () => {
    serve([installed()]);
    const assign = vi.fn();
    Object.defineProperty(window, "location", { value: { assign }, writable: true });
    post.mockResolvedValue({ url: "/apps/spare-parts/" });
    render(<AppsClient />);
    await userEvent.click(await screen.findByRole("button", { name: /Open/ }));
    expect(post).toHaveBeenCalledWith("/service-apps/a1/launch/");
    await waitFor(() => expect(assign).toHaveBeenCalledWith("/apps/spare-parts/"));
  });

  it("a stopped application cannot be opened and says what to do", async () => {
    serve([installed({ health: { state: "stopped", reachable: false, checked_at: "" } })]);
    render(<AppsClient />);
    const open = await screen.findByRole("button", { name: /Open/ });
    expect(open).toBeDisabled();
    expect(screen.getByText(/Control Center/)).toBeInTheDocument();
  });

  it("explains a refused Open instead of failing silently", async () => {
    serve([installed()]);
    post.mockRejectedValue(new ApiError(403, { detail: "no" }));
    render(<AppsClient />);
    await userEvent.click(await screen.findByRole("button", { name: /Open/ }));
    expect(await screen.findByText(/don't have access/)).toBeInTheDocument();
  });

  it("installs an available application with the shop name the owner types", async () => {
    serve([], [
      { deployment: "spare-parts", app_type: "spare_parts", product_name: "Spare Parts", description: "Parts shop.", organizations: ["o1"] },
    ]);
    post.mockResolvedValue({});
    render(<AppsClient />);
    await userEvent.click(await screen.findByRole("button", { name: "Install" }));
    const dialog = await screen.findByRole("dialog");
    await userEvent.type(within(dialog).getByLabelText("Shop name"), "Harbour Motors");
    await userEvent.click(within(dialog).getByRole("button", { name: "Install" }));
    await waitFor(() =>
      expect(post).toHaveBeenCalledWith("/service-apps/", {
        deployment: "spare-parts",
        organization: "o1",
        display_name: "Harbour Motors",
        config: { currency: "AED" },
      }),
    );
  });
});
