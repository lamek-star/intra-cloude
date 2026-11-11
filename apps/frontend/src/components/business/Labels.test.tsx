import { describe, expect, it } from "vitest";
import { testSchema } from "@/lib/test-schema";
import { labelsHtml } from "./Labels";
import { labelFor, pictureLinks } from "./ProductDetail";

describe("labels", () => {
  it("a medicine's label carries its item number, name, generic name, pack, price, shelf and Rx", () => {
    const schema = testSchema({ pharmacy: true });
    const label = labelFor(
      schema,
      {
        id: "p1",
        "F:part.name": "Atrest 25mg Tablet",
        "F:part.generic_name": "Tetrabenazine 25 mg",
        "F:part.pack": "10 tablets",
        "F:part.manufacturer": "Centaur",
        "F:part.list_price": "120.0000",
        "F:part.storage_location": "Shelf B3",
        "F:part.prescription_required": true,
      },
      "NM-847249",
    );
    expect(label).toEqual({
      number: "NM-847249",
      name: "Atrest 25mg Tablet",
      details: ["Tetrabenazine 25 mg", "10 tablets · Centaur"],
      price: "120.00",
      location: "Shelf B3",
      flag: "Rx",
    });
    const html = labelsHtml([label], 2, "printer");
    expect(html.match(/class="label"/g)).toHaveLength(2);
    expect(html).toContain("<svg");
    expect(html).toContain("Shelf B3");
  });

  it("a spare part's label carries its part number and name", () => {
    const label = labelFor(testSchema(), { id: "p1", "F:part.name": "Oil Filter", "F:part.list_price": "15" }, "04465-0K290");
    expect(label).toMatchObject({ number: "04465-0K290", name: "Oil Filter", price: "15.00" });
  });

  it("escapes every value it prints", () => {
    const html = labelsHtml([{ number: "X<1>", name: "<script>alert(1)</script>", details: ['"a"'] }], 1, "sheet");
    expect(html).not.toContain("<script>alert");
    expect(html).toContain("&lt;script&gt;");
  });

  it("keeps only https picture links", () => {
    expect(pictureLinks("https://a.example/1.jpg, javascript:alert(1), http://b.example/2.jpg,https://c.example/3.png")).toEqual([
      "https://a.example/1.jpg",
      "https://c.example/3.png",
    ]);
  });
});
