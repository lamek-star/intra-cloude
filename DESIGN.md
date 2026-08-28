# DESIGN.md — Intra-Cloud

> Design source of truth for design and coding agents working on Intra-Cloud.
> Companion to `CLAUDE.md` / `AGENTS.md` (which describe *how to build*).
> This file describes *how it should look and feel*, with the rationale attached
> so an agent can stay on-system when it hits a case this file never covered.
>
> **Status legend used throughout**
> - `[shipped]` — already implemented in `apps/frontend`; match it exactly.
> - `[spec]` — specified here, **not yet implemented**. Do not assume it exists.

---

## 1. Identity

**Intra-Cloud is private cloud infrastructure that organizations run on their own terms.**
Its users are administrators, developers and data owners. They arrive with a task
(find a file, fix a permission, read a log, import a table) and want it done with
the fewest possible unknowns.

### Design direction

Original to Intra-Cloud, informed by — never copied from — four reference products:

| Borrowed principle | From | How it shows up here |
|---|---|---|
| Precise navigation, one obvious hierarchy, keyboard-first | Linear | Fixed navy rail, `Ctrl K` command palette, one primary action per view |
| Technical surfaces treated as first-class UI, not an afterthought | Supabase | Table/database screens use real data density, monospace for identifiers |
| Restraint — typography and spacing carry the design, not ornament | Vercel | One accent colour, near-flat surfaces, no decorative gradients in content |
| Readable, calm content and settings screens | Notion | Generous line length limits, labelled sections, quiet dividers |

**We do not** reproduce any of those companies' logos, wordmarks, brand colours,
proprietary typefaces, illustration styles or marketing copy. The reference
collection in `design-references/` is inspiration for *structure and restraint*
only.

### Three rules that settle most arguments

1. **Certainty over delight.** If an animation, colour or flourish makes the
   user less sure about what just happened or what will happen next, remove it.
2. **One accent.** Indigo means "this is the action" or "this is where you are."
   If indigo is on screen three times, two of them are wrong.
3. **Density is a feature.** These are working screens. Prefer showing one more
   row of real data over one more pixel of padding.

### Naming note

The shipped sidebar and mobile header currently read **"Private Data Cloud"**
(`apps/frontend/src/components/AppShell.tsx`). The product is referred to as
**Intra-Cloud** in this document. Aligning the in-product wordmark is a
deliberate product decision and is **out of scope** for any styling task — do
not change it as a side effect of design work.

---

## 2. Colour tokens

### 2.1 Light theme `[shipped]`

This is the theme the application ships today.

| Token | Value | Use |
|---|---|---|
| `--surface-canvas` | `#F5F6FB` | App background behind all content |
| `--surface-raised` | `#FFFFFF` | Cards, tables, modals, inputs |
| `--surface-sunken` | `#EEF0F7` | Wells, code blocks, inset panels |
| `--surface-muted` | `#F8FAFC` | Table headers, hover rows, quiet fills |
| `--border-subtle` | `#E2E8F0` | Default border (cards use it at 70% alpha) |
| `--border-strong` | `#CBD5E1` | Dividers that must survive a busy screen |
| `--text-primary` | `#151823` | Headings, values, primary body |
| `--text-secondary` | `#475569` | Body copy, table cells |
| `--text-tertiary` | `#94A3B8` | Labels, captions, disabled, placeholder |
| `--text-inverse` | `#FFFFFF` | Text on brand / navy fills |

### 2.2 Brand `[shipped]`

| Token | Value | Use |
|---|---|---|
| `--brand-700` | `#4338CA` | Pressed state |
| `--brand-600` | `#4F46E5` | Primary buttons, active nav |
| `--brand-500` | `#6366F1` | Hover, focus ring, avatar fills |
| `--brand-100` | `#E0E7FF` | Selected row tint |
| `--brand-50`  | `#EEF2FF` | Info badge background |

### 2.3 Chrome (navigation rail) `[shipped]`

The navy rail is the one place a gradient is allowed. It exists to separate
"where you are in the product" from "what you are working on."

| Token | Value | Use |
|---|---|---|
| `--chrome-from` | `#12163A` | Rail gradient top |
| `--chrome-to`   | `#0B0E24` | Rail gradient bottom |
| `--chrome-fg`   | `#FFFFFF` | Active rail label |
| `--chrome-fg-muted` | `#94A3B8` | Inactive rail label |
| `--chrome-fill` | `rgba(255,255,255,0.05)` | Rail search / account tiles |
| `--chrome-fill-hover` | `rgba(255,255,255,0.10)` | Rail hover |
| `--chrome-divider` | `rgba(255,255,255,0.10)` | Rail section rule |

### 2.4 Status `[shipped]`

Status colour is always paired with a **word**. Colour alone never carries
meaning — see §14.

| Intent | Solid | Tint bg | Tint fg |
|---|---|---|---|
| Success | `#059669` | `#ECFDF5` | `#047857` |
| Warning | `#D97706` | `#FFFBEB` | `#B45309` |
| Danger  | `#DC2626` | `#FEF2F2` | `#B91C1C` |
| Info    | `#4F46E5` | `#EEF2FF` | `#4338CA` |
| Neutral | `#64748B` | `#F1F5F9` | `#475569` |

### 2.5 Dark theme `[spec]`

**Not implemented.** `globals.css` defines light values only, with no
`prefers-color-scheme` block and no `data-theme` switch. Ship the tokens below
before any component starts referencing them; do not half-adopt them.

| Token | Dark value | Note |
|---|---|---|
| `--surface-canvas` | `#0B0E24` | Canvas adopts the rail's deep navy |
| `--surface-raised` | `#151935` | Cards lift *toward* light |
| `--surface-sunken` | `#080A1B` | Code, wells |
| `--surface-muted`  | `#1C2145` | Table header, hover |
| `--border-subtle`  | `#262B4D` | |
| `--border-strong`  | `#39406B` | |
| `--text-primary`   | `#E8EAF6` | Never pure `#FFF` — it vibrates on navy |
| `--text-secondary` | `#A9B0D0` | |
| `--text-tertiary`  | `#6F779E` | |
| `--brand-600`      | `#6366F1` | Brand lightens one step in dark |
| `--brand-500`      | `#818CF8` | |
| Success / Warning / Danger tints | `#064E3B` / `#4A2E05` / `#4C1417` | fg lightens to `#6EE7B7` / `#FCD34D` / `#FCA5A5` |

**Rule:** the rail does **not** change between themes. In dark mode it stops
being a contrast device and becomes continuous with the canvas — that is
intended, and the rail keeps its `--chrome-divider` rules so structure survives.

### 2.6 Implementation

Define every token once on `:root`, override only what changes in dark, and
guard the media query so an explicit light choice still wins:

```css
:root { --surface-canvas: #F5F6FB; /* …all light tokens… */ }
:root:not([data-theme="light"]) {
  @media (prefers-color-scheme: dark) { /* …dark overrides… */ }
}
:root[data-theme="dark"] { /* …dark overrides… */ }
```

Never give a colour its only definition inside a media query.

---

## 3. Typography

**Sans:** Inter, self-hosted via `next/font` and exposed as `--font-inter`,
mapped to Tailwind's `--font-sans` in `globals.css`. `[shipped]`
**Mono:** `ui-monospace, "JetBrains Mono", "SF Mono", Menlo, Consolas, monospace`.

Mono is not decorative. Use it for values the user may need to copy or compare
character by character: IDs, API keys, hashes, hostnames, column names, request
IDs, log lines, file sizes in tables.

| Role | Size | Weight | Tracking | Colour |
|---|---|---|---|---|
| Page title | 24px | 600 | `-0.02em` | primary |
| Section title | 18px | 600 | `-0.01em` | primary |
| Card title | 14px | 600 | normal | primary |
| Body | 14px | 400 | normal | secondary |
| Table cell | 14px | 400 | normal | secondary |
| Stat value | 24px | 600 | `-0.02em` | primary |
| Label / field label | 12px | 500 | normal | tertiary |
| Table header | 12px | 500 | `0.05em`, uppercase | tertiary |
| Caption / meta | 11–12px | 400 | normal | tertiary |
| Badge | 11px | 500 | normal | per status |

**Constraints**
- **14px is the floor for anything the user must read to act.** 11–12px is for
  labels and metadata only.
- Prose and descriptions cap at **`max-w-2xl` (~65ch)**. Data tables do not cap.
- Headings never wrap to more than two lines at `lg`.
- Numbers in tables and stat cards use tabular figures
  (`font-variant-numeric: tabular-nums`) so columns align.

---

## 4. Spacing

4px base scale, matching Tailwind's default. Use these steps only:

`2 · 4 · 6 · 8 · 10 · 12 · 14 · 16 · 20 · 24 · 32 · 40 · 48 · 56`

| Context | Value |
|---|---|
| Icon ↔ label | 6px (`gap-1.5`) |
| Inside a badge | 8px / 2px |
| Button padding (`sm`) | 10px / 6px |
| Button padding (`md`) | 14px / 8px |
| Input padding | 12px / 8px |
| Card padding | 20px (`p-5`) |
| Table cell padding | 16px / 10px |
| Between form fields | 16px |
| Between cards in a grid | 16px (`gap-4`) |
| Between page sections | 24–32px |
| Page gutter (mobile / desktop) | 16px / 24px |

**Rule:** vertical rhythm between sections is always larger than rhythm inside
them. If a section's internal gap equals its external gap, the grouping has
stopped communicating.

---

## 5. Radii `[shipped]`

| Token | Value | Applied to |
|---|---|---|
| `sm` | 6px | Badges on dense rows, inline code |
| `md` | 8px | Buttons, inputs, selects, textareas, error banners |
| `lg` | 12px | Rail tiles, avatars, stat icon chips, menus |
| `xl` | 16px | Cards, tables, modals, empty states |
| `full` | 9999px | Badges, avatars, pills |

**Rule:** a child's radius is never larger than its parent's. A `md` button
inside an `xl` card is correct; the reverse is not.

---

## 6. Shadows

Elevation is carried by **border first, shadow second**. Shadows here are almost
imperceptible by design — they hint at a seam, they do not float.

| Token | Value | Use |
|---|---|---|
| `--shadow-card` | `0 1px 2px rgba(16,24,40,0.04)` | Cards, tables `[shipped]` |
| `--shadow-control` | `0 1px 2px rgba(16,24,40,0.06)` | Buttons, inputs `[shipped]` |
| `--shadow-menu` | `0 8px 24px -8px rgba(11,14,36,0.18)` | Dropdowns, popovers, command palette |
| `--shadow-overlay` | `0 20px 40px -12px rgba(11,14,36,0.35)` | Modals |

In dark mode, shadows do not read. Substitute a one-step-lighter
`--border-subtle` for menus and modals instead of increasing shadow opacity.

---

## 7. Navigation

### 7.1 Structure `[shipped]`

```
Rail (navy, 240px, ≥sm)     Content
├─ Wordmark                 ├─ PageHeader — title, description, primary action
├─ Search  (Ctrl K)         ├─ Breadcrumb / back link when nested
├─ Dashboard                └─ Body
├─ Organizations
└─ Account · Log out (foot)
```

The rail carries only **top-level destinations**. Everything deeper —
organization sections, the developer portal, workspace and table detail — is
reached from within the content area. This is deliberate: the rail must not
grow with the data model.

- **Mobile (`<sm`):** the rail is hidden and replaced by a 56px white top bar
  with the wordmark. `[shipped]`
- **Developer portal:** owns a secondary nav (`DeveloperNav.tsx`) rendered
  inside the content area, not in the rail. `[shipped]`

### 7.2 Rules

- Exactly one nav item may be active. Active state = `--chrome-fg` text plus
  `--chrome-fill` background plus `aria-current="page"`.
- **Every** nav landmark carries an `aria-label` (`Main navigation`, etc.) —
  already true across the app and must stay true. `[shipped]`
- Breadcrumbs appear whenever a page is more than one level below a rail
  destination (e.g. Orgs → Org → Workspace → Table).
- The **command palette (`Ctrl K`) is the fastest path** to any resource and is
  the reason the rail can stay short. Any new resource type should be reachable
  from it.
- A "Skip to main content" link is the first focusable element on every page.
  `[shipped]`

---

## 8. Buttons `[shipped]`

Four variants, two sizes. There is no fifth variant — if a new one seems
necessary, the layout is doing too much.

| Variant | Fill | Text | Border | Use |
|---|---|---|---|---|
| `primary` | `--brand-600` → `--brand-500` hover | inverse | none | The one action the page exists for |
| `secondary` | raised → `--surface-muted` hover | secondary | subtle | Everything else |
| `danger` | `#DC2626` → `#EF4444` hover | inverse | none | Destructive, after confirmation |
| `ghost` | transparent → `--surface-muted` hover | secondary | none | Toolbar, row-level, tertiary |

- Sizes: `sm` = 12px text / 10×6 padding · `md` = 14px text / 14×8 padding.
- Radius `md` (8px), weight 500, `transition-colors` only.
- **One `primary` per view.** A page with two primary buttons has an unresolved
  hierarchy problem.
- Focus: 2px `--brand-500` ring, 2px offset against the canvas. `[shipped]`
- Disabled: 50% opacity, pointer events off. Never hide a disabled action —
  explain why it is disabled nearby.
- Destructive actions route through `ConfirmProvider`, never a bare `onClick`.
  `[shipped]`
- A button that triggers async work shows a `Spinner` **in place of its icon**,
  keeps its label, and disables itself. The button must not change width.

---

## 9. Forms and validation `[shipped]`

**Structure:** `Label` (12px/500/tertiary, 6px below) → control → help or error
text. Fields stack at 16px. Related fields group inside a `fieldset` with a
`legend` — as the connect wizard's access-level radios already do.

**Controls:** full width, raised background, subtle border, radius `md`,
12×8 padding, 14px text, `--text-tertiary` placeholder. Focus moves the border
to `--brand-500` and adds a 2px `--brand-500/20` ring.

**Validation rules**
- Validate on **blur**, then on every change once a field has errored. Never
  validate on first keystroke.
- Required fields use the **real `required` attribute**, not a visual asterisk
  alone — the app already does this on table row forms and must keep doing it.
- An errored field gets: `aria-invalid="true"`, `aria-describedby` pointing at
  the message, a `#DC2626` border, and a 12px message below it.
- Error text names the fix, not the failure: "Bucket names use lowercase letters,
  numbers and hyphens" — not "Invalid input."
- **Form-level failure** renders an `ErrorBanner` above the form and moves focus
  to it. Server errors expose status / code / requestId behind a collapsed
  "View technical details" disclosure — never a stack trace, never expanded by
  default. `[shipped]`
- Never clear a user's input on a failed submit.
- Secrets (API keys, connection strings, tokens) render through `SecretReveal`
  masked by default, with `CopyButton` beside them. A secret is shown in full
  exactly once, at creation, with an explicit "you will not see this again"
  warning.

---

## 10. Tables `[shipped]`

The densest and most important surface in Intra-Cloud.

- Container: raised, radius `xl`, subtle border, `overflow-x-auto`.
- Header: `--surface-muted` fill, bottom border, 12px uppercase tertiary,
  `0.05em` tracking, `whitespace-nowrap`.
- Cells: 16×10 padding, 14px, `--text-secondary`.
- Rows: 1px `#F1F5F9` bottom border, none on the last row.
- **Clickable rows** get `role="button"`, `tabIndex={0}`, Enter/Space handling
  and a visible focus outline. A row is never clickable without all four.
  `[shipped]`
- Identifiers, sizes and timestamps render in mono with tabular figures.
- Numeric columns right-align; everything else left-aligns.
- Row actions live in a trailing column, `ghost` size `sm`, revealed on hover
  **and always present for keyboard users** (never `opacity-0` alone).

**Scale**
- Sort on any column the backend can sort; indicate direction in the header.
- Paginate past 50 rows. Show "N of M" — never just "Next".
- Filters sit above the table in a single row, and their active state is
  visible without opening a menu.
- Bulk selection adds a leading checkbox column and swaps the filter row for a
  selection bar reading "N selected" plus its actions.
- Wide tables scroll **inside their own container**. The page body must never
  scroll horizontally.

---

## 11. Dashboard cards `[shipped]`

**`StatCard`** — icon chip (36px, radius `lg`, tinted) → 12px label → 24px value
→ optional 11px detail, closed by a 4px accent bar flush to the card's bottom
edge. Card padding is moved inside (`!p-0` + inner `p-5`) so the bar can reach
the edges.

- Stat grids are 1 / 2 / 4 columns at base / `sm` / `lg`.
- The value is the largest text in the card. If a card needs a second value of
  equal weight, it is two cards.
- **A number without a comparison is decoration.** Prefer "1,284 · +12% vs last
  week" over "1,284".
- Loading: skeleton the value only. Never collapse the card's height.
- Zero is a real value — render `0`, never an em dash or a blank.

**`Card`** — raised, radius `xl`, `--border-subtle` at 70% alpha, `p-5`,
`--shadow-card`. The default container for everything that is not a table.

---

## 12. Domain surfaces

### 12.1 File browser — buckets `[shipped]`

Routes: `/buckets/[bucketId]`

- Table-first, not tiles. Columns: name (with type icon), size (mono, tabular),
  modified (relative, with absolute in `title`), and a trailing action column.
- Folders sort above files, each group alphabetical.
- Path breadcrumb sits directly above the table; every segment is a link, and
  the current segment is plain text.
- Upload is the page's one `primary` action. Drag-and-drop over the table
  outlines the container in `--brand-500` — no full-screen overlay.
- In-progress uploads pin to the top of the table with a determinate progress
  bar, a byte count, and a cancel control.
- Delete is `danger`, always confirmed, and names the file in the confirmation.
- File-type icons come from `lucide-react` and are `--text-tertiary` — the icon
  identifies the type, it does not decorate the row.

### 12.2 Database management — tables `[shipped]`

Routes: `/tables/[tableId]`, `/tables/[tableId]/import`, `/tables/[tableId]/analytics`,
`/connected-databases/[id]`, `/tenant-databases/[dbId]`

- A table detail page has three tabs — **Data · Import · Analytics** — as a
  tab bar under the `PageHeader`, not as rail entries.
- Column names and SQL types render in mono. Types are `neutral` badges, never
  coloured.
- Nullable columns show `NULL` in `--text-tertiary` italic mono. An empty string
  is `""` — the two must be visually distinguishable.
- Row editing is inline, not a modal: the row becomes inputs, with Save/Cancel
  in the trailing column. Escape cancels.
- **Import** is a stepper: Upload → Map columns → Preview → Confirm. Column
  mapping is a two-column list of source header ↔ target column with per-row
  type warnings. The preview shows the first 10 parsed rows and a count of rows
  that will fail, before anything is written.
- Connection strings and credentials are `SecretReveal` + `CopyButton`, never
  plain text.
- Connection state is a badge with a word: `Connected` / `Degraded` /
  `Unreachable`.

### 12.3 Organizations, teams, workspaces `[shipped]`

Routes: `/orgs`, `/orgs/[orgId]`, `/orgs/[orgId]/teams`, `/orgs/[orgId]/workspaces/[workspaceId]`

- `/orgs` is a card grid: name, member count, role badge, last activity.
- An org overview leads with stat cards, then its sections as a linked list.
- Member tables show avatar + name + email in one cell, role as a `Select` for
  users who may change it and as a `Badge` for those who may not.
- **Role is always visible before a destructive action.** Removing a member
  states their role in the confirmation.
- Pending invites are a separate table above members, with Resend and Revoke.
- The last owner of an organization cannot be removed or demoted — the control
  is disabled with an inline explanation, not hidden.
- Audit (`/orgs/[orgId]/audit`) is a table of actor · action · target ·
  timestamp, filterable by actor and date, with timestamps in mono.

### 12.4 Developer portal `[shipped]`

Routes: `/orgs/[orgId]/developer/*` — api-keys, api-logs, applications, auth,
database, docs, environments, sdks, storage, usage, webhooks.

- Owns a secondary nav (`DeveloperNav`) inside the content area.
- Every page that shows a code sample uses `--surface-sunken`, mono, radius `md`,
  and a `CopyButton` in the top-right of the block.
- API keys: created once, revealed once, masked thereafter. The table shows
  prefix, scopes, created, last used, and a `danger` Revoke.
- API logs: mono, tabular, colour-coded status **with the numeric status
  visible** (`200`, `404`, `500` — never colour alone). Row expands to headers
  and body.
- Environments are `info` badges; production is `warning` to slow the user down.
- `DeveloperStub` / `ComingSoon` is the honest placeholder for unbuilt sections
  — it states what is coming, and never fakes data.

### 12.5 Settings `[spec for layout, shipped per-page]`

- Two-column at `lg`: a sticky section list on the left, content on the right.
  Single column below `lg`, sections stacked with headings.
- Each setting is one row: label + description on the left, control on the
  right, separated by a `--border-subtle` rule.
- **Save behaviour is per section, not per page.** A section with unsaved
  changes reveals a Save / Discard pair; nothing else on the page moves.
- Destructive settings live in a final "Danger zone" section: `#DC2626` border,
  every action `danger`, every action confirmed by typing the resource name.

---

## 13. States

Every data surface implements all five. A screen that renders only its success
state is incomplete.

| State | Pattern |
|---|---|
| **Empty** | `EmptyState` — dashed subtle border, radius `xl`, `bg-white/60`, 14px title, description ≤ `max-w-sm`, and the action that resolves it. `[shipped]` |
| **Loading** | `PageLoading` (centred `Spinner`, 256px min-height) for a whole page; skeletons matching final layout for partial regions. Never a layout that jumps when data lands. `[shipped]` |
| **Success** | Inline and quiet — a `success` badge or a 3s toast. Never a modal. Never block the next action. |
| **Warning** | `warning` tint banner above the affected region, stating the consequence and what to do. Dismissible only if truly optional. |
| **Error** | `ErrorBanner` — `#FEF2F2` fill, `#FECACA` border, `#B91C1C` text, radius `md`. Plain-language message, technical detail behind a disclosure. `[shipped]` |

**Rules**
- Distinguish "no data yet" (offer the action) from "no results" (offer to clear
  filters). They are different states with different copy.
- A destroyed-by-error page still shows its chrome and nav — errors never take
  the user's navigation away.
- Optimistic updates roll back visibly, with an error banner explaining what
  reverted.

---

## 14. Accessibility

Non-negotiable. The app has already been through an accessibility pass; these
are the invariants that pass established.

- **Contrast:** 4.5:1 for text under 18px, 3:1 for large text and for the
  boundary of every interactive control. `--text-tertiary` (`#94A3B8`) passes on
  white for 12px+ **labels only** — never for body copy.
- **Focus:** a global `focus-visible` rule gives every interactive element a 2px
  `#6366F1` outline at 2px offset; components may override with their own ring
  but may never remove it. `[shipped]`
- **Keyboard:** every interactive element is reachable and operable. Clickable
  table rows implement Enter/Space. Modals and menus trap focus, close on
  Escape, and restore focus to their trigger (`useDialogA11y`). `[shipped]`
- **Landmarks:** one `<main id="main-content">`, labelled `<nav>` elements,
  `aria-current="page"` on the active item, skip link first in the DOM.
  `[shipped]`
- **Forms:** every control has a real `<label htmlFor>`; groups use
  `fieldset`/`legend`; errors are wired with `aria-invalid` + `aria-describedby`.
  `[shipped]`
- **Colour is never the only signal.** Status badges carry text. Log status
  codes show the number. Chart series are distinguishable without colour.
- **Live regions:** async results announce via `aria-live="polite"`; errors via
  `role="alert"`.
- **Icons:** decorative icons are `aria-hidden="true"`; icon-only buttons carry
  an `aria-label`.
- **Zoom:** usable at 200% zoom and at a 320px viewport with no horizontal page
  scroll.

---

## 15. Responsive

| Breakpoint | Width | What changes |
|---|---|---|
| base | <640 | Single column. Rail hidden, white top bar. 16px gutters. Tables scroll inside their container. Steppers stack vertically. `[shipped]` |
| `sm` | ≥640 | Navy rail appears (240px). Two-column stat grids. 24px gutters. |
| `md` | ≥768 | Two-column forms where fields are genuinely paired. |
| `lg` | ≥1024 | Four-column stat grids. Settings goes two-column. Table row actions become persistent rather than hover-revealed. |
| `xl` | ≥1280 | Content caps at 1280px and centres. Reading columns still cap at `max-w-2xl`. |

**Rules**
- Design the 375px view first for any new screen; the desktop view is the one
  that gets extra room, not the one that gets designed first.
- Touch targets are ≥44×44px below `sm`, including table row actions.
- Never hide data at small sizes — reflow it. Hiding a column is acceptable only
  when it is also reachable by expanding the row.
- The connect wizard's stepper is already responsive; new multi-step flows
  follow it. `[shipped]`

---

## 16. Motion and reduced motion

Motion in Intra-Cloud confirms that something happened. It never announces.

| Kind | Duration | Easing |
|---|---|---|
| Hover / focus colour | 120ms | `ease-out` |
| Menu, popover, palette | 150ms | `cubic-bezier(0.16, 1, 0.3, 1)` |
| Modal | 200ms | `cubic-bezier(0.16, 1, 0.3, 1)` |
| Toast in / out | 200 / 150ms | `ease-out` / `ease-in` |
| Spinner | 800ms | `linear`, infinite |

- Animate `opacity` and `transform` only. Never animate layout properties.
- Nothing animates for longer than 300ms.
- Content that has loaded never animates on arrival — it appears.

**Reduced motion is mandatory.** Honour `prefers-reduced-motion: reduce`
globally:

```css
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
    scroll-behavior: auto !important;
  }
}
```

Under reduced motion, transitions become instant state changes — never removed
feedback. The one permitted exception is the `Spinner`, which may keep rotating
because it is the only indication that work is still in progress; if it is
suppressed, replace it with static "Loading…" text.

> This block is **`[spec]`** — `globals.css` does not currently contain it. Add
> it before introducing any new animation.

---

## 17. Working agreements for agents

1. **Reuse before you create.** `apps/frontend/src/components/ui.tsx` already
   exports Button, LinkButton, Input, Textarea, Select, Checkbox, Label, Card,
   Badge, Spinner, PageLoading, EmptyState, ErrorBanner, CopyButton,
   SecretReveal, PageHeader, Table/THead/Th/Td/TRow, Modal, ComingSoon and
   StatCard. Extend a primitive rather than styling a one-off.
2. **No new colours.** If a value is not in §2, it does not go in the codebase.
3. **No new dependencies for styling.** Tailwind v4 + `lucide-react` is the
   whole toolkit.
4. **Accessibility invariants in §14 are not negotiable** and are not traded for
   visual preference.
5. **Respect `[spec]` markers.** Dark mode and the reduced-motion block do not
   exist yet. Implement them deliberately and completely, or not at all.
6. **Do not change the wordmark, copy, or business logic** as a side effect of a
   styling task.

---

## 18. References

`design-references/awesome-claude-design/` — the VoltAgent curated collection.
Note that it is a **link index** (`README.md`), not a set of local `DESIGN.md`
files; each entry points to its preview and download page on getdesign.md.

Consult it for structural and typographic restraint. Do not copy any listed
company's branding, wordmark, palette, proprietary typeface or copy into
Intra-Cloud.
