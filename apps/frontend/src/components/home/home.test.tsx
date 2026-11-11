import { beforeAll, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ProductDemo } from "./ProductDemo";
import { SetupWalkthrough } from "./SetupWalkthrough";
import { SCENES } from "./DemoScenes";

// jsdom has no layout: the observers and the media query are stand-ins.
beforeAll(() => {
  class Observer {
    observe() {}
    disconnect() {}
    unobserve() {}
  }
  vi.stubGlobal("ResizeObserver", Observer);
  vi.stubGlobal("IntersectionObserver", Observer);
  vi.stubGlobal(
    "matchMedia",
    vi.fn().mockImplementation((query: string) => ({ matches: false, media: query, addEventListener: () => {}, removeEventListener: () => {} })),
  );
});

describe("the home page demo", () => {
  it("names every scene and switches to the one asked for", async () => {
    render(<ProductDemo />);
    expect(screen.getByRole("region", { name: /intraforge demo with sample data/i })).toBeInTheDocument();
    for (const scene of SCENES) expect(screen.getByRole("button", { name: scene.title })).toBeInTheDocument();
    expect(screen.getByText(SCENES[0].caption)).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Install business apps" }));
    expect(screen.getByRole("button", { name: "Install business apps" })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByText(SCENES[2].caption)).toBeInTheDocument();
  });

  it("can be paused, so the motion stops for anyone who wants it to", async () => {
    render(<ProductDemo />);
    await userEvent.click(screen.getByRole("button", { name: "Pause" }));
    expect(screen.getByRole("button", { name: "Play" })).toBeInTheDocument();
  });
});

describe("the setup walkthrough", () => {
  it("shows the real Setup screens for the first two steps and says when a picture is only an illustration", async () => {
    render(<SetupWalkthrough />);
    expect(screen.getByRole("img", { name: /choose the install and data folders/i })).toBeInTheDocument();
    expect(screen.getByText("Real screens from IntraForge Setup")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: /it installs itself/i }));
    expect(screen.getByRole("img", { name: /installing/i })).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: /create the owner account/i }));
    expect(screen.getByText("Illustration with sample names")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /create the owner account/i })).toHaveAttribute("aria-current", "step");
  });
});
