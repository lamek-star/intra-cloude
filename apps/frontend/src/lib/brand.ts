/** The owner's copyright line, shown with the version in the app and in Setup (scripts/shop-kit/setup-stub/Copyright.cs). */
export const COPYRIGHT = "© 2026 lamek-rusoom";

/** "IntraForge 1.5.2" -- the version without its build suffix (1.5.2-ce9b03c85 -> 1.5.2). */
export function versionLabel(version: string | null | undefined): string {
  const shown = version ? version.split("-")[0] : "";
  return `IntraForge${shown ? ` ${shown}` : ""}`;
}

/** "IntraForge 1.5.2 · © 2026 lamek-rusoom", for places with room for one line. */
export function versionLine(version: string | null | undefined): string {
  return `${versionLabel(version)} · ${COPYRIGHT}`;
}
