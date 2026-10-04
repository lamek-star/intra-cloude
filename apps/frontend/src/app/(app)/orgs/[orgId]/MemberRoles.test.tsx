import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

const { post, del } = vi.hoisted(() => ({ post: vi.fn(), del: vi.fn() }));
vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return { ...actual, api: { ...actual.api, post, del } };
});

import { ApiError } from "@/lib/api";
import { MemberRoles, type RoleOption } from "./MemberRoles";

const ROLES: RoleOption[] = [
  { slug: "organization-administrator", name: "Organization Administrator", summary: "Everything.", administrative: true },
  { slug: "spare-parts-sales", name: "Spare Parts Sales", summary: "Selling. No cost prices.", administrative: false },
  { slug: "spare-parts-viewer", name: "Spare Parts Viewer", summary: "Look only.", administrative: false },
];

function setup(held: string[]) {
  const onChange = vi.fn();
  render(
    <MemberRoles orgId="o1" membershipId="m1" who="sara@shop.test" roles={ROLES} held={held} onChange={onChange} />,
  );
  return onChange;
}

describe("member roles", () => {
  beforeEach(() => {
    post.mockReset();
    del.mockReset();
  });

  it("says a member without a role can open nothing yet", () => {
    setup([]);
    expect(screen.getByText(/No role/)).toBeInTheDocument();
  });

  it("gives a chosen role, showing what it allows first", async () => {
    post.mockResolvedValue({ id: "r1", role: "spare-parts-sales" });
    const onChange = setup([]);
    await userEvent.selectOptions(screen.getByLabelText("Give sara@shop.test a role"), "spare-parts-sales");
    expect(screen.getByText("Selling. No cost prices.")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Give" }));
    expect(post).toHaveBeenCalledWith("/organizations/o1/members/m1/role/", { role_slug: "spare-parts-sales" });
    await waitFor(() => expect(onChange).toHaveBeenCalledWith(["spare-parts-sales"]));
  });

  it("does not offer a role the member already has", () => {
    setup(["spare-parts-sales"]);
    const options = Array.from((screen.getByLabelText("Give sara@shop.test a role") as HTMLSelectElement).options);
    expect(options.map((o) => o.value)).not.toContain("spare-parts-sales");
  });

  it("takes a role away after confirming", async () => {
    vi.spyOn(window, "confirm").mockReturnValue(true);
    del.mockResolvedValue(undefined);
    const onChange = setup(["spare-parts-sales", "spare-parts-viewer"]);
    await userEvent.click(screen.getByRole("button", { name: "Take away Spare Parts Sales from sara@shop.test" }));
    expect(del).toHaveBeenCalledWith("/organizations/o1/members/m1/roles/spare-parts-sales/");
    await waitFor(() => expect(onChange).toHaveBeenCalledWith(["spare-parts-viewer"]));
  });

  it("keeps the role and shows why when the server refuses", async () => {
    vi.spyOn(window, "confirm").mockReturnValue(true);
    del.mockRejectedValue(
      new ApiError(409, { detail: "This is the organization's last Organization Administrator." }),
    );
    const onChange = setup(["organization-administrator"]);
    await userEvent.click(
      screen.getByRole("button", { name: "Take away Organization Administrator from sara@shop.test" }),
    );
    expect(await screen.findByText(/last Organization Administrator/)).toBeInTheDocument();
    expect(onChange).not.toHaveBeenCalled();
  });
});
