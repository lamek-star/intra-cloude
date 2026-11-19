import { describe, expect, it } from "vitest";
import { parseUris } from "./_client";

describe("sign-in client return addresses", () => {
  it("takes one address per line and drops blanks and spaces", () => {
    expect(parseUris(" https://a.example.com/cb \r\n\n https://b.example.com/cb\n")).toEqual([
      "https://a.example.com/cb",
      "https://b.example.com/cb",
    ]);
  });
});
