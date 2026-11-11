import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { TOUR_SLIDES, WelcomeTour } from "./WelcomeTour";
import { COPYRIGHT, versionLine } from "@/lib/brand";
import { markTourSeen, readTourState, rememberTourRequest, shouldShowTour, tourRequestFrom, TOUR_REQUEST_KEY, tourSeenKey } from "@/lib/tour";

// An in-memory localStorage: the test environment's own one is not always a complete Storage.
function memoryStorage(): Storage {
  const items = new Map<string, string>();
  return {
    get length() {
      return items.size;
    },
    clear: () => items.clear(),
    getItem: (k) => items.get(k) ?? null,
    key: (i) => [...items.keys()][i] ?? null,
    removeItem: (k) => void items.delete(k),
    setItem: (k, v) => void items.set(k, String(v)),
  };
}

describe("when the welcome tour opens", () => {
  beforeEach(() => {
    Object.defineProperty(window, "localStorage", { value: memoryStorage(), configurable: true });
  });

  it("reads Setup's wish from the address", () => {
    expect(tourRequestFrom("?tour=1")).toBe("show");
    expect(tourRequestFrom("?tour=off")).toBe("off");
    expect(tourRequestFrom("?next=/apps")).toBeNull();
  });

  it("opens once per person, unless Setup said otherwise", () => {
    expect(shouldShowTour(false, null)).toBe(true);
    expect(shouldShowTour(true, null)).toBe(false);
    expect(shouldShowTour(true, "show")).toBe(true);
    expect(shouldShowTour(false, "off")).toBe(false);
  });

  it("remembers the wish until sign-in, and forgets it once the tour is done", () => {
    rememberTourRequest("off");
    expect(readTourState("u1")).toEqual({ seen: false, request: "off" });
    markTourSeen("u1");
    expect(window.localStorage.getItem(tourSeenKey("u1"))).toBe("1");
    expect(window.localStorage.getItem(TOUR_REQUEST_KEY)).toBeNull();
    expect(readTourState("u2").seen).toBe(false); // another person on the same browser still gets it
  });
});

describe("the version line", () => {
  it("shows the version without its build suffix, with the owner's copyright", () => {
    expect(versionLine("1.5.2-ce9b03c85")).toBe(`IntraForge 1.5.2 · ${COPYRIGHT}`);
    expect(versionLine(undefined)).toBe(`IntraForge · ${COPYRIGHT}`);
    expect(COPYRIGHT).toContain("lamek-rusoom");
  });
});

describe("WelcomeTour", () => {
  it("walks through every slide and ends with the version and copyright", async () => {
    const onClose = vi.fn();
    render(<WelcomeTour open onClose={onClose} version="1.5.2-ce9b03c85" />);
    expect(screen.getByRole("dialog", { name: "Welcome to IntraForge" })).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: /take the tour/i }));
    for (const slide of TOUR_SLIDES.slice(1, -1)) {
      expect(screen.getByRole("heading", { name: slide.title })).toBeInTheDocument();
      await userEvent.click(screen.getByRole("button", { name: /^next/i }));
    }
    expect(screen.getByText(`IntraForge 1.5.2 · ${COPYRIGHT}`)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /skip tour/i })).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: /start using intraforge/i }));
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("goes back, jumps to a slide, and can be skipped", async () => {
    const onClose = vi.fn();
    render(<WelcomeTour open onClose={onClose} />);
    await userEvent.click(screen.getByRole("tab", { name: /slide 4/i }));
    expect(screen.getByRole("heading", { name: "Connect apps, safely" })).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Back" }));
    expect(screen.getByRole("heading", { name: "Databases and business apps" })).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: /skip tour/i }));
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("renders nothing when closed", () => {
    const { container } = render(<WelcomeTour open={false} onClose={() => {}} />);
    expect(container).toBeEmptyDOMElement();
  });
});
