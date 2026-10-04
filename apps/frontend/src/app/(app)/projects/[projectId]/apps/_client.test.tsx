import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

const { get, post } = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn() }));
vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return { ...actual, api: { ...actual.api, get, post } };
});

import { ApiError } from "@/lib/api";
import AppGalleryClient from "./_client";

const PROJECT = { id: "p1", name: "Business", workspace: "w1" };

function app(overrides: Record<string, unknown> = {}) {
  return {
    key: "spare_parts",
    label: "Spare Parts",
    summary: "Sell and stock spare parts.",
    highlights: ["Parts and part numbers", "Inventory"],
    status: "partially_qualified",
    status_label: "Pilot preview",
    evidence: [],
    installed: [],
    ...overrides,
  };
}

function serve(catalog: () => unknown[]) {
  get.mockImplementation(async (path: string) => {
    if (path === "/projects/p1/") return PROJECT;
    if (path.startsWith("/built-in-apps/")) return { results: catalog() };
    throw new Error(`unexpected GET ${path}`);
  });
}

beforeEach(() => {
  get.mockReset();
  post.mockReset();
});

describe("application gallery", () => {
  it("says plainly that nothing is available when the catalog is empty", async () => {
    serve(() => []);
    render(<AppGalleryClient projectId="p1" />);
    expect(await screen.findByText("No applications are available yet")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Install" })).not.toBeInTheDocument();
  });

  it("shows a preview with its honest label and warning, never as production-ready", async () => {
    serve(() => [app()]);
    render(<AppGalleryClient projectId="p1" />);
    const card = await screen.findByRole("article", { name: "Spare Parts" });
    expect(within(card).getByText("Pilot preview")).toBeInTheDocument();
    expect(within(card).getByText(/has not completed production qualification/)).toBeInTheDocument();
    expect(within(card).queryByText("Ready for use")).not.toBeInTheDocument();
  });

  it("shows a qualified application as ready for use, with no preview warning", async () => {
    serve(() => [app({ status: "qualified", status_label: "Ready for use" })]);
    render(<AppGalleryClient projectId="p1" />);
    const card = await screen.findByRole("article", { name: "Spare Parts" });
    expect(within(card).getByText("Ready for use")).toBeInTheDocument();
    expect(within(card).queryByText(/qualification/)).not.toBeInTheDocument();
  });

  it("requires acknowledging a preview before it can be installed", async () => {
    serve(() => [app()]);
    const user = userEvent.setup();
    render(<AppGalleryClient projectId="p1" />);
    await user.click(await screen.findByRole("button", { name: "Install" }));
    const dialog = screen.getByRole("dialog", { name: "Install Spare Parts" });
    const install = within(dialog).getByRole("button", { name: "Install" });
    expect(install).toBeDisabled();
    await user.click(within(dialog).getByRole("checkbox", { name: "I understand this is a preview" }));
    expect(install).toBeEnabled();
  });

  it("installs, shows progress and success, and links to Open application", async () => {
    let installed: unknown[] = [];
    serve(() => [app({ installed })]);
    post.mockImplementation(async (path: string) => {
      if (path === "/projects/p1/built-in-apps/spare_parts/install/") {
        installed = [{ id: "i1", label: "My Shop", runtime: "ready" }];
        return { id: "i1" };
      }
      throw new Error(`unexpected POST ${path}`);
    });
    const user = userEvent.setup();
    render(<AppGalleryClient projectId="p1" />);
    await user.click(await screen.findByRole("button", { name: "Install" }));
    const dialog = screen.getByRole("dialog");
    await user.clear(within(dialog).getByLabelText("Application name"));
    await user.type(within(dialog).getByLabelText("Application name"), "My Shop");
    await user.click(within(dialog).getByRole("checkbox"));
    await user.click(within(dialog).getByRole("button", { name: "Install" }));
    await waitFor(() =>
      expect(post).toHaveBeenCalledWith("/projects/p1/built-in-apps/spare_parts/install/", { label: "My Shop" }),
    );
    expect(await within(dialog).findByText(/Spare Parts is ready/)).toBeInTheDocument();
    expect(within(dialog).getByRole("link", { name: "Open application" })).toHaveAttribute("href", "/apps/i1");
  });

  it("finishes a stranded install with the safe retry instead of installing a second copy", async () => {
    let installed: unknown[] = [];
    serve(() => [app({ installed })]);
    post.mockImplementation(async (path: string) => {
      if (path === "/projects/p1/built-in-apps/spare_parts/install/") {
        installed = [{ id: "i9", label: "Spare Parts", runtime: "failed" }]; // created, then setup failed
        throw new ApiError(500, { error: { code: "install_failed", message: "The application could not be prepared." } });
      }
      if (path === "/app-instances/i9/built-in/retry/") {
        installed = [{ id: "i9", label: "Spare Parts", runtime: "ready" }];
        return { id: "i9" };
      }
      throw new Error(`unexpected POST ${path}`);
    });
    const user = userEvent.setup();
    render(<AppGalleryClient projectId="p1" />);
    await user.click(await screen.findByRole("button", { name: "Install" }));
    const dialog = screen.getByRole("dialog");
    await user.click(within(dialog).getByRole("checkbox"));
    await user.click(within(dialog).getByRole("button", { name: "Install" }));

    expect(await within(dialog).findByRole("alert")).toHaveTextContent("could not be prepared");
    expect(within(dialog).getByText(/created but not finished/)).toBeInTheDocument();
    await user.click(within(dialog).getByRole("button", { name: "Try again" }));

    expect(await within(dialog).findByText(/Spare Parts is ready/)).toBeInTheDocument();
    expect(post).toHaveBeenCalledWith("/app-instances/i9/built-in/retry/", {});
    expect(post.mock.calls.filter(([p]) => String(p).includes("/install/"))).toHaveLength(1); // never a second install
  });

  it("explains a permission failure plainly and says nothing was installed", async () => {
    serve(() => [app()]);
    post.mockRejectedValue(new ApiError(403, {}));
    const user = userEvent.setup();
    render(<AppGalleryClient projectId="p1" />);
    await user.click(await screen.findByRole("button", { name: "Install" }));
    const dialog = screen.getByRole("dialog");
    await user.click(within(dialog).getByRole("checkbox"));
    await user.click(within(dialog).getByRole("button", { name: "Install" }));
    expect(await within(dialog).findByRole("alert")).toHaveTextContent("don't have permission");
    expect(within(dialog).getByText("Nothing was installed.")).toBeInTheDocument();
  });

  it("offers Open for a ready installed app and Finish setup for an incomplete one", async () => {
    serve(() => [
      app({
        installed: [
          { id: "ok", label: "Main Shop", runtime: "ready" },
          { id: "half", label: "Second Shop", runtime: "failed" },
        ],
      }),
    ]);
    const user = userEvent.setup();
    post.mockResolvedValue({ id: "half" });
    render(<AppGalleryClient projectId="p1" />);
    const card = await screen.findByRole("article", { name: "Spare Parts" });
    expect(within(card).getByRole("link", { name: "Open" })).toHaveAttribute("href", "/apps/ok");
    await user.click(within(card).getByRole("button", { name: "Finish setup" }));
    await waitFor(() => expect(post).toHaveBeenCalledWith("/app-instances/half/built-in/retry/", {}));
    expect(within(card).getByRole("button", { name: "Install another copy" })).toBeInTheDocument();
  });
});
