import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

const { get, post } = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn() }));
vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return { ...actual, ensureCsrfCookie: vi.fn(async () => undefined), api: { ...actual.api, get, post } };
});

import { AccessRequests } from "./AccessRequests";
import { tokenFromHash } from "@/lib/access";

const ROLES = [
  { slug: "spare-parts-sales", name: "Spare Parts Sales", summary: "", administrative: false },
  { slug: "spare-parts-viewer", name: "Spare Parts Viewer", summary: "", administrative: false },
];
const PENDING = {
  id: "r1",
  status: "pending",
  email: "hana@example.test",
  name: "Hana Tesfay",
  phone: "+971 50 111 2222",
  app: { id: "a1", name: "lamek general trading LLC", type: "spare_parts" },
  requested_role: "spare-parts-sales",
  requested_role_name: "Spare Parts Sales",
  granted_role: "",
  message: "Counter",
  new_account: true,
  activated: false,
  decision_note: "",
  decided_by: null,
  decided_at: null,
  created_at: "2026-11-22T10:00:00Z",
};

beforeEach(() => {
  get.mockReset();
  post.mockReset();
});

describe("AccessRequests", () => {
  it("approves with the role the administrator chooses and shows the link once", async () => {
    get.mockResolvedValue({ results: [PENDING], email_enabled: false });
    post.mockResolvedValue({ link: "https://localhost:8443/confirm#t=abcdefghijklmnop", emailed: false });
    render(<AccessRequests orgId="o1" roles={ROLES} />);
    await userEvent.click(await screen.findByRole("button", { name: "Approve" }));
    await userEvent.selectOptions(screen.getByLabelText("Role to give"), "spare-parts-viewer");
    await userEvent.click(screen.getAllByRole("button", { name: "Approve" }).at(-1)!);
    expect(post).toHaveBeenCalledWith("/organizations/o1/access-requests/r1/approve/", {
      role_slug: "spare-parts-viewer",
      note: "",
    });
    expect(await screen.findByText("https://localhost:8443/confirm#t=abcdefghijklmnop")).toBeTruthy();
    expect(screen.getByText(/nothing was sent/)).toBeTruthy();
  });

  it("renders nothing for someone who may not give roles", async () => {
    get.mockRejectedValue(new Error("403"));
    const { container } = render(<AccessRequests orgId="o1" roles={ROLES} />);
    await waitFor(() => expect(get).toHaveBeenCalled());
    expect(container.textContent).toBe("");
  });
});

describe("tokenFromHash", () => {
  it("reads the token from the fragment only", () => {
    expect(tokenFromHash("#t=Abc_def-1234567")).toBe("Abc_def-1234567");
    expect(tokenFromHash("")).toBe("");
    expect(tokenFromHash("#t=<script>")).toBe("");
  });
});
