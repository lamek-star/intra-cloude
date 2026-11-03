import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemberRoles, type RoleOption } from "./MemberRoles";

const roles: RoleOption[] = [
  { slug: "viewer", name: "Viewer", summary: "Read only", administrative: false },
  { slug: "spare-parts-sales", name: "Spare Parts Sales", summary: "Sell", administrative: false },
];

describe("MemberRoles", () => {
  it("offers the role picker for a person", () => {
    render(<MemberRoles orgId="o1" membershipId="m1" who="sara@shop.test" roles={roles} held={[]} onChange={() => {}} />);
    expect(screen.getByRole("combobox", { name: "Give sara@shop.test a role" })).toBeInTheDocument();
  });

  it("shows why, and no picker, for an application's sign-in", () => {
    render(
      <MemberRoles
        orgId="o1"
        membershipId="m2"
        who="service-account+1@service.internal"
        roles={roles}
        held={[]}
        onChange={() => {}}
        givingRefused="Access is given on the application's page, not as a role."
      />,
    );
    expect(screen.queryByRole("combobox")).not.toBeInTheDocument();
    expect(screen.getByText(/application's page/)).toBeInTheDocument();
  });
});
