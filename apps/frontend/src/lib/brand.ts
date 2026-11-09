/** The owner's copyright line, shown with the version in the app and in Setup (scripts/shop-kit/setup-stub/Copyright.cs). */
export const COPYRIGHT = "© 2026 lamek-rusoom";

/** "IntraForge 1.5.2 · © 2026 lamek-rusoom" -- the version without its build suffix (1.5.2-ce9b03c85 -> 1.5.2). */
export function versionLine(version: string | null | undefined): string {
  const shown = version ? version.split("-")[0] : "";
  return `IntraForge${shown ? ` ${shown}` : ""} · ${COPYRIGHT}`;
}
