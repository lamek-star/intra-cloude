import { beforeEach, describe, expect, it, vi } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";

const { get } = vi.hoisted(() => ({ get: vi.fn() }));
vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return { ...actual, api: { ...actual.api, get } };
});

import { runtimeInstanceId, runtimeLabels, useRuntimeLabels } from "./runtime-names";

const INSTANCE = "d880bbdf-97a8-4e81-8824-818dcb30957d";
const schema = {
  models: [
    {
      id: "00006823-5920-4e9b-8bfb-ff289457fbed",
      label: "Part",
      fields: [{ id: "3d0e118c-c72a-4723-b2ce-f5fd93b31f5c", label: "Part name" }],
    },
  ],
  relationships: [{ id: "9e045907-eb65-4dbd-90fb-aef2ae7c39bc", label: "Supplier" }],
};

beforeEach(() => get.mockReset());

describe("runtime database names", () => {
  it("recognises only an application's runtime database", () => {
    expect(runtimeInstanceId(`App runtime ${INSTANCE}`)).toBe(INSTANCE);
    expect(runtimeInstanceId("Shop data")).toBeNull();
    expect(runtimeInstanceId(`My App runtime ${INSTANCE}`)).toBeNull();
  });

  it("maps physical table and column names to the labels in the definition", () => {
    const labels = runtimeLabels(schema as never);
    expect(labels["m_0000682359204e9b8bfbff289457fbed"]).toBe("Part");
    expect(labels["f_3d0e118cc72a4723b2cef5fd93b31f5c"]).toBe("Part name");
    expect(labels["r_9e045907eb654dbd90fbaef2ae7c39bc"]).toBe("Supplier");
    expect(labels["j_9e045907eb654dbd90fbaef2ae7c39bc"]).toBe("Supplier");
  });

  it("loads the definition for a runtime database and nothing for any other", async () => {
    get.mockResolvedValue(schema);
    const { result } = renderHook(() => useRuntimeLabels(`App runtime ${INSTANCE}`));
    await waitFor(() => expect(result.current["m_0000682359204e9b8bfbff289457fbed"]).toBe("Part"));
    expect(get).toHaveBeenCalledWith(`/app-instances/${INSTANCE}/schema/`);

    get.mockClear();
    renderHook(() => useRuntimeLabels("Shop data"));
    expect(get).not.toHaveBeenCalled();
  });
});
