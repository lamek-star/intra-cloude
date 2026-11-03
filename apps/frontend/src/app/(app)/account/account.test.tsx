import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

const { post, refresh, user } = vi.hoisted(() => ({
  post: vi.fn(),
  refresh: vi.fn(async () => {}),
  user: { current: { id: "u1", email: "owner@shop.test", first_name: "", last_name: "", date_joined: "", mfa_enabled: false } },
}));
vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return { ...actual, api: { ...actual.api, post }, ensureCsrfCookie: async () => {} };
});
vi.mock("@/lib/auth-context", () => ({ useAuth: () => ({ user: user.current, refresh }) }));

import AccountClient, { groupKey } from "./_client";

beforeEach(() => {
  post.mockReset();
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
    render(<AccountClient />);
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
    render(<AccountClient />);
    expect(screen.getByText("On")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Turn off two-step sign-in" }));
    await userEvent.type(screen.getByLabelText("Current code"), "654321");
    await userEvent.click(screen.getByRole("button", { name: "Turn off" }));
    await waitFor(() => expect(post).toHaveBeenCalledWith("/auth/mfa/disable/", { code: "654321" }));
  });

  it("keeps the form and says why when the server refuses", async () => {
    const { ApiError } = await import("@/lib/api");
    post.mockRejectedValue(new ApiError(400, { detail: "Two-step sign-in is already on. Turn it off with a current code first." }));
    render(<AccountClient />);
    await userEvent.click(screen.getByRole("button", { name: "Turn on two-step sign-in" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("already on");
  });
});
