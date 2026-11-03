import { beforeEach, describe, expect, it, vi } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";

const { get } = vi.hoisted(() => ({ get: vi.fn() }));
vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return { ...actual, api: { ...actual.api, get } };
});

import { useProjectTrail } from "./project-trail";

const responses: Record<string, unknown> = {
  "/projects/p1/": { id: "p1", name: "Spare Parts", workspace: "w1" },
  "/workspaces/w1/": { id: "w1", name: "Applications", organization: "o1" },
  "/organizations/o1/": { id: "o1", name: "Micheal LLC" },
};

beforeEach(() => {
  get.mockReset();
});

describe("useProjectTrail", () => {
  it("links every level: organization, workspace, project", async () => {
    get.mockImplementation(async (path: string) => responses[path]);
    const { result } = renderHook(() => useProjectTrail("p1"));
    await waitFor(() => expect(result.current).toHaveLength(3));
    expect(result.current).toEqual([
      { label: "Micheal LLC", href: "/orgs/o1" },
      { label: "Applications", href: "/orgs/o1/workspaces/w1" },
      { label: "Spare Parts", href: "/projects/p1" },
    ]);
  });

  it("keeps the project when the workspace cannot be read", async () => {
    get.mockImplementation(async (path: string) => {
      if (path.startsWith("/workspaces/")) throw new Error("403");
      return responses[path];
    });
    const { result } = renderHook(() => useProjectTrail("p1"));
    await waitFor(() => expect(result.current).toHaveLength(1));
    expect(result.current[0]).toEqual({ label: "Spare Parts", href: "/projects/p1" });
  });

  it("asks for nothing without a project id", () => {
    const { result } = renderHook(() => useProjectTrail(undefined));
    expect(result.current).toEqual([]);
    expect(get).not.toHaveBeenCalled();
  });
});
