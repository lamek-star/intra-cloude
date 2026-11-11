# Primitives check

Two files to apply to IntraForge's frontend (`apps/frontend`), in this order:

1. **[token-fixes.patch](token-fixes.patch)**: the WCAG AA token fixes.
   - It replaces the `@theme` block in `src/app/globals.css` with [../tokens.css](../tokens.css).
   - It updates the matching classes in `src/components/ui.tsx`, `AppShell.tsx` and `CommandPalette.tsx`.
   - It was made against `feature/app-platform` `6fc50c7`. Check it applies to the kit's newer source (`dbf44f593`):
     `git apply --check token-fixes.patch`.
2. **[design-page.tsx](design-page.tsx)**: copy to `src/app/design/page.tsx`.
   - It renders every shipped primitive in every state.
   - It needs no sign-in and calls no API. Gate it to development builds or remove it before a release.

Also update DESIGN.md §2.1, §2.3, §8 and §9 with the values in `../tokens.json` → `_changed`, so the doc and the code
agree again.

## What was checked (2026-11-03)

These checks ran in a scratch copy of the repo with the patch applied, under `next dev` on port 3107, in the
built-in browser.

| check | result |
| --- | --- |
| `py contrast.py tokens.json` | 35 pairs, **0 failing AA** (before the fixes: 7 failing pairs in shipped components) |
| `tsc --noEmit` (after `next typegen`) | passes |
| `/design` renders all 9 sections (colours, type, buttons, forms, badges, stat cards, table, states, overlays) | yes |
| token roles resolve as Tailwind utilities (`bg-accent-hover`, `border-border-input`, `text-text-placeholder`, `ring-focus`, `bg-nav-active`) | yes, colours match the tokens on screen |
| input / select / textarea boundary visible | yes (`#8492A6`, 3.16:1) |
| secondary button focus ring | brand ring `rgb(59,130,246)` at 2px offset (was slate-300, 1.42:1) |
| console | only 4 × 404 for `/api/v1/auth/*`: `AuthProvider` in the root layout looks for a backend that isn't running in this preview. Expected |

Not checked here:
- **An automated axe scan.** `@axe-core/playwright` is in devDependencies but needs Playwright's browser download.
  Run `npx playwright install chromium`, then axe over `/design`.
- **Hover states by pointer.** Their colours are covered by the contrast pairs.
- **The new components in components.md** (ActionsMenu, Switch, Toast, Tabs, …). Those get built per milestone.
