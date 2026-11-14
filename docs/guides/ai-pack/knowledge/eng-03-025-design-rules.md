# Chapter 3 — The frontend — Design rules

Topic for: software engineers. Source: IntraForge Engineering Handbook, Chapter 3 — The frontend.

- **Colours are tokens** (`--color-brand-600`, `--color-navy`, …) defined in `globals.css` and redefined for dark mode
  under `html[data-theme="dark"]`. `ThemeToggle` and `lib/theme.ts` store the choice (system / light / dark) in the
  browser. Never hard-code a hex colour in a component. The brand is described in `DESIGN.md`.
- **Icons are `lucide-react` components, never emoji** (emoji render differently across fonts and platforms).
- Accessible by default: labels on every input, visible focus rings, `Modal` traps focus, motion respects
  `prefers-reduced-motion` (`use-reduced-motion.ts`).
- The screen hiding a button is a courtesy; the server's capability check is the lock. Always handle a 403 with a
  clear "you don't have permission" message.
