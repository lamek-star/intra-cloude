import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

const { get, post } = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn() }));
vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return { ...actual, api: { ...actual.api, get, post } };
});

import { ShareSection } from "./ShareSection";

const MEMBER = { id: "m1", status: "active", user: { id: "u1", email: "cashier@example.com" } };

beforeEach(() => {
  get.mockReset();
  post.mockReset();
  get.mockImplementation(async (path: string) => {
    if (path.endsWith("/members/")) return [MEMBER];
    return [];
  });
});

describe("ShareSection for business operations", () => {
  const levels = [
    { value: "sell" as const, label: "Sell", hint: "Record sales: the order, its lines, the stock taken out and the invoice." },
    { value: "receive" as const, label: "Receive", hint: "Receive stock into a warehouse." },
  ];

  it("offers exactly the operations it is given, with what each one allows, and nothing like Read/Write/Admin", async () => {
    const user = userEvent.setup();
    render(
      <ShareSection organizationId="o1" resourceType="inventory_operations" resourceId="app1" title="Business operations" levels={levels} />,
    );
    expect(await screen.findByRole("heading", { name: "Business operations" })).toBeInTheDocument();
    await user.click(await screen.findByRole("button", { name: "Share" }));
    const dialog = await screen.findByRole("dialog");
    const options = within(dialog).getAllByRole("option").map((o) => o.textContent);
    expect(options).toContain("Sell");
    expect(options).toContain("Receive");
    expect(options).not.toContain("Read");
    expect(options).not.toContain("Admin");
    expect(within(dialog).getByText(/Record sales/)).toBeInTheDocument();
  });

  it("grants exactly the chosen operation on the application, to the chosen member", async () => {
    post.mockResolvedValue({
      id: "s1", organization: "o1", resource_type: "inventory_operations", resource_id: "app1",
      principal_type: "user", user: "u1", team: null, level: "receive", expires_at: null, revoked_at: null,
      created_by: "owner", created_at: "2026-09-20T00:00:00Z",
    });
    const user = userEvent.setup();
    render(<ShareSection organizationId="o1" resourceType="inventory_operations" resourceId="app1" levels={levels} />);
    await user.click(await screen.findByRole("button", { name: "Share" }));
    const dialog = await screen.findByRole("dialog");
    await user.selectOptions(within(dialog).getByLabelText("Access level"), "receive");
    await user.click(within(dialog).getByRole("button", { name: /^Share$/ }));
    expect(post).toHaveBeenCalledTimes(1);
    const [path, body] = post.mock.calls[0];
    expect(path).toBe("/organizations/o1/shares/");
    expect(body).toMatchObject({
      resource_type: "inventory_operations",
      resource_id: "app1",
      principal_type: "user",
      level: "receive",
      user_id: "u1",
    });
    expect(await screen.findByText("Receive")).toBeInTheDocument(); // listed with its readable label
  });

  it("keeps the ordinary Read/Write/Admin levels for other resources", async () => {
    const user = userEvent.setup();
    render(<ShareSection organizationId="o1" resourceType="app_instance" resourceId="app1" />);
    await user.click(await screen.findByRole("button", { name: "Share" }));
    const dialog = await screen.findByRole("dialog");
    expect(within(dialog).getAllByRole("option").map((o) => o.textContent)).toEqual(
      expect.arrayContaining(["Read", "Write", "Admin"]),
    );
  });
});
