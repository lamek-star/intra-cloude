/**
 * Validates a `?next=` return-to path before ever navigating to it.
 * Must be a same-origin, absolute-from-root path -- never a scheme-
 * relative ("//evil.example.com"), absolute ("https://evil.example.com"),
 * or backslash-prefixed ("\\evil.example.com", which some browsers still
 * treat as scheme-relative) URL. This is the one thing standing between
 * "/login?next=..." and being an open redirect.
 */
export function isSafeNextPath(value: string | null | undefined): value is string {
  if (!value) return false;
  if (!value.startsWith("/")) return false;
  if (value.startsWith("//")) return false;
  if (value.startsWith("/\\")) return false;
  if (value.includes("://")) return false;
  return true;
}
