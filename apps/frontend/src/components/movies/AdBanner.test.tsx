import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { AdBanner } from "./AdBanner";

const AD = { title: "Phones at Abel's", text: "10% off this week", advertiser: "Abel Phones", film: null, link: "https://abel.example", has_picture: false };

describe("AdBanner", () => {
  it("always says it is an ad and who it is for", () => {
    render(<AdBanner ad={AD} shopName="Lamek Movies" />);
    expect(screen.getByText("Ad · Abel Phones")).toBeInTheDocument();
    expect(screen.getByText("Open")).toBeInTheDocument();
  });

  it("names the shop when the ad is the shop's own, and offers Watch for a film", () => {
    render(<AdBanner ad={{ ...AD, advertiser: "", link: "", film: "f1" }} shopName="Lamek Movies" />);
    expect(screen.getByText("Ad · Lamek Movies")).toBeInTheDocument();
    expect(screen.getByText("Watch")).toBeInTheDocument();
  });

  it("is a button only when tapping does something", () => {
    const onTap = vi.fn();
    const { rerender } = render(<AdBanner ad={AD} shopName="Lamek Movies" onTap={onTap} />);
    fireEvent.click(screen.getByRole("button", { name: "Ad: Phones at Abel's" }));
    expect(onTap).toHaveBeenCalledOnce();
    rerender(<AdBanner ad={{ ...AD, link: "" }} shopName="Lamek Movies" />);
    expect(screen.queryByRole("button")).toBeNull();
  });
});
