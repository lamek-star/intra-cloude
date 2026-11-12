"use client";

import { useEffect, useState } from "react";
import { Monitor, Moon, Sun } from "lucide-react";
import { applyTheme, saveTheme, storedTheme, type ThemeChoice } from "@/lib/theme";

const NEXT: Record<ThemeChoice, ThemeChoice> = { system: "light", light: "dark", dark: "system" };
const LABEL: Record<ThemeChoice, string> = { system: "Theme: like this computer", light: "Theme: light", dark: "Theme: dark" };

/** Light, dark, or like the computer; one press moves to the next. */
export function ThemeToggle({ className = "" }: { className?: string }) {
  const [choice, setChoice] = useState<ThemeChoice>("system");

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- read the stored choice once, in the browser
    setChoice(storedTheme());
    const media = window.matchMedia?.("(prefers-color-scheme: dark)");
    const follow = () => {
      if (storedTheme() === "system") applyTheme("system");
    };
    media?.addEventListener?.("change", follow);
    return () => media?.removeEventListener?.("change", follow);
  }, []);

  const Icon = choice === "dark" ? Moon : choice === "light" ? Sun : Monitor;
  return (
    <button
      type="button"
      className={className}
      title={LABEL[choice]}
      aria-label={`${LABEL[choice]}. Change theme`}
      onClick={() => {
        const next = NEXT[choice];
        setChoice(next);
        saveTheme(next);
      }}
    >
      <Icon aria-hidden="true" className="h-4 w-4" />
      <span>{LABEL[choice]}</span>
    </button>
  );
}
