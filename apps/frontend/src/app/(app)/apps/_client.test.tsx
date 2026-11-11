import { beforeEach, describe, expect, it, vi } from "vitest";
import { screen, waitFor, within } from "@testing-library/react";
import { renderWithQuery } from "@/test/render";
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

let sites: unknown[] = [];
let shops: unknown[] = [];

function serve(results: unknown[], available: unknown[] = []) {
  get.mockImplementation(async (path: string) => {
    if (path === "/service-apps/") return { results, available };
    if (path === "/organizations/") return [ORG];
    if (path === "/organizations/o1/sites/") return sites;
    if (path === "/organizations/o1/movie-shops/") return shops;
    throw new Error(`unexpected GET ${path}`);
  });
}

beforeEach(() => {
  get.mockReset();
  post.mockReset();
  sites = [];
  shops = [];
});

describe("Apps", () => {
  it("shows the configured shop name, never a hard-coded one, with its live status", async () => {
    serve([installed()]);
    renderWithQuery(<AppsClient />);
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
    renderWithQuery(<AppsClient />);
    await userEvent.click(await screen.findByRole("button", { name: /Open/ }));
    expect(post).toHaveBeenCalledWith("/service-apps/a1/launch/");
    await waitFor(() => expect(assign).toHaveBeenCalledWith("/apps/spare-parts/"));
  });

  it("a stopped application cannot be opened and says what to do", async () => {
    serve([installed({ health: { state: "stopped", reachable: false, checked_at: "" } })]);
    renderWithQuery(<AppsClient />);
    const open = await screen.findByRole("button", { name: /Open/ });
    expect(open).toBeDisabled();
    expect(screen.getByText(/Control Center/)).toBeInTheDocument();
  });

  it("explains a refused Open instead of failing silently", async () => {
    serve([installed()]);
    post.mockRejectedValue(new ApiError(403, { detail: "no" }));
    renderWithQuery(<AppsClient />);
    await userEvent.click(await screen.findByRole("button", { name: /Open/ }));
    expect(await screen.findByText(/don't have access/)).toBeInTheDocument();
  });

  it("installs an available application with the shop name the owner types", async () => {
    serve([], [
      { deployment: "spare-parts", app_type: "spare_parts", product_name: "Spare Parts", description: "Parts shop.", organizations: ["o1"] },
    ]);
    post.mockResolvedValue({});
    renderWithQuery(<AppsClient />);
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

describe("Apps: uploaded apps", () => {
  function site(overrides: Record<string, unknown> = {}) {
    return {
      id: "s1", organization: "o1", name: "Price checker", slug: "prices", status: "active", single_page_app: false,
      hostname: null, internet_hostname: null, lan_address: "", kind: "node", runtime_state: "running", runtime_log: "",
      application: null, path: "/prices/", public_port: 8445, created_at: "", updated_at: "",
      active_version: { id: "v1", number: 3, original_filename: "prices.zip", file_count: 4, total_bytes: 900, notes: "",
        uploaded_by_email: "", created_at: "" },
      ...overrides,
    };
  }

  it("shows an uploaded Node.js app beside the installed ones, with its state, version and address", async () => {
    sites = [site()];
    serve([installed()]);
    renderWithQuery(<AppsClient />);
    expect(await screen.findByRole("heading", { name: "Your uploaded apps" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Price checker" })).toBeInTheDocument();
    expect(screen.getByText("Node.js app")).toBeInTheDocument();
    expect(screen.getByText(/Version 3 · prices\.zip/)).toBeInTheDocument();
    const open = screen.getAllByRole("link", { name: /Open/ }).find((l) => l.getAttribute("href")?.includes("8445"));
    expect(open).toHaveAttribute("href", "https://localhost:8445/prices/");
    expect(screen.getByRole("link", { name: /Manage/ })).toHaveAttribute("href", "/orgs/o1/sites");
  });

  it("offers no Open for an app that is offline or failed", async () => {
    sites = [site({ status: "disabled" }), site({ id: "s2", name: "Broken", runtime_state: "failed" })];
    serve([]);
    renderWithQuery(<AppsClient />);
    expect(await screen.findByText("Offline")).toBeInTheDocument();
    expect(screen.getByText("Failed to start")).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /Open/ })).not.toBeInTheDocument();
  });

  it("shows no uploaded section where the person may not read websites", async () => {
    serve([installed()]);
    get.mockImplementation(async (path: string) => {
      if (path === "/service-apps/") return { results: [installed()], available: [] };
      if (path === "/organizations/") return [ORG];
      throw new ApiError(403, { detail: "no" });
    });
    renderWithQuery(<AppsClient />);
    expect(await screen.findByRole("heading", { name: "Harbour Motors" })).toBeInTheDocument();
    await waitFor(() => expect(get).toHaveBeenCalledWith("/organizations/o1/sites/"));
    expect(screen.queryByRole("heading", { name: "Your uploaded apps" })).not.toBeInTheDocument();
  });

  it("shows each movie shop as an installed app and offers the Movie Shop to install", async () => {
    shops = [
      {
        id: "m1",
        organization: "o1",
        project: "p1",
        name: "Lamek Movies",
        default_price: 40,
        category_prices: {},
        agent_seen_at: null,
        agent: { computer: "", version: "" },
        titles: 12,
        can_manage: true,
        can_sell: true,
        created_at: "",
      },
    ];
    serve([]);
    renderWithQuery(<AppsClient />);
    expect(await screen.findByRole("heading", { name: "Lamek Movies" })).toBeInTheDocument();
    expect(screen.getByText("Media agent off")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Open/ })).toHaveAttribute("href", "/movies/m1");
    expect(screen.getByRole("button", { name: "Install Movie Shop" })).toBeEnabled();
  });
});
