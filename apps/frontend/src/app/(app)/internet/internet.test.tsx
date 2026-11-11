import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

const { get, post } = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn() }));
vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return { ...actual, ensureCsrfCookie: vi.fn(async () => {}), api: { ...actual.api, get, post } };
});
vi.mock("@/components/ConfirmProvider", () => ({ useConfirm: () => async () => true }));

import InternetPage from "./page";

function gate(autoDomain: string) {
  return {
    enabled: true,
    can_manage: true,
    changed_at: null,
    auto_domain: autoDomain,
    tunnel: { state: "running" },
    published: autoDomain
      ? [{ site: "s1", name: "Price list", organization: "Test Shop", internet_hostname: `price-list.${autoDomain}`, published_at: null, auto: true }]
      : [],
    publishable: [],
  };
}

beforeEach(() => {
  get.mockReset();
  post.mockReset();
});

describe("Auto-publish", () => {
  it("switches on for a domain with the Super Administrator's password", async () => {
    get.mockResolvedValue(gate(""));
    post.mockResolvedValue(gate("harmongt.uk"));
    render(<InternetPage />);
    await userEvent.type(await screen.findByLabelText("Your domain"), " HarmonGT.uk ");
    await userEvent.type(screen.getByLabelText("Your IntraForge password"), "secret");
    get.mockResolvedValue(gate("harmongt.uk"));
    await userEvent.click(screen.getByRole("button", { name: "Switch auto-publish on" }));
    expect(post).toHaveBeenCalledWith("/internet-gateway/auto-publish/", { domain: "harmongt.uk", password: "secret" });
    expect(await screen.findByText("On: *.harmongt.uk")).toBeInTheDocument();
    expect(screen.getByText("Automatic")).toBeInTheDocument();
  });

  it("switches off with an empty domain", async () => {
    get.mockResolvedValue(gate("harmongt.uk"));
    post.mockResolvedValue(gate(""));
    render(<InternetPage />);
    await userEvent.type(await screen.findByLabelText("Your IntraForge password"), "secret");
    await userEvent.click(screen.getByRole("button", { name: "Switch auto-publish off" }));
    await waitFor(() => expect(post).toHaveBeenCalledWith("/internet-gateway/auto-publish/", { domain: "", password: "secret" }));
  });
});
