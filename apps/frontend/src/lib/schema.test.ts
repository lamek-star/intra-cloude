import { beforeEach, describe, expect, it, vi } from "vitest";

const { get } = vi.hoisted(() => ({ get: vi.fn() }));
vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return { ...actual, api: { ...actual.api, get } };
});

import { loadSchema } from "./business";

beforeEach(() => get.mockReset());

describe("loadSchema", () => {
  it("resolves ids from ONE request, however many models the application has", async () => {
    get.mockResolvedValue({
      models: Array.from({ length: 13 }, (_, i) => ({
        id: `M${i}`, instance: "i1", key: `model_${i}`, label: `Model ${i}`, position: i, source_definition_id: null,
        fields: [{ id: `F${i}`, model: `M${i}`, key: "name", label: "Name", data_type: "text", required: true, default_value: null, position: 0, source_definition_id: null }],
      })),
      relationships: [
        { id: "R1", instance: "i1", key: "link", label: "Link", position: 0, source_definition_id: null, source_model: "M3", target_model: "M4", kind: "many_to_one", deletion_policy: "restrict" },
      ],
    });
    const schema = await loadSchema("i1");
    expect(get).toHaveBeenCalledTimes(1);
    expect(get).toHaveBeenCalledWith("/app-instances/i1/schema/");
    expect(schema.modelId("model_12")).toBe("M12");
    expect(schema.id("model_3", "name")).toBe("F3");
    expect(schema.id("model_3", "link")).toBe("R1");
  });
});
