# Chapter 3 — The frontend — Adding a screen

Topic for: software engineers. Source: IntraForge Engineering Handbook, Chapter 3 — The frontend.

1. Create `src/app/(app)/<route>/page.tsx` as a client component; use `PageHeader` and the kit.
2. Add the response type to `lib/api.ts` and a query hook (or `useQuery` inline) keyed by the resource id.
3. Handle loading (`PageLoading`), empty (`EmptyState`), error (`ErrorBanner`) and 403 states.
4. Add it to the sidebar (`AppShell.tsx`) or the command palette (`CommandPalette.tsx`) if people need to find it.
5. Add a Vitest test for any logic in `lib/`, and a Playwright spec for a whole workflow.
