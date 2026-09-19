import { useEffect, useRef } from "react";

const FOCUSABLE = 'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';

/** Shared dialog accessibility behavior (Unit 8): Escape-to-close, a
 * basic Tab/Shift+Tab focus trap within the panel, focus moved into the
 * dialog on open, and focus restored to whatever triggered it on close.
 * Used by Modal, ConfirmProvider, and CommandPalette -- three real
 * overlay implementations that all had the same gap independently,
 * rather than three copies of this logic. */
export function useDialogA11y(open: boolean, onClose: () => void, panelRef: React.RefObject<HTMLElement | null>) {
  const previouslyFocused = useRef<HTMLElement | null>(null);
  // The latest onClose, read at key-press time. It must NOT be an effect dependency: a parent
  // that re-renders (e.g. on every keystroke in a form whose state it owns) passes a new function
  // each time, and re-running this effect would move focus to the first control on every render
  // -- typing a space would then "press" the Close button.
  const onCloseRef = useRef(onClose);
  useEffect(() => {
    onCloseRef.current = onClose;
  });

  useEffect(() => {
    if (!open) return;
    previouslyFocused.current = document.activeElement as HTMLElement | null;
    const panel = panelRef.current;
    const firstFocusable = panel?.querySelector<HTMLElement>(FOCUSABLE);
    (firstFocusable ?? panel)?.focus();

    function onKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") {
        e.stopPropagation();
        onCloseRef.current();
        return;
      }
      if (e.key !== "Tab" || !panel) return;
      const focusable = Array.from(panel.querySelectorAll<HTMLElement>(FOCUSABLE));
      if (focusable.length === 0) return;
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault();
        last.focus();
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault();
        first.focus();
      }
    }
    document.addEventListener("keydown", onKeyDown, true);
    return () => {
      document.removeEventListener("keydown", onKeyDown, true);
      previouslyFocused.current?.focus?.();
    };
  }, [open, panelRef]);
}
