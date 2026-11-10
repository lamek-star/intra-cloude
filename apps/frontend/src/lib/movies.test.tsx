import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { agentOnline, drawnCover, formatBytes, pairCommand, titlesLabel, type MovieTitle } from "./movies";
import { MovieCover } from "@/components/movies/MovieCover";

const TITLE: MovieTitle = {
  id: "t1",
  library: "l1",
  relative_path: "Action\\Desert Wind (2025).mp4",
  category: "Action",
  title: "Desert Wind",
  year: 2025,
  kind: "movie",
  size_bytes: 2_100_000_000,
  episodes: 1,
  has_cover: false,
  price: 50,
  own_price: null,
  hidden: false,
  description: "",
};

describe("the Movie Shop helpers", () => {
  it("writes sizes the way people read them", () => {
    expect(formatBytes(2_100_000_000)).toBe("2.1 GB");
    expect(formatBytes(512)).toBe("512 B");
    expect(formatBytes(null)).toBe("—");
  });

  it("counts titles in plain words", () => {
    expect(titlesLabel(1)).toBe("1 title");
    expect(titlesLabel(1284)).toBe("1,284 titles");
  });

  it("calls the media agent running only while it reports", () => {
    const now = Date.parse("2026-11-10T12:00:00Z");
    expect(agentOnline("2026-11-10T11:59:30Z", now)).toBe(true);
    expect(agentOnline("2026-11-10T11:50:00Z", now)).toBe(false);
    expect(agentOnline(null, now)).toBe(false);
  });

  it("gives the pairing command for IntraForge on this PC, always over HTTPS", () => {
    expect(pairCommand("pdc_sk_abc.def", "http://localhost:8443")).toBe('"C:\\IntraForge\\IntraForgeMediaAgent.exe" pair https://localhost:8443 pdc_sk_abc.def');
  });

  it("draws the same cover for the same title every time", () => {
    expect(drawnCover("Desert Wind")).toEqual(drawnCover("Desert Wind"));
    expect(drawnCover("Desert Wind")).not.toEqual(drawnCover("Iron Harbor"));
  });
});

describe("MovieCover", () => {
  it("draws a cover with the title and price when the title has no picture", () => {
    render(<MovieCover title={TITLE} />);
    expect(screen.getByText("Desert Wind")).toBeInTheDocument();
    expect(screen.getByText("50")).toBeInTheDocument();
    expect(document.querySelector("img")).toBeNull();
  });

  it("shows the shop's own picture when there is one, and the episode count of a series", () => {
    render(<MovieCover title={{ ...TITLE, has_cover: true, kind: "series", episodes: 30 }} />);
    expect(document.querySelector("img")?.getAttribute("src")).toBe("/api/v1/movie-titles/t1/cover/");
    expect(screen.getByText("30 EP")).toBeInTheDocument();
  });
});
