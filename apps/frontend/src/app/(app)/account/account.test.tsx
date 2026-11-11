import { beforeEach, describe, expect, it, vi } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

const { get, post, refresh, user } = vi.hoisted(() => ({
  get: vi.fn(),
  post: vi.fn(),
  refresh: vi.fn(async () => {}),
  user: { current: { id: "u1", email: "owner@shop.test", first_name: "", last_name: "", date_joined: "", mfa_enabled: false } },
}));
vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return { ...actual, api: { ...actual.api, get, post }, ensureCsrfCookie: async () => {} };
});
vi.mock("@/lib/auth-context", () => ({ useAuth: () => ({ user: user.current, refresh }) }));

import { renderWithQuery } from "@/test/render";
import AccountClient, { groupKey } from "./_client";

const NO_PASSKEYS = { passkey_only: false, this_address: "localhost", passkeys: [] };

beforeEach(() => {
  post.mockReset();
  get.mockReset();
  get.mockResolvedValue(NO_PASSKEYS);
  refresh.mockClear();
  user.current = { ...user.current, mfa_enabled: false };
});

describe("Account page: two-step sign-in", () => {
  it("groups the setup key in fours", () => {
    expect(groupKey("JBSWY3DPEHPK3PXP")).toBe("JBSW Y3DP EHPK 3PXP");
  });

  it("turns it on: shows the key, then confirms with the app's code", async () => {
    post.mockImplementation(async (path: string) =>
      path === "/auth/mfa/enroll/" ? { secret: "JBSWY3DPEHPK3PXP", provisioning_uri: "otpauth://totp/x" } : {},
    );
    renderWithQuery(<AccountClient />);
    await userEvent.click(screen.getByRole("button", { name: "Turn on two-step sign-in" }));
    expect(await screen.findByText("JBSW Y3DP EHPK 3PXP")).toBeInTheDocument();
    const turnOn = screen.getByRole("button", { name: "Turn on" });
    expect(turnOn).toBeDisabled();
    await userEvent.type(screen.getByLabelText("Code from the app"), "123456");
    await userEvent.click(turnOn);
    await waitFor(() => expect(post).toHaveBeenCalledWith("/auth/mfa/confirm/", { code: "123456" }));
    expect(refresh).toHaveBeenCalled();
  });

  it("turning it off asks for a current code", async () => {
    user.current = { ...user.current, mfa_enabled: true };
    renderWithQuery(<AccountClient />);
    expect(screen.getByText("On")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Turn off two-step sign-in" }));
    await userEvent.type(screen.getByLabelText("Current code"), "654321");
    await userEvent.click(screen.getByRole("button", { name: "Turn off" }));
    await waitFor(() => expect(post).toHaveBeenCalledWith("/auth/mfa/disable/", { code: "654321" }));
  });

  it("keeps the form and says why when the server refuses", async () => {
    const { ApiError } = await import("@/lib/api");
    post.mockRejectedValue(new ApiError(400, { detail: "Two-step sign-in is already on. Turn it off with a current code first." }));
    renderWithQuery(<AccountClient />);
    await userEvent.click(screen.getByRole("button", { name: "Turn on two-step sign-in" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("already on");
  });
});

describe("Account page: passkeys", () => {
  const phone = {
    id: "p1", name: "My phone", rp_id: "localhost", backed_up: true, transports: ["hybrid"],
    created_at: "2026-11-08T10:00:00Z", last_used_at: null,
  };

  it("lists the passkeys with the address each one belongs to", async () => {
    get.mockResolvedValue({ ...NO_PASSKEYS, passkeys: [phone] });
    renderWithQuery(<AccountClient />);
    expect(await screen.findByText("My phone")).toBeInTheDocument();
    expect(screen.getByText(/For localhost \(this address\)/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Sign in with passkey only" })).toBeInTheDocument();
  });

  it("switching to passkey only asks for the password again", async () => {
    get.mockResolvedValue({ ...NO_PASSKEYS, passkeys: [phone] });
    post.mockResolvedValue({});
    renderWithQuery(<AccountClient />);
    await userEvent.click(await screen.findByRole("button", { name: "Sign in with passkey only" }));
    await userEvent.type(screen.getByLabelText("Your password"), "a-strong-passw0rd!");
    await userEvent.click(screen.getByRole("button", { name: "Passkey only" }));
    await waitFor(() =>
      expect(post).toHaveBeenCalledWith("/auth/passkeys/only/", { on: true, password: "a-strong-passw0rd!", code: "" }),
    );
  });

  it("removing a passkey asks for the password", async () => {
    get.mockResolvedValue({ ...NO_PASSKEYS, passkeys: [phone] });
    post.mockResolvedValue({});
    renderWithQuery(<AccountClient />);
    await userEvent.click(await screen.findByRole("button", { name: "Remove My phone" }));
    await userEvent.type(screen.getByLabelText("Your password"), "pw-123456789012");
    await userEvent.click(screen.getByRole("button", { name: "Remove" }));
    await waitFor(() =>
      expect(post).toHaveBeenCalledWith("/auth/passkeys/p1/remove/", { password: "pw-123456789012", code: "" }),
    );
  });

  it("explains that an address made of numbers cannot use passkeys", async () => {
    get.mockResolvedValue({ ...NO_PASSKEYS, this_address: null });
    renderWithQuery(<AccountClient />);
    expect(await screen.findByText(/need IntraForge's name in the address/)).toBeInTheDocument();
  });
});
