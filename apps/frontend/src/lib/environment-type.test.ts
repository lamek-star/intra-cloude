import { describe, expect, it } from "vitest";
import { exampleEnvironmentName, namesProductionWithoutType } from "./environment-type";

describe("environment type helpers", () => {
  it("suggests a name that matches the chosen type", () => {
    expect(exampleEnvironmentName("development")).toBe("Development");
    expect(exampleEnvironmentName("production")).toBe("Production");
    expect(exampleEnvironmentName("staging")).toBe("Staging");
  });

  it("flags a production-sounding name on a non-production type", () => {
    expect(namesProductionWithoutType("Production", "development")).toBe(true);
    expect(namesProductionWithoutType("shop prod", "staging")).toBe(true);
  });

  it("stays quiet when the type matches or the name is unrelated", () => {
    expect(namesProductionWithoutType("Production", "production")).toBe(false);
    expect(namesProductionWithoutType("Product catalogue", "development")).toBe(false);
    expect(namesProductionWithoutType("Development", "development")).toBe(false);
  });
});
