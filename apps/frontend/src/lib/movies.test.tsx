import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { agentOnline, copyProgress, drawnCover, formatBytes, pairCommand, partsLabel, qrDataUrl, titlesLabel, type MovieTitle, type Sale } from "./movies";
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

describe("the counter sale helpers", () => {
  const line = (size: number, status: Sale["lines"][number]["copy_status"], copied = 0) => ({
    id: `l${size}`,
    title: "T",
    title_id: null,
    category: "Action",
    kind: "movie" as const,
    price: 50,
    size_bytes: size,
    copy_status: status,
    copied_bytes: copied,
    copy_message: "",
    free: false,
  });
  const sale = (lines: Sale["lines"]): Sale => ({
    id: "s1",
    shop: "shop-1",
    number: "MOV-1",
    status: "paid",
    method: "cash",
    customer_name: "",
    total: 100,
    destination: "E:\\",
    folder: "Shop",
    pay: null,
    receipt_number: "",
    paid_at: null,
    created_at: "2026-11-10T10:00:00Z",
    lines,
    customer: null,
    use_points: false,
    points_used: 0,
    discount: 0,
  });

  it("measures copying by bytes, counting a copied title in full", () => {
    expect(copyProgress(sale([line(300, "copied", 0), line(100, "copying", 50)]))).toBeCloseTo(350 / 400);
    expect(copyProgress(sale([line(100, "waiting")]))).toBe(0);
    expect(copyProgress(sale([line(100, "copying", 999)]))).toBe(1);
  });

  it("uses Pay's QR data URL as it is and encodes a bare SVG, including non-ASCII text", () => {
    expect(qrDataUrl("data:image/svg+xml;base64,PHN2Zy8+")).toBe("data:image/svg+xml;base64,PHN2Zy8+");
    const url = qrDataUrl("<svg><title>ብር</title></svg>") ?? "";
    expect(url.startsWith("data:image/svg+xml;base64,")).toBe(true);
    const decoded = new TextDecoder().decode(Uint8Array.from(atob(url.split(",")[1]), (c) => c.charCodeAt(0)));
    expect(decoded).toBe("<svg><title>ብር</title></svg>");
  });

  it("gives no picture for anything that is not an SVG", () => {
    expect(qrDataUrl("javascript:alert(1)")).toBeNull();
    expect(qrDataUrl("data:text/html;base64,PHNjcmlwdD4=")).toBeNull();
    expect(qrDataUrl('data:image/svg+xml;base64,PHN2Zy8+" onerror="x')).toBeNull();
  });
});

describe("music and series labels", () => {
  it("says episodes for a series, songs for an album, and nothing for a film", () => {
    expect(partsLabel({ kind: "series", episodes: 6 })).toBe("6 episodes");
    expect(partsLabel({ kind: "series", episodes: 6 }, true)).toBe("6 ep.");
    expect(partsLabel({ kind: "album", episodes: 1 })).toBe("1 song");
    expect(partsLabel({ kind: "album", episodes: 14 })).toBe("14 songs");
    expect(partsLabel({ kind: "music", episodes: 1 })).toBe("Song");
    expect(partsLabel({ kind: "movie", episodes: 1 })).toBeNull();
  });
});
