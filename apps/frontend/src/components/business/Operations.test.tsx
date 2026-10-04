import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

const { get, postIdempotent } = vi.hoisted(() => ({ get: vi.fn(), postIdempotent: vi.fn() }));
vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return { ...actual, api: { ...actual.api, get, postIdempotent } };
});

vi.mock("./BusinessApp", async () => {
  const { testSchema } = await import("@/lib/test-schema");
  const schema = testSchema();
  return { useBusiness: () => ({ schema, instance: { id: "app1", label: "My Shop", project: "p1" } }) };
});

vi.mock("./hooks", () => {
  const options = {
    warehouse: [{ id: "w1", label: "Main Warehouse", row: {} }],
    supplier: [{ id: "s1", label: "Demo Supplier A", row: {} }],
    customer: [{ id: "c1", label: "Demo Retail Customer", row: {} }],
  } as Record<string, { id: string; label: string; row: Record<string, unknown> }[]>;
  return {
    useOptions: (model: string) => ({ options: options[model] ?? [], loading: false, error: false }),
    useNames: () => ({}),
  };
});

// A product picker reduced to one button: the search behavior is the server's and is tested there.
vi.mock("./ProductPicker", () => ({
  default: ({ label, value, onChange }: { label: string; value: unknown; onChange: (p: unknown) => void }) => (
    <button
      type="button"
      onClick={() =>
        onChange({ id: "p-oil", name: "Oil Filter", row: { "F:part.list_price": "15.0000" } })
      }
    >
      {value ? `${label}: chosen` : `Pick ${label}`}
    </button>
  ),
}));

import { ApiError } from "@/lib/api";
import ReceiveStock from "./ReceiveStock";
import SellStock from "./SellStock";

function serveInventory(onHand: string) {
  get.mockImplementation(async (path: string) => {
    if (path.includes("/app-models/M:inventory/records/")) {
      return { count: 1, limit: 1, offset: 0, results: [{ id: "inv1", "F:inventory.quantity_on_hand": onHand }] };
    }
    throw new Error(`unexpected GET ${path}`);
  });
}

beforeEach(() => {
  get.mockReset();
  postIdempotent.mockReset();
});

async function fillReceive(user: ReturnType<typeof userEvent.setup>, quantity = "100") {
  await user.click(screen.getByRole("button", { name: /Pick Product/ }));
  await user.selectOptions(screen.getByLabelText("Warehouse"), "w1");
  await user.type(screen.getByLabelText("Quantity"), quantity);
}

describe("Receive stock", () => {
  it("asks for what is missing and posts nothing", async () => {
    const user = userEvent.setup();
    render(<ReceiveStock />);
    await user.click(screen.getByRole("button", { name: "Confirm receive" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Choose the product");
    expect(screen.getByRole("alert")).toHaveTextContent("Choose the warehouse");
    expect(screen.getByRole("alert")).toHaveTextContent("whole quantity");
    expect(postIdempotent).not.toHaveBeenCalled();
  });

  it("states only an intent, posts it once with an idempotency key, and reads the balance back", async () => {
    serveInventory("100");
    postIdempotent.mockResolvedValue({
      results: [{ operation: 0, model: "M:stock_movement", ref: null, record: { id: "m1", "F:stock_movement.quantity_delta": 100 } }],
    });
    const user = userEvent.setup();
    render(<ReceiveStock />);
    await fillReceive(user);
    await user.click(screen.getByRole("button", { name: "Confirm receive" }));

    expect(await screen.findByText("Stock received")).toBeInTheDocument();
    const [path, body, key] = postIdempotent.mock.calls[0];
    expect(path).toBe("/app-instances/i1/operations/receive/"); // the controlled operation, never the record API
    expect(key).toMatch(/^[0-9a-f-]{36}$/);
    expect(body).toMatchObject({ part: "p-oil", warehouse: "w1", quantity: 100 });
    // the browser states neither a balance nor a stock movement: the server builds the movement and the ledger decides
    expect(JSON.stringify(body)).not.toMatch(/quantity_on_hand|quantity_delta|movement_type|operations/);
    expect(screen.getByTestId("on-hand-now")).toHaveTextContent("100"); // read back from the server
  });

  it("with a supplier names the supplier and the unit cost (the server records the purchase order)", async () => {
    serveInventory("10");
    postIdempotent.mockResolvedValue({ results: [] });
    const user = userEvent.setup();
    render(<ReceiveStock />);
    await fillReceive(user, "10");
    await user.selectOptions(screen.getByLabelText("Supplier"), "s1");
    await user.type(screen.getByLabelText("Unit cost"), "2.50");
    await user.click(screen.getByRole("button", { name: "Confirm receive" }));
    await screen.findByText("Stock received");
    expect(postIdempotent.mock.calls[0][1]).toMatchObject({ supplier: "s1", unit_cost: "2.50", quantity: 10 });
  });

  it("on failure shows a plain message, keeps the form, and a retry reuses the same key", async () => {
    serveInventory("100");
    postIdempotent.mockRejectedValueOnce(new ApiError(500, "Traceback"));
    postIdempotent.mockResolvedValueOnce({ results: [] });
    const user = userEvent.setup();
    render(<ReceiveStock />);
    await fillReceive(user);
    await user.click(screen.getByRole("button", { name: "Confirm receive" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Nothing was changed");
    expect(screen.getByLabelText("Quantity")).toHaveValue("100"); // nothing lost

    await user.click(screen.getByRole("button", { name: "Confirm receive" }));
    await screen.findByText("Stock received");
    expect(postIdempotent.mock.calls[1][2]).toBe(postIdempotent.mock.calls[0][2]); // same key -> replay, not a second receipt
  });

  it("editing after a failure starts a new operation with a new key", async () => {
    serveInventory("50");
    postIdempotent.mockRejectedValueOnce(new ApiError(500, "x"));
    postIdempotent.mockResolvedValueOnce({ results: [] });
    const user = userEvent.setup();
    render(<ReceiveStock />);
    await fillReceive(user);
    await user.click(screen.getByRole("button", { name: "Confirm receive" }));
    await screen.findByRole("alert");
    await user.clear(screen.getByLabelText("Quantity"));
    await user.type(screen.getByLabelText("Quantity"), "50");
    await user.click(screen.getByRole("button", { name: "Confirm receive" }));
    await screen.findByText("Stock received");
    expect(postIdempotent.mock.calls[1][2]).not.toBe(postIdempotent.mock.calls[0][2]);
  });
});

async function fillSale(user: ReturnType<typeof userEvent.setup>, quantity = "5") {
  await user.selectOptions(screen.getByLabelText("Customer"), "c1");
  await user.click(screen.getByRole("button", { name: /Pick Product/ }));
  await user.selectOptions(screen.getByLabelText("Warehouse"), "w1");
  await user.type(screen.getByLabelText("Quantity"), quantity);
}

describe("Sell stock", () => {
  it("prefills the price from the product and asks for anything missing", async () => {
    const user = userEvent.setup();
    render(<SellStock />);
    await user.click(screen.getByRole("button", { name: "Confirm sale" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Choose the customer");
    expect(postIdempotent).not.toHaveBeenCalled();
    await user.click(screen.getByRole("button", { name: /Pick Product/ }));
    expect(screen.getByLabelText("Unit price")).toHaveValue("15.00");
  });

  it("posts one sale intent (the server records order, lines, movements and invoice) and reads the stock back", async () => {
    serveInventory("95");
    postIdempotent.mockResolvedValue({ results: [{ operation: 0, model: "M:sales_order", ref: "order", record: { id: "o1" } }] });
    const user = userEvent.setup();
    render(<SellStock />);
    await fillSale(user);
    expect(screen.getByText("75.00")).toBeInTheDocument(); // total is money on the document, not stock
    await user.click(screen.getByRole("button", { name: "Confirm sale" }));

    expect(await screen.findByText("Sale complete")).toBeInTheDocument();
    const [path, body] = postIdempotent.mock.calls[0];
    expect(path).toBe("/app-instances/i1/operations/sell/");
    expect(body).toMatchObject({ customer: "c1", lines: [{ part: "p-oil", warehouse: "w1", quantity: 5, unit_price: "15.00" }] });
    expect(body.invoice_number).toMatch(/^INV-\d{8}-[0-9A-Z]{5}$/);
    expect(JSON.stringify(body)).not.toMatch(/quantity_delta|movement_type|operations|quantity_on_hand/);
    expect(screen.getByTestId("on-hand-after-sale")).toHaveTextContent("95");
    expect(screen.getByRole("link", { name: "Open sales document" })).toHaveAttribute("href", "/apps/app1/sales/o1");
  });

  it("explains an oversell in plain words and reports no sale", async () => {
    postIdempotent.mockRejectedValue(
      new ApiError(400, { detail: "this quantity ledger balance would go negative (-1)", operation: 2 }),
    );
    const user = userEvent.setup();
    render(<SellStock />);
    await fillSale(user, "6");
    await user.click(screen.getByRole("button", { name: "Confirm sale" }));
    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("not enough stock");
    expect(alert).toHaveTextContent("Nothing was changed");
    expect(screen.queryByText("Sale complete")).not.toBeInTheDocument();
  });

  it("a retry reuses the key and invoice number; an edit starts a fresh sale", async () => {
    serveInventory("95");
    postIdempotent.mockRejectedValueOnce(new ApiError(500, "x"));
    postIdempotent.mockResolvedValueOnce({ results: [{ operation: 0, model: "M:sales_order", ref: "order", record: { id: "o1" } }] });
    postIdempotent.mockRejectedValueOnce(new ApiError(500, "x"));
    const user = userEvent.setup();
    const { unmount } = render(<SellStock />);
    await fillSale(user);
    await user.click(screen.getByRole("button", { name: "Confirm sale" }));
    await screen.findByRole("alert");
    await user.click(screen.getByRole("button", { name: "Confirm sale" }));
    await screen.findByText("Sale complete");
    const [first, second] = postIdempotent.mock.calls;
    expect(second[2]).toBe(first[2]);
    const invoice = (call: unknown[]) => (call[1] as { invoice_number: string }).invoice_number;
    expect(invoice(second)).toBe(invoice(first));
    unmount();

    // fresh form: fail, edit, submit -> a different key and invoice number
    serveInventory("95");
    postIdempotent.mockReset();
    postIdempotent.mockRejectedValueOnce(new ApiError(500, "x"));
    postIdempotent.mockRejectedValueOnce(new ApiError(500, "x"));
    render(<SellStock />);
    await fillSale(user);
    await user.click(screen.getByRole("button", { name: "Confirm sale" }));
    await waitFor(() => expect(postIdempotent).toHaveBeenCalledTimes(1));
    await screen.findByRole("alert");
    await user.clear(screen.getByLabelText("Quantity"));
    await user.type(screen.getByLabelText("Quantity"), "4");
    await user.click(screen.getByRole("button", { name: "Confirm sale" }));
    await waitFor(() => expect(postIdempotent).toHaveBeenCalledTimes(2));
    expect(postIdempotent.mock.calls[1][2]).not.toBe(postIdempotent.mock.calls[0][2]);
    expect(invoice(postIdempotent.mock.calls[1])).not.toBe(invoice(postIdempotent.mock.calls[0]));
  });
});
