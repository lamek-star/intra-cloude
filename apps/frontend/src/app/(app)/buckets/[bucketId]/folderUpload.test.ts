import { afterEach, describe, expect, it, vi } from "vitest";
import { api, ApiError } from "@/lib/api";
import { folderOf, foldersToMake, uploadFolder } from "./folderUpload";

function picked(path: string): File {
  const f = new File(["x"], path.split("/").pop() ?? path);
  Object.defineProperty(f, "webkitRelativePath", { value: path });
  return f;
}

afterEach(() => vi.restoreAllMocks());

describe("folder upload", () => {
  it("finds each file's folder and drops .. parts", () => {
    expect(folderOf("Invoices/2026/march.pdf")).toEqual(["Invoices", "2026"]);
    expect(folderOf("note.txt")).toEqual([]);
    expect(folderOf("A/../../etc/passwd")).toEqual(["A", "etc"]);
  });

  it("makes each folder once, parents first", () => {
    expect(foldersToMake(["A/b/1.txt", "A/2.txt", "A/b/c/3.txt", "Z/4.txt"])).toEqual([
      ["A"],
      ["Z"],
      ["A", "b"],
      ["A", "b", "c"],
    ]);
  });

  it("reuses an existing folder, makes the missing one, and keeps going past a failed file", async () => {
    vi.spyOn(api, "get").mockImplementation(
      async (url: string) => (url.includes("?parent=") ? [] : [{ id: "f-top", name: "Shop" }]) as never,
    );
    const post = vi.spyOn(api, "post").mockResolvedValue({ id: "f-new", name: "2026" } as never);
    const sent: (string | null)[] = [];
    vi.spyOn(api, "postForm").mockImplementation(async (_url: string, form: FormData) => {
      if ((form.get("file") as File).name === "bad.txt") throw new ApiError(413, { detail: "Too large." });
      sent.push(form.get("folder") as string | null);
      return {} as never;
    });
    const progress: number[] = [];
    const result = await uploadFolder(
      "b1",
      null,
      [picked("Shop/a.txt"), picked("Shop/2026/b.txt"), picked("Shop/bad.txt")],
      (done) => progress.push(done),
    );
    expect(post).toHaveBeenCalledTimes(1);
    expect(post).toHaveBeenCalledWith("/buckets/b1/folders/", { name: "2026", parent_id: "f-top" });
    expect(sent).toEqual(["f-top", "f-new"]);
    expect(result.uploaded).toBe(2);
    expect(result.failed).toEqual([{ path: "Shop/bad.txt", reason: "Too large." }]);
    expect(progress).toEqual([0, 1, 2, 3]);
  });
});
