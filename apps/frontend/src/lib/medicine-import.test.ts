import { describe, expect, it } from "vitest";
import { canEncode128, code128Modules, code128Svg, code128Values, CODE128_PATTERNS } from "./barcode";
import { CsvStream, itemNumberFrom, medicineFromRow, parseRupees, readMedicines, sellingPrice } from "./medicine-import";
import { editionOf } from "./business";
import { testSchema } from "./test-schema";
import { importBatches, medicineKey } from "@/components/business/MedicineImport";

const HEADER =
  "disease_name,disease_url,med_name,med_url,final_price,price,prescription_required,drug_varient,drug_manufacturer," +
  "drug_manufacturer_origin,drug_content,generic_name,img_urls";
const ATREST =
  'ADHD (7),https://www.netmeds.com/prescriptions/adhd,"Atrest 25mg Tablet 10\'S",https://www.netmeds.com/prescriptions/atrest-25mg-tablet-10-s,' +
  '₹335.68,MRP ₹381.46  Save 12 %,Rx required,*10 Tablet(s) in a Strip,* Mkt: Centaur Pharmaceuticals Pvt Ltd,' +
  '* Country of Origin: India,"INTRODUCTION ""long"" text,\nover lines",Generic Name  Tetrabenazine 25 mg,' +
  '"https://www.netmeds.com/images/product-v1/600x600/847249/atrest_0.jpg, https://www.netmeds.com/images/product-v1/600x600/847249/atrest_1.jpg"';

function rows(text: string, chunk = 7): string[][] {
  const out: string[][] = [];
  const csv = new CsvStream();
  for (let i = 0; i < text.length; i += chunk) csv.push(text.slice(i, i + chunk), (r) => out.push(r));
  csv.end((r) => out.push(r));
  return out;
}

describe("reading a medicines catalogue", () => {
  it("splits CSV with quotes, doubled quotes and line breaks inside quotes, whatever the chunk size", () => {
    for (const chunk of [1, 3, 7, 1000]) {
      const parsed = rows(`${HEADER}\r\n${ATREST}\n`, chunk);
      expect(parsed).toHaveLength(2);
      expect(parsed[1]).toHaveLength(13);
      expect(parsed[1][10]).toBe('INTRODUCTION "long" text,\nover lines');
    }
  });

  it("keeps the facts and drops the catalogue's own words", () => {
    const [h, r] = rows(`${HEADER}\n${ATREST}\n`);
    const m = medicineFromRow(Object.fromEntries(h.map((k, i) => [k, r[i]])))!;
    expect(m).toMatchObject({
      name: "Atrest 25mg Tablet 10'S",
      generic_name: "Tetrabenazine 25 mg",
      pack: "10 Tablet(s) in a Strip",
      manufacturer: "Centaur Pharmaceuticals Pvt Ltd",
      country_of_origin: "India",
      prescription_required: true,
      used_for: ["ADHD"],
      reference_price: "335.68",
      item_number: "NM-847249",
    });
    expect(m.image_links).toHaveLength(2);
    expect(JSON.stringify(m)).not.toContain("INTRODUCTION");
  });

  it("reads prices, item numbers and origin the way the catalogue writes them", () => {
    expect(parseRupees("MRP  ₹ 1,275.15")).toBe("1275.15");
    expect(parseRupees("")).toBeNull();
    expect(itemNumberFrom([], "https://example.com/x")).toBeNull();
    expect(medicineFromRow({ med_name: "X", drug_manufacturer_origin: "* Country of Origin: NA" })!.country_of_origin).toBe("");
    expect(medicineFromRow({ med_name: "  " })).toBeNull();
    expect(medicineFromRow({ med_name: "X", img_urls: "javascript:alert(1), http://plain.example/a.jpg" })!.image_links).toEqual([]);
  });

  it("merges a medicine listed under several diseases into one", async () => {
    const second = ATREST.replace("ADHD (7)", "Huntington Disease (3)");
    const file = new Blob([`${HEADER}\n${ATREST}\n${second}\n`]);
    const { medicines, rows: count } = await readMedicines(file);
    expect(count).toBe(2);
    expect(medicines).toHaveLength(1);
    expect(medicines[0].used_for).toEqual(["ADHD", "Huntington Disease"]);
  });

  it("refuses a file that is not a medicines catalogue", async () => {
    await expect(readMedicines(new Blob(["a,b\n1,2\n"]))).rejects.toThrow(/not a medicines catalogue/);
  });

  it("sets a selling price only when a rate is given", () => {
    expect(sellingPrice("335.68", null)).toBeNull();
    expect(sellingPrice("335.68", 0.18)).toBe("60.42");
    expect(sellingPrice(null, 0.18)).toBeNull();
  });
});

describe("importing into the Pharmacy", () => {
  const schema = testSchema({ pharmacy: true });
  const none = () => ({ numbers: new Set<string>(), keys: new Set<string>() });
  const medicine = (n: number) => medicineFromRow({ med_name: `Medicine ${n}`, img_urls: `https://x.example/product-v1/600x600/${1000 + n}/a.jpg` })!;

  it("recognises the Pharmacy edition by its fields", () => {
    expect(editionOf(schema)).toBe("pharmacy");
    expect(editionOf(testSchema())).toBe("spare_parts");
  });

  it("sends at most 100 operations per transaction, each medicine with its item number", () => {
    const { batches } = importBatches(schema, Array.from({ length: 120 }, (_, i) => medicine(i)), none(), 0.18);
    expect(batches.every((b) => b.length <= 100)).toBe(true);
    expect(batches.flat().filter((op) => op.model === "M:part")).toHaveLength(120);
    const [first, second] = batches[0];
    expect(second.data["R:part_number_part"]).toEqual({ $ref: first.ref });
    expect(second.data["F:part_number.number"]).toBe("NM-1000");
  });

  it("leaves medicines the Pharmacy already has as they are", () => {
    const { batches, skipped } = importBatches(
      schema,
      [medicine(1), medicine(2), medicine(1)],
      { numbers: new Set(["NM-1001"]), keys: new Set() },
      null,
    );
    expect(skipped).toBe(2);
    expect(batches.flat().filter((op) => op.model === "M:part")).toHaveLength(1);
  });

  it("recognises a medicine without an item number by its source link, so a repeated import adds no copy", () => {
    const plain = medicineFromRow({ med_name: "No Picture Syrup", med_url: "https://x.example/no-picture-syrup" })!;
    expect(plain.item_number).toBeNull();
    const again = importBatches(schema, [plain], { numbers: new Set(), keys: new Set([medicineKey(plain.source_url, plain.name)]) }, null);
    expect(again.skipped).toBe(1);
    expect(again.batches).toHaveLength(0);
    const byName = medicineFromRow({ med_name: "Plain Name" })!;
    expect(importBatches(schema, [byName], { numbers: new Set(), keys: new Set(["plain name"]) }, null).skipped).toBe(1);
  });
});

describe("barcodes", () => {
  it("has a complete, consistent Code 128 table", () => {
    expect(CODE128_PATTERNS).toHaveLength(107);
    expect(new Set(CODE128_PATTERNS).size).toBe(107);
    for (const p of CODE128_PATTERNS.slice(0, 106)) expect([...p].reduce((a, b) => a + Number(b), 0)).toBe(11);
  });

  it("starts with set B, ends with the stop code and carries the checksum", () => {
    // "PJJ123C": 104 + 48*1 + 42*2 + 42*3 + 17*4 + 18*5 + 19*6 + 35*7 = 879; 879 mod 103 = 55.
    expect(code128Values("PJJ123C")).toEqual([104, 48, 42, 42, 17, 18, 19, 35, 55, 106]);
    expect(code128Modules("A").reduce((a, b) => a + b, 0)).toBe(11 * 3 + 13); // start B, "A", checksum, stop
  });

  it("refuses what a barcode cannot hold and escapes what it draws", () => {
    expect(canEncode128("NM-847249")).toBe(true);
    expect(canEncode128("ДК-1")).toBe(false);
    expect(code128Svg('A"<')).toContain("Barcode A&quot;&lt;");
  });
});
