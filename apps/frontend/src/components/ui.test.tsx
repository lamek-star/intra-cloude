import { describe, expect, it, vi } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { Button, CopyButton, Modal, Table, TRow, Td } from "./ui";

// DESIGN.md §10: a clickable table row must implement role="button",
// tabIndex={0}, and Enter/Space handling together -- never just one of
// the four. This is the invariant that pass established, not styling.
describe("TRow", () => {
  it("is not interactive when it has no onClick", () => {
    render(
      <Table>
        <tbody>
          <TRow>
            <Td>plain row</Td>
          </TRow>
        </tbody>
      </Table>
    );
    const row = screen.getByText("plain row").closest("tr")!;
    expect(row).not.toHaveAttribute("role");
    expect(row).not.toHaveAttribute("tabindex");
  });

  it("fires onClick via mouse click, Enter, and Space, and exposes role=button/tabIndex=0", () => {
    const onClick = vi.fn();
    render(
      <Table>
        <tbody>
          <TRow onClick={onClick}>
            <Td>row one</Td>
          </TRow>
        </tbody>
      </Table>
    );
    const row = screen.getByText("row one").closest("tr")!;
    expect(row).toHaveAttribute("role", "button");
    expect(row).toHaveAttribute("tabindex", "0");

    fireEvent.click(row);
    fireEvent.keyDown(row, { key: "Enter" });
    fireEvent.keyDown(row, { key: " " });
    fireEvent.keyDown(row, { key: "a" });

    expect(onClick).toHaveBeenCalledTimes(3);
  });
});

describe("Button", () => {
  it("is disabled and inert when the disabled prop is set", async () => {
    const onClick = vi.fn();
    const user = userEvent.setup();
    render(
      <Button disabled onClick={onClick}>
        Save
      </Button>
    );
    const button = screen.getByRole("button", { name: "Save" });
    expect(button).toBeDisabled();
    await user.click(button);
    expect(onClick).not.toHaveBeenCalled();
  });
});

describe("CopyButton", () => {
  it("writes the value to the clipboard and shows Copied feedback", async () => {
    const writeText = vi.spyOn(navigator.clipboard, "writeText").mockResolvedValue(undefined);
    const user = userEvent.setup();

    render(<CopyButton value="pdc_sk_secret123" label="Copy key" />);
    await user.click(screen.getByRole("button", { name: "Copy key" }));

    expect(writeText).toHaveBeenCalledWith("pdc_sk_secret123");
    expect(await screen.findByText("Copied")).toBeInTheDocument();
  });
});

// DESIGN.md §14: modals trap focus, close on Escape, and restore focus
// to their trigger -- the useDialogA11y invariant shared by every
// overlay in the app.
describe("Modal", () => {
  function Harness() {
    const [open, setOpen] = useState(false);
    return (
      <div>
        <button onClick={() => setOpen(true)}>Open dialog</button>
        <Modal open={open} onClose={() => setOpen(false)} title="Delete bucket">
          <button>Confirm</button>
        </Modal>
      </div>
    );
  }

  it("moves focus into the panel on open, and restores it to the trigger on Escape", async () => {
    const user = userEvent.setup();
    render(<Harness />);

    const trigger = screen.getByRole("button", { name: "Open dialog" });
    await user.click(trigger);

    const dialog = await screen.findByRole("dialog", { name: "Delete bucket" });
    await waitFor(() => expect(dialog.contains(document.activeElement)).toBe(true));

    fireEvent.keyDown(document, { key: "Escape" });

    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    await waitFor(() => expect(document.activeElement).toBe(trigger));
  });
});

// Regression: a parent that owns the form state re-renders on every keystroke and hands Modal a
// new onClose each time. That must not move focus (typing a space then pressed the Close button
// and dismissed the dialog).
describe("Modal focus stability", () => {
  it("keeps focus in the field being typed in when the parent re-renders with a new onClose", async () => {
    function Parent() {
      const [name, setName] = useState("");
      return (
        <Modal open onClose={() => setName("closed")} title="Name it">
          <input aria-label="Name" value={name} onChange={(e) => setName(e.target.value)} />
        </Modal>
      );
    }
    const user = userEvent.setup();
    render(<Parent />);
    const input = screen.getByLabelText("Name");
    await user.click(input);
    await user.type(input, "My Shop");
    expect(input).toHaveValue("My Shop");
    expect(input).toHaveFocus();
  });

  it("still closes on Escape using the latest onClose", async () => {
    const first = vi.fn();
    const second = vi.fn();
    const { rerender } = render(<Modal open onClose={first} title="T"><button>ok</button></Modal>);
    rerender(<Modal open onClose={second} title="T"><button>ok</button></Modal>);
    await userEvent.setup().keyboard("{Escape}");
    expect(first).not.toHaveBeenCalled();
    expect(second).toHaveBeenCalledTimes(1);
  });
});
