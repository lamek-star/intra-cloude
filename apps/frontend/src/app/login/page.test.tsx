import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";

const { get, search } = vi.hoisted(() => ({ get: vi.fn(), search: { next: null as string | null } }));
vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return { ...actual, api: { ...actual.api, get } };
});
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
  useSearchParams: () => new URLSearchParams(search.next ? { next: search.next } : {}),
}));
vi.mock("@/lib/auth-context", () => ({
  useAuth: () => ({ login: vi.fn(), verifyMfa: vi.fn() }),
  isMfaRequired: () => false,
}));

import { ApiError } from "@/lib/api";
import LoginPage from "./page";

const APP = "3f2c1a9e-8b7d-4c6e-9a1b-2d3e4f5a6b7c";

describe("sign-in page", () => {
  beforeEach(() => {
    get.mockReset();
    search.next = null;
  });

  it("is the ordinary IntraForge sign-in without an application", async () => {
    render(<LoginPage />);
    expect(await screen.findByRole("heading", { name: "IntraForge" })).toBeInTheDocument();
    expect(get).not.toHaveBeenCalled();
  });

  it("shows the application's own sign-in when an application sent the person here", async () => {
    search.next = `/service-apps/${APP}/open`;
    get.mockResolvedValue({ product_name: "Spare Parts", display_name: "Micheal Spare Part LLC" });
    render(<LoginPage />);
    expect(await screen.findByRole("heading", { name: "Spare Parts" })).toBeInTheDocument();
    expect(screen.getByText("Micheal Spare Part LLC")).toBeInTheDocument();
    expect(screen.getByText("Sign in with your staff account")).toBeInTheDocument();
    expect(get).toHaveBeenCalledWith(`/service-apps/${APP}/sign-in/`);
  });

  it("falls back to the ordinary sign-in when the application is unknown", async () => {
    search.next = `/service-apps/${APP}/open`;
    get.mockRejectedValue(new ApiError(404, {}));
    render(<LoginPage />);
    await waitFor(() => expect(get).toHaveBeenCalled());
    expect(screen.getByRole("heading", { name: "IntraForge" })).toBeInTheDocument();
  });

  it("never asks for branding for other return paths", async () => {
    for (const next of ["/dashboard", `//evil.example/service-apps/${APP}/open`, `/service-apps/${APP}/settings`]) {
      search.next = next;
      const { unmount } = render(<LoginPage />);
      await screen.findByRole("heading", { name: "IntraForge" });
      unmount();
    }
    expect(get).not.toHaveBeenCalled();
  });
});
