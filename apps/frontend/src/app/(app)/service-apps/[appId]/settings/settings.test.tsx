import { beforeEach, describe, expect, it, vi } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderWithQuery } from "@/test/render";

const { get, patch } = vi.hoisted(() => ({ get: vi.fn(), patch: vi.fn() }));
vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return { ...actual, api: { ...actual.api, get, patch } };
});
vi.mock("next/navigation", () => ({ useRouter: () => ({ push: vi.fn() }) }));

import { ApiError } from "@/lib/api";
import SettingsClient from "./_client";

const APP = {
  id: "a1",
  app_type: "pharmacy",
  name: "Pharmacy",
  display_name: "Test Pharmacy",
  organization: { id: "o1", name: "Test Shop" },
  version: "1.4.0",
  enabled: true,
  removed: false,
  launch: { path: "/apps/pharmacy/", requires: "pharmacy.view" },
  required_capabilities: [],
  config: null,
  health: { state: "running", reachable: true, checked_at: "" },
  can_open: true,
  can_configure: false,
  can_manage: true,
  created_at: "",
};

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason: unknown) => void;
  const promise = new Promise<T>((res, rej) => {
    resolve = res;
    reject = rej;
  });
  return { promise, resolve, reject };
}

beforeEach(() => {
  get.mockReset();
  patch.mockReset();
  get.mockImplementation(async (path: string) => {
    if (path === "/service-apps/a1/") return APP;
    if (path === "/service-apps/") return { results: [APP], available: [] };
    throw new Error(`unexpected GET ${path}`);
  });
});

describe("app Settings availability", () => {
  it("switches on the click, before the server answers", async () => {
    const answer = deferred<unknown>();
    patch.mockReturnValue(answer.promise);
    renderWithQuery(<SettingsClient appId="a1" />);
    await userEvent.click(await screen.findByRole("button", { name: "Disable" }));

    expect(await screen.findByRole("button", { name: "Enable" })).toBeInTheDocument();
    expect(screen.getByText(/Nobody can open this application/)).toBeInTheDocument();
    expect(patch).toHaveBeenCalledWith("/service-apps/a1/", { enabled: false });
    answer.resolve({ ...APP, enabled: false, health: { state: "disabled", reachable: null, checked_at: "" } });
    expect(await screen.findByText("Disabled")).toBeInTheDocument();
  });

  it("goes back and says so when the server refuses", async () => {
    patch.mockRejectedValue(new ApiError(403, { error: { message: "Not allowed." } }));
    renderWithQuery(<SettingsClient appId="a1" />);
    await userEvent.click(await screen.findByRole("button", { name: "Disable" }));

    expect(await screen.findByText("The change was not saved.")).toBeInTheDocument();
    await waitFor(() => expect(screen.getByRole("button", { name: "Disable" })).toBeInTheDocument());
  });
});
