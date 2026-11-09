import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { looksLikeToyotaNumber, ToyoDiyLookup, TOYODIY_XREF_URL, toyoDiyNumber } from "./ToyoDiyLookup";

describe("ToyoDIY lookup", () => {
  it("cleans a number the way the cross-reference box expects it", () => {
    expect(toyoDiyNumber("04465-0k290")).toBe("044650K290");
    expect(toyoDiyNumber(" 90915 YZZE1 ")).toBe("90915YZZE1");
  });

  it("offers the lookup only for Toyota-shaped numbers", () => {
    expect(looksLikeToyotaNumber("04465-0K290")).toBe(true);
    expect(looksLikeToyotaNumber("NM-847249")).toBe(false);
    expect(looksLikeToyotaNumber("ABC")).toBe(false);
  });

  it("opens the public cross-reference in a new tab and renders nothing for other numbers", () => {
    render(<ToyoDiyLookup number="04465-0K290" />);
    const link = screen.getByRole("link", { name: /look up 044650K290 on toyodiy/i });
    expect(link).toHaveAttribute("href", TOYODIY_XREF_URL);
    expect(link).toHaveAttribute("target", "_blank");
    expect(link).toHaveAttribute("rel", "noopener noreferrer");
    const { container } = render(<ToyoDiyLookup number="NM-847249" />);
    expect(container).toBeEmptyDOMElement();
  });
});
