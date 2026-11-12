// Light, dark or the computer's own choice (globals.css: dark mode redefines the colour variables under
// data-theme="dark" on <html>). The choice is kept in this browser only.

export type ThemeChoice = "system" | "light" | "dark";
export const THEME_KEY = "intraforge-theme";

export function storedTheme(): ThemeChoice {
  try {
    const v = window.localStorage.getItem(THEME_KEY);
    return v === "light" || v === "dark" ? v : "system";
  } catch {
    return "system";
  }
}

export function effectiveTheme(choice: ThemeChoice): "light" | "dark" {
  if (choice !== "system") return choice;
  return typeof window !== "undefined" && window.matchMedia?.("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

export function applyTheme(choice: ThemeChoice): void {
  document.documentElement.dataset.theme = effectiveTheme(choice);
}

export function saveTheme(choice: ThemeChoice): void {
  try {
    if (choice === "system") window.localStorage.removeItem(THEME_KEY);
    else window.localStorage.setItem(THEME_KEY, choice);
  } catch {
    /* private window: the choice lasts for this page only */
  }
  applyTheme(choice);
}

/** Runs in <head> before the page paints, so a dark page never flashes white. Kept tiny and self-contained. */
export const THEME_BOOT_SCRIPT = `(function(){try{var v=localStorage.getItem("${THEME_KEY}");var d=v==="dark"||(v!=="light"&&window.matchMedia("(prefers-color-scheme: dark)").matches);document.documentElement.dataset.theme=d?"dark":"light"}catch(e){}})();`;
