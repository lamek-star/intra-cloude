import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

const { get, post } = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn() }));
vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return { ...actual, api: { ...actual.api, get, post }, ensureCsrfCookie: async () => {} };
});
vi.mock("@/components/ConfirmProvider", () => ({ useConfirm: () => async () => true }));
vi.mock("@/components/ShareSection", () => ({ ShareSection: () => null }));

import { ApiError } from "@/lib/api";
import BucketDetailClient from "./_client";

const file = (id: string, name: string, extra = {}) => ({
  id,
  bucket: "b1",
  folder: null,
  display_filename: name,
  size: 2048,
  mime_type: "text/plain",
  checksum_sha256: "x",
  status: "active",
  created_at: "2026-11-01T10:00:00Z",
  updated_at: "2026-11-02T10:00:00Z",
  ...extra,
});
const folder = { id: "f1", bucket: "b1", parent: null, name: "invoices", created_at: "2026-11-01T10:00:00Z", created_by: "u" };

beforeEach(() => {
  get.mockReset();
  post.mockReset();
});

describe("Bucket page", () => {
  it("lists folders above files and opens a folder with a path back", async () => {
    get.mockImplementation(async (path: string) => {
      if (path.startsWith("/buckets/b1/folders/?parent=f1")) return [];
      if (path.startsWith("/buckets/b1/folders/")) return [folder];
      if (path.includes("folder=f1")) return [file("2", "inv-001.pdf", { folder: "f1" })];
      return [file("1", "price-list.txt")];
    });
    render(<BucketDetailClient bucketId="b1" initialName="Shop files" projectId={null} />);
    // A clickable row is role="button" (TRow), so the folder is found by name, before the file.
    const folderRow = await screen.findByRole("button", { name: /invoices/ });
    const fileCell = screen.getByText("price-list.txt");
    expect(folderRow.compareDocumentPosition(fileCell) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(screen.getByText("text/plain")).toBeInTheDocument();

    await userEvent.click(folderRow);
    expect(await screen.findByText("inv-001.pdf")).toBeInTheDocument();
    const path = screen.getByRole("navigation", { name: "Folder path" });
    expect(within(path).getByRole("button", { name: "Shop files" })).toBeInTheDocument();
    expect(within(path).getByText("invoices")).toHaveAttribute("aria-current", "page");
  });

  it("restores from the Trash and explains a refusal", async () => {
    get.mockImplementation(async (path: string) => {
      if (path.startsWith("/buckets/b1/folders/")) return [];
      if (path.includes("status=deleted")) return [file("3", "old.txt", { status: "deleted" }), file("4", "evil.txt", { status: "deleted" })];
      return [];
    });
    post.mockImplementation(async (path: string) => {
      if (path === "/files/4/restore/") throw new ApiError(409, { detail: "A file named “evil.txt” is already in this folder." });
      return {};
    });
    render(<BucketDetailClient bucketId="b1" initialName="Shop files" projectId={null} />);
    await userEvent.click(await screen.findByRole("button", { name: "Trash" }));
    const restoreButtons = await screen.findAllByRole("button", { name: "Restore" });

    await userEvent.click(restoreButtons[0]);
    await waitFor(() => expect(screen.queryByText("old.txt")).not.toBeInTheDocument());
    expect(screen.getByText(/is back in the bucket/)).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Restore" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("already in this folder");
    expect(screen.getByText("evil.txt")).toBeInTheDocument();
  });

  it("says why the Trash is hidden from someone who may not delete", async () => {
    get.mockImplementation(async (path: string) => {
      if (path.includes("status=deleted")) throw new ApiError(403, {});
      if (path.startsWith("/buckets/b1/folders/")) return [];
      return [];
    });
    render(<BucketDetailClient bucketId="b1" initialName="Shop files" projectId={null} />);
    await userEvent.click(await screen.findByRole("button", { name: "Trash" }));
    expect(await screen.findByText("You can't see the Trash here")).toBeInTheDocument();
  });
});
