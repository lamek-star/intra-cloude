import { beforeEach, describe, expect, it, vi } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";

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
import { useNames } from "./hooks";

beforeEach(() => {
  get.mockReset();
});

const ids = (n: number) => Array.from({ length: n }, (_, i) => `part-${String(i).padStart(3, "0")}`);

describe("useNames", () => {
  it("names a whole page of rows with ONE request, not one per row", async () => {
    get.mockImplementation(async (path: string) => {
      const asked = new URL(path, "http://x").searchParams.get("ids")!.split(",");
      return {
        count: asked.length,
        limit: 100,
        offset: 0,
        results: asked.map((id) => ({ id, "F:part.name": `Name of ${id}` })),
      };
    });
    const { result } = renderHook(() => useNames("part", "name", ids(25)));
    await waitFor(() => expect(Object.keys(result.current)).toHaveLength(25));
    expect(get).toHaveBeenCalledTimes(1);
    expect(result.current["part-007"]).toBe("Name of part-007");
    expect(get.mock.calls[0][0]).toContain("/app-models/M:part/records/?ids=");
  });

  it("asks once for repeated ids, and stays within the server's 100-id cap", async () => {
    get.mockImplementation(async (path: string) => {
      const asked = new URL(path, "http://x").searchParams.get("ids")!.split(",");
      expect(asked.length).toBeLessThanOrEqual(100);
      return { count: asked.length, limit: 100, offset: 0, results: asked.map((id) => ({ id, "F:part.name": id })) };
    });
    const repeated = [...ids(130), ...ids(130)];
    const { result } = renderHook(() => useNames("part", "name", repeated));
    await waitFor(() => expect(Object.keys(result.current)).toHaveLength(130));
    expect(get).toHaveBeenCalledTimes(2); // 130 distinct ids -> 100 + 30
  });

  it("does not ask again for ids it already knows when the page re-renders", async () => {
    get.mockImplementation(async (path: string) => {
      const asked = new URL(path, "http://x").searchParams.get("ids")!.split(",");
      return { count: asked.length, limit: 100, offset: 0, results: asked.map((id) => ({ id, "F:part.name": id })) };
    });
    const { result, rerender } = renderHook(({ list }) => useNames("part", "name", list), {
      initialProps: { list: ids(3) },
    });
    await waitFor(() => expect(Object.keys(result.current)).toHaveLength(3));
    rerender({ list: [...ids(3), "part-999"] });
    await waitFor(() => expect(result.current["part-999"]).toBe("part-999"));
    expect(get).toHaveBeenCalledTimes(2);
    expect(new URL(get.mock.calls[1][0], "http://x").searchParams.get("ids")).toBe("part-999"); // only the new one
  });

  it("marks an id the server did not return, or a refused request, as unavailable -- never blank, never throwing", async () => {
    get.mockImplementationOnce(async () => ({ count: 1, limit: 100, offset: 0, results: [{ id: "a", "F:part.name": "Alpha" }] }));
    const { result } = renderHook(() => useNames("part", "name", ["a", "b"]));
    await waitFor(() => expect(Object.keys(result.current)).toHaveLength(2));
    expect(result.current).toEqual({ a: "Alpha", b: "(unavailable)" });

    get.mockRejectedValueOnce(new ApiError(403, { detail: "no" }));
    const refused = renderHook(() => useNames("part", "name", ["c"]));
    await waitFor(() => expect(refused.result.current).toEqual({ c: "(unavailable)" }));
  });
});
