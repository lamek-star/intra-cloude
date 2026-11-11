import { beforeEach, describe, expect, it } from "vitest";
import { invoiceHtml, type InvoiceData } from "./invoice";
import { labelPages } from "./label-image";
import { defaultShopDetails, loadShopDetails, saveShopDetails, withCurrency } from "./shop-details";
import { labelsHtml, numberCaption } from "@/components/business/Labels";

const DATA: InvoiceData = {
  number: "INV-20261110-0042",
  date: "10 Nov 2026",
  payment: "unpaid",
  customer: "Asmara Garage",
  lines: [
    { number: "04465-0K290", name: "Brake pads, front", quantity: "2", unitPrice: "48.00", total: "96.00" },
    { number: "", name: "Oil filter <genuine>", quantity: "1", unitPrice: "6.50", total: "6.50" },
  ],
  total: "102.50",
  amountDue: "102.50",
  numberCaption: "Part No.",
  productWord: "Product",
  printedAt: "10 Nov 2026, 15:20",
};
const SHOP = { name: "Lamek Spare Parts", address: "Harnet Ave 12, Asmara", phone: "+291 1 123456", taxId: "", currency: "ERN", footer: "Thank you!" };

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

describe("the printed invoice", () => {
  it("an A4 invoice carries the shop, the invoice number, every line with its part number, and the amount due", () => {
    const html = invoiceHtml(DATA, "a4", SHOP);
    for (const text of ["Lamek Spare Parts", "Harnet Ave 12, Asmara", "Tel. +291 1 123456", "INV-20261110-0042", "Asmara Garage", "04465-0K290", "Part No.", "102.50 ERN", "Thank you!"]) {
      expect(html).toContain(text);
    }
    expect(html).not.toContain("Tax no."); // empty details are left out
    expect(html).toContain("<svg"); // the invoice number as a barcode
  });

  it("a receipt is the same sale on narrow paper", () => {
    const html = invoiceHtml(DATA, "receipt80", SHOP);
    expect(html).toContain("size:80mm auto");
    expect(html).toContain("2 × 48.00");
    expect(html).toContain("AMOUNT DUE");
    expect(invoiceHtml(DATA, "receipt58", SHOP)).toContain("width:58mm");
  });

  it("escapes every value it prints", () => {
    const html = invoiceHtml({ ...DATA, customer: '<img src=x onerror="alert(1)">' }, "a4", { ...SHOP, name: "<b>shop</b>" });
    expect(html).not.toContain("<img src=x");
    expect(html).not.toContain("<b>shop</b>");
    expect(html).toContain("Oil filter &lt;genuine&gt;");
  });

  it("an order that has no invoice yet prints as a sales order with its total", () => {
    const html = invoiceHtml({ ...DATA, number: "", payment: "" }, "a4", SHOP);
    expect(html).toContain("SALES ORDER");
    expect(html).not.toContain("Invoice no.");
  });
});

describe("the shop's details", () => {
  beforeEach(() => {
    Object.defineProperty(window, "localStorage", { value: memoryStorage(), configurable: true });
  });

  it("start from the app's name, and are remembered per app on this computer", () => {
    expect(loadShopDetails("a1", "Spare Parts")).toEqual(defaultShopDetails("Spare Parts"));
    saveShopDetails("a1", SHOP);
    expect(loadShopDetails("a1", "Spare Parts")).toEqual(SHOP);
    expect(loadShopDetails("a2", "Pharmacy").name).toBe("Pharmacy");
  });

  it("puts the currency after an amount only when one is set", () => {
    expect(withCurrency("10.00", "ERN")).toBe("10.00 ERN");
    expect(withCurrency("10.00", " ")).toBe("10.00");
  });
});

describe("labels", () => {
  it("show the shop's name, the product name and the captioned part number", () => {
    const html = labelsHtml([{ number: "04465-0K290", name: "Brake pads", details: [] }], 1, "printer", { shop: "Lamek Spare Parts", numberCaption: "Part No." });
    expect(html).toContain("LAMEK SPARE PARTS");
    expect(html).toContain("Brake pads");
    expect(html).toContain('<span class="caption">Part No.</span> 04465-0K290');
  });

  it("caption the number the way each edition names it", () => {
    expect(numberCaption("Part number")).toBe("Part No.");
    expect(numberCaption("Item number")).toBe("Item No.");
  });

  it("make one picture per label for a label printer, and one per 24 labels on A4", () => {
    expect(labelPages(3, "printer")).toBe(3);
    expect(labelPages(24, "sheet")).toBe(1);
    expect(labelPages(25, "sheet")).toBe(2);
    expect(labelPages(0, "sheet")).toBe(0);
  });
});
