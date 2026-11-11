import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

const { get, search, login, signInWithPasskey, push } = vi.hoisted(() => ({
  get: vi.fn(),
  search: { next: null as string | null },
  login: vi.fn(),
  signInWithPasskey: vi.fn(),
  push: vi.fn(),
}));
vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return { ...actual, api: { ...actual.api, get } };
});
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push, replace: vi.fn() }),
  useSearchParams: () => new URLSearchParams(search.next ? { next: search.next } : {}),
}));
vi.mock("@/lib/auth-context", () => ({
  useAuth: () => ({ login, verifyMfa: vi.fn(), signInWithPasskey }),
  isMfaRequired: () => false,
}));

import { ApiError } from "@/lib/api";
import LoginPage from "./page";

const APP = "3f2c1a9e-8b7d-4c6e-9a1b-2d3e4f5a6b7c";

describe("sign-in page", () => {
  beforeEach(() => {
    get.mockReset();
    login.mockReset();
    signInWithPasskey.mockReset();
    push.mockReset();
    search.next = null;
    // jsdom has no WebAuthn; most tests give the page one.
    vi.stubGlobal("PublicKeyCredential", function PublicKeyCredential() {});
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

  it("signs in with a passkey from the phone and goes on to the dashboard", async () => {
    signInWithPasskey.mockResolvedValue({ id: "u1" });
    render(<LoginPage />);
    await userEvent.click(await screen.findByRole("button", { name: "Sign in with a passkey" }));
    expect(signInWithPasskey).toHaveBeenCalledWith("phone");
    await waitFor(() => expect(push).toHaveBeenCalledWith("/dashboard"));
  });

  it("says so when the person closes the passkey dialog", async () => {
    signInWithPasskey.mockRejectedValue(new DOMException("closed", "NotAllowedError"));
    render(<LoginPage />);
    await userEvent.click(await screen.findByRole("button", { name: "Sign in with a passkey" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("closed or timed out");
  });

  it("points a passkey-only account to the passkey button", async () => {
    login.mockRejectedValue(new ApiError(403, { detail: "This account signs in with a passkey only.", passkey_only: true }));
    render(<LoginPage />);
    await userEvent.type(await screen.findByLabelText("Email"), "owner@shop.test");
    await userEvent.type(screen.getByLabelText("Password"), "a-strong-passw0rd!");
    await userEvent.click(screen.getByRole("button", { name: "Sign in" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Use the passkey button below");
  });

  it("offers no passkey button where the browser has none", async () => {
    vi.unstubAllGlobals();
    render(<LoginPage />);
    await screen.findByRole("heading", { name: "IntraForge" });
    expect(screen.queryByRole("button", { name: "Sign in with a passkey" })).not.toBeInTheDocument();
  });
});
