import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";

const { get } = vi.hoisted(() => ({ get: vi.fn() }));
vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return { ...actual, api: { ...actual.api, get } };
});

vi.mock("./BusinessApp", async () => {
  const { testSchema } = await import("@/lib/test-schema");
  const schema = testSchema();
  return { useBusiness: () => ({ schema, instance: { id: "app1", label: "My Shop", project: "p1" } }) };
});

import { ApiError } from "@/lib/api";
import Overview from "./Overview";

beforeEach(() => get.mockReset());

describe("Overview counts", () => {
  it("shows each count the person may read even when another model is refused to them", async () => {
    get.mockImplementation(async (path?: string) => {
      if (path?.includes("/app-models/M:supplier/records/")) throw new ApiError(403, { detail: "You do not have permission to perform this action." });
      return { count: 7, limit: 1, offset: 0, results: [] };
    });
    render(<Overview />);
    expect(await screen.findByRole("link", { name: /^Products\s*7/ })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /^Customers\s*7/ })).toBeInTheDocument();
    // The refused model shows a dash and says it isn't available -- not a number, and not a blank page.
    expect(screen.getByRole("link", { name: /^Suppliers\s*—\s*not available/ })).toBeInTheDocument();
  });
});
