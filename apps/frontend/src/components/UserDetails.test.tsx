import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

const { patch } = vi.hoisted(() => ({ patch: vi.fn() }));
vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return { ...actual, ensureCsrfCookie: vi.fn(async () => undefined), api: { ...actual.api, patch } };
});

import { detailsOf, EditMemberDetails, UserDetailsForm } from "./UserDetails";
import { ApiError, type User } from "@/lib/api";

const STAFF = {
  id: "u1",
  email: "staff@example.com",
  first_name: "Hana",
  last_name: "",
  date_joined: "2026-11-21T00:00:00Z",
  mfa_enabled: false,
} as User;

beforeEach(() => patch.mockReset());

describe("UserDetailsForm", () => {
  it("sends every field and reports the save", async () => {
    const save = vi.fn(async (d) => ({ ...STAFF, ...d }) as User);
    const onSaved = vi.fn();
    render(<UserDetailsForm initial={detailsOf(STAFF)} save={save} onSaved={onSaved} />);
    await userEvent.type(screen.getByLabelText("Phone"), "+971 50 123 4567");
    await userEvent.type(screen.getByLabelText("Job title"), "Cashier");
    await userEvent.click(screen.getByRole("button", { name: "Save" }));
    expect(save).toHaveBeenCalledWith({
      first_name: "Hana",
      last_name: "",
      phone: "+971 50 123 4567",
      job_title: "Cashier",
      address: "",
      emergency_contact: "",
    });
    expect(onSaved).toHaveBeenCalled();
    expect(await screen.findByText("Saved.")).toBeTruthy();
  });

  it("shows the server's refusal instead of saving silently", async () => {
    const save = vi.fn(async () => {
      throw new ApiError(400, { phone: ["Enter a phone number: digits, spaces, +, -, ( and ) only."] });
    });
    render(<UserDetailsForm initial={detailsOf(STAFF)} save={save} onSaved={vi.fn()} />);
    await userEvent.type(screen.getByLabelText("Phone"), "call me");
    await userEvent.click(screen.getByRole("button", { name: "Save" }));
    expect(await screen.findByText(/Enter a phone number/)).toBeTruthy();
    expect(screen.queryByText("Saved.")).toBeNull();
  });
});

describe("EditMemberDetails", () => {
  it("saves a member's details through the organization's members endpoint", async () => {
    patch.mockResolvedValue({ ...STAFF, phone: "0501234567" });
    const onSaved = vi.fn();
    render(<EditMemberDetails orgId="o1" membershipId="m1" user={STAFF} onSaved={onSaved} />);
    await userEvent.click(screen.getByRole("button", { name: "Edit the details of staff@example.com" }));
    await userEvent.type(screen.getByLabelText("Phone"), "0501234567");
    await userEvent.click(screen.getByRole("button", { name: "Save" }));
    expect(patch).toHaveBeenCalledWith(
      "/organizations/o1/members/m1/profile/",
      expect.objectContaining({ phone: "0501234567" }),
    );
    expect(onSaved).toHaveBeenCalledWith(expect.objectContaining({ phone: "0501234567" }));
  });
});
