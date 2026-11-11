# Components: IntraForge

One block per component the recon found (recon.md → Components). The **behaviour** reference was AWS's console
patterns: what a resource table, a wizard or a secret-shown-once dialog must do. **Every visual value is IntraForge's
own**: tokens from [tokens.json](tokens.json), DESIGN.md, and `apps/frontend/src/components/ui.tsx`. No AWS colour,
font, icon or copy is used. Icons are `lucide-react` (ISC licence), already a dependency.

Status per block:
- **shipped**: exists in `ui.tsx` or another component; spec = what it does + the fixes it needs.
- **new**: needed by the architecture's build order; build it in `ui.tsx` (or its own file) before any screen uses it.

Token names are the replica roles from `tokens.css` (`bg-surface`, `text-muted`, `border-border-input`, `ring-focus`,
…). In Tailwind v4 a colour token `--color-x` becomes `bg-x`, `text-x`, `border-x`, `ring-x`.

Global rules for every component (DESIGN.md §14, unchanged):
- **Focus.** A visible 2px `focus` ring at 2px offset. A component may restyle it but never remove it.
- **Status.** Colour never carries meaning alone; every status has a word.
- **Touch targets.** ≥ 44×44px below `sm`.
- **Motion.** `opacity`/`transform` only, ≤ 300ms, instant under reduced motion (except Spinner).

---

## Actions

```
Button                                                                       shipped · FIX
  variants  primary (one per view), secondary, danger, ghost
  sizes     sm 12px text, 10x6 padding (~28px tall) · md 14px, 14x8 (~36px). Below sm: min-h 44px
  states    default, hover, active, focus-visible, disabled (50%, still visible, reason nearby), loading
  tokens    primary bg accent → hover accent-hover (FIX, was brand-500 = 3.68:1), text on-accent
            secondary bg surface, border border, text text-body → hover surface-muted
            danger bg danger → hover danger-hover (FIX, was red-500 = 3.76:1), text on-accent
            ghost transparent, text text-body → hover surface-sunken
            all: radius md, weight 500, shadow control (not ghost), ring focus (FIX for secondary/ghost: was slate-300 = 1.42:1)
  loading   Spinner replaces the icon, label stays, aria-busy="true", disabled, width does not change
  a11y      real <button type="button|submit">; icon-only needs aria-label; danger routes through ConfirmDialog
  used on   every screen
```

```
LinkButton                                                                   shipped · FIX
  same look as Button for navigation (<Link>), variants primary/secondary/ghost
  FIX       primary hover → accent-hover; add the focus-visible ring classes Button has (LinkButton has none,
            so it falls back to the global outline — fine, but make it explicit)
  a11y      it is a link: never use it for an action that changes data
```

```
CopyButton                                                                   shipped
  states    idle "Copy" → "Copied" with check icon for 1.5s → idle; silent fallback if no Clipboard API
  ADD       aria-live="polite" on the label so "Copied" is announced
  used on   S17 credentials, S28 site address, S29 env values, F02 share link, code blocks
```

```
ActionsMenu (dropdown)                                                       NEW
  purpose   row and page actions beyond the one primary: Rename, Download, Share link, Delete…
  anatomy   ghost sm trigger (MoreHorizontal icon + aria-label "Actions for <name>") → menu, radius lg, shadow menu
  states    closed, open, item hover/focus, item disabled (with title explaining why), danger item last, separated
  keyboard  Enter/Space/ArrowDown opens and focuses first item; arrows move; Home/End; Escape closes and returns focus;
            typing a letter jumps to the next item starting with it
  a11y      button aria-haspopup="menu" aria-expanded; role="menu"/"menuitem"; never opacity-0 for keyboard users
  used on   S07 file rows, S05 bucket list, S25/S28 site cards (replaces the 6 inline buttons), S17 credentials
```

## Forms

```
Input / Textarea / Select                                                    shipped · FIX
  states    default, hover, focus (border focus + 2px focus/20 ring), invalid, disabled, read-only
  tokens    bg surface, text text, radius md, 12x8 padding, 14px
            border border-input (FIX: was slate-200 = 1.23:1; WCAG 1.4.11 needs 3:1)
            placeholder text-placeholder (FIX: was slate-400 = 2.56:1)
            invalid: border danger, aria-invalid="true", aria-describedby → FieldError
  rule      validate on blur, then on change once errored; never clear input on a failed submit
  used on   every form
```

```
Checkbox                                                                     shipped · FIX
  FIX       border border-checkbox (was slate-300 = 1.48:1); focus ring focus (was brand-500/30, too faint)
  a11y      always with a <label>; groups in fieldset/legend
```

```
Switch (toggle)                                                              NEW
  purpose   on/off settings that apply immediately: bucket versioning, external sharing, lifecycle rule enabled
  anatomy   36x20 track, 16px thumb; off track border-input on surface, on track accent; label left, state word right
  states    off, on, focus, disabled, pending (Spinner in the thumb while the PATCH runs; reverts with ErrorBanner on failure)
  a11y      <button role="switch" aria-checked>; the visible label is its name; the state word ("On"/"Off") is visible
  used on   S10 bucket settings, S12 lifecycle rules, org external-sharing toggle
```

```
Label / FieldHelp / FieldError                                               shipped (Label) · NEW (help, error)
  Label     12px/500 text-muted, 6px below; real <label htmlFor>
  FieldHelp 12px text-muted under the control, id wired via aria-describedby
  FieldError 12px danger-text, id wired via aria-describedby; text names the fix ("Use lowercase letters…")
```

```
DateRangePicker                                                              NEW
  purpose   audit and usage filters (F09, F12)
  anatomy   two native <input type="date"> (from / to) + presets as ghost buttons: Today, 7 days, 30 days
  rule      dates are the SHOP's local days (SHOP_TIME_ZONE), shown as such: "Dates in shop time (UTC+4)"
  states    empty (= all time), set, invalid (to < from → FieldError), disabled
  a11y      native date inputs keep the platform's keyboard and screen-reader support; no custom calendar
  used on   S31, S32, S35
```

```
FilterBar                                                                    NEW (pattern exists ad hoc on S31)
  anatomy   one row above a table: search Input, Selects, DateRangePicker, Apply (secondary), Clear (ghost)
  states    no filters, filters active (each shown as a removable chip below the row: "Result: Denied ×"), no results
  rule      active filters are visible without opening anything; "no results" offers Clear, distinct from empty
  used on   S07, S31, S32, S05/S20 org-wide lists
```

## Data display

```
Table / THead / Th / Td / TRow                                               shipped · EXTEND
  tokens    container surface, radius xl, border border/70; header surface-muted, 12px uppercase 0.05em text-muted;
            cells 16x10, 14px text-body; rows 1px surface-sunken divider
  EXTEND    sortable Th: <button> inside the th, aria-sort on the th, arrow icon shows direction
            Pagination footer: "1–50 of 121" + Previous/Next (secondary sm), disabled at the ends (S31 already does this)
            Selection: leading Checkbox column; selection bar "N selected" + actions replaces the FilterBar
            mono + tabular-nums for ids, sizes, times; numeric columns right-aligned
  states    loading (skeleton rows, same height), empty (EmptyState inside), no results (EmptyState + Clear filters),
            error (ErrorBanner above, table chrome stays)
  a11y      clickable row = role="button" + tabIndex 0 + Enter/Space + visible outline (TRow does all four)
  used on   S05, S07, S14, S17, S20, S29, S31, S32
```

```
KeyValueList (details)                                                       NEW
  purpose   object/bucket/site/event properties: S09 file detail, S10 bucket settings, S31 event detail
  anatomy   <dl>, 1 column below md, 2 at md, 3 at lg; term 12px/500 text-muted, value 14px text; ids/hashes mono
            with CopyButton; empty value shows "—" only when the field truly has no value (zero shows 0)
  a11y      semantic <dl>/<dt>/<dd>
```

```
Badge (status)                                                               shipped
  tones     default (neutral-text on neutral-tint), success, warning, danger, info (accent-tint-text on accent-tint)
  rule      always a word: Online, Active, Running, Denied, Planned, not yet built…; production env = warning tone
  size      11px/500, pill; never the only signal
```

```
StatCard                                                                     shipped
  anatomy   36px tinted icon chip → 12px label → 24px value (tabular) → 11px detail → 4px accent bar
  states    loading = skeleton the value only; zero shows 0
  note      the accent bar gradient is decoration (DESIGN.md allows the mark's gradient only — consider a flat bar)
```

```
CodeBlock                                                                    NEW (pattern exists on Developer pages)
  anatomy   surface-sunken (or code-bg/code-text for secrets), mono 12px, radius md, CopyButton top-right
  a11y      <pre><code>, horizontally scrollable inside its own box, tabindex="0" when it scrolls
  used on   S30 webhook payload/verification, S40 docs, S28 "how to publish a Node.js app"
```

```
LogViewer                                                                    NEW
  purpose   hosted-app logs (F07, S27) and request log detail
  anatomy   code-bg panel, mono 12px code-text, one line per entry: time (shop TZ) · stream · text;
            stderr lines prefixed "ERR" (word + colour); toolbar: lines (100/200/500), stream filter, Pause/Resume, Copy
  states    loading, empty ("No output yet — the app has not written anything"), live (polls 5s, aria-live off),
            paused, runner unreachable (ErrorBanner, keeps last lines)
  a11y      region with aria-label "Logs for <site>"; polling never steals focus; text selectable
```

```
Charts                                                                       shipped (AnalyticsResult) · reuse
  rule      series distinguishable without colour (labels, patterns or direct labelling); teal/green as fills only
  used on   S35 usage, S38 dashboards
```

## Feedback

```
EmptyState                                                                   shipped
  anatomy   dashed border, radius xl, surface/60, 14px title, description ≤ max-w-sm, the action that resolves it
  rule      two kinds: "no data yet" (offer the action) vs "no results" (offer Clear filters)
```

```
ComingSoon                                                                   shipped
  the honest placeholder for the 6 unbuilt Developer tabs; replace each as its milestone lands, never fake data
```

```
ErrorBanner                                                                  shipped · FIX
  tokens    danger-tint bg, red-200 border, danger-text, radius md, role="alert"
  FIX       "View technical details" text: danger-text (was red-600/80 = 3.49:1)
  rule      friendly message first; status/code/request id behind the disclosure; focus moves to it on submit failure
```

```
Toast                                                                        NEW
  purpose   quiet success after an action: "Link copied", "Version 3 restored", "Backup queued"
  anatomy   bottom-right (bottom full-width below sm), surface, border, shadow menu, radius lg, icon + one line,
            optional Undo (ghost sm); stack max 3
  timing    in 200ms ease-out, stays 3s (6s if it has Undo, paused on hover/focus), out 150ms
  a11y      container role="status" aria-live="polite"; never used for errors (ErrorBanner) or anything the user must
            read to continue; Undo reachable by keyboard (F6 or Tab from the trigger's next stop)
```

```
Banner (warning / info)                                                      NEW
  purpose   region-level consequence: "Share links only work when Shop network or Internet access is on" (F02),
            "This is a production environment" (S29), quota at 80% (S35)
  tokens    warning-tint + warning-strong-text, or accent-tint + accent-tint-text; icon + text + optional action
  rule      states the consequence and what to do; dismissible only if optional
```

```
Spinner / PageLoading / Skeleton                                             shipped (Spinner, PageLoading) · NEW (Skeleton)
  Spinner   800ms linear, keeps spinning under reduced motion, aria-hidden (the button/region carries aria-busy)
  Skeleton  surface-sunken blocks matching the final layout; no shimmer under reduced motion
  rule      PageLoading on any page that waits > 300ms. L12 found 3–7 s first loads: fix the wait, not the spinner
```

```
ProgressBar (upload)                                                         NEW
  anatomy   4px track surface-sunken, fill accent, determinate; label "2.4 MB of 10 MB · 24%" in mono tabular
  states    queued, uploading, done (success word), failed (danger word + Retry), cancelled
  a11y      role="progressbar" aria-valuenow/min/max + aria-valuetext; Cancel is a real button
  used on   S08 upload rows (pinned to the top of the file table)
```

## Overlays

```
Modal                                                                        shipped
  anatomy   overlay slate-900/40, panel surface radius xl shadow overlay, max-w-md (add size lg = max-w-2xl for wizards)
  a11y      role="dialog" aria-modal, labelled by title, focus trap, Escape closes, focus returns to trigger
            (useDialogA11y). Never for success messages
```

```
ConfirmDialog                                                                shipped (ConfirmProvider) · EXTEND
  shipped   role="alertdialog", useConfirm() from any page
  EXTEND    typed confirmation for irreversible deletes (bucket, database, site, organization):
            "Type <name> to confirm" Input; danger button disabled until it matches exactly; names the role when
            removing a member (DESIGN.md 12.3)
```

```
SecretOnce (SecretReveal)                                                    shipped
  anatomy   warning-tint panel, "shown only once — copy it now", code-bg/code-text mono value, CopyButton
  EXTEND    optional Download .txt for recovery codes (F11) and reset codes (F04); a checkbox
            "I have saved it" before the dialog's Done enables
  used on   S17 new credential, F02 new share link, F11 recovery codes, F04 reset code, webhook signing secret
```

```
CommandPalette (Ctrl K)                                                      shipped · EXTEND · FIX
  EXTEND    search resources via GET /search/ (L5): groups Organizations, Projects, Buckets, Databases, Apps, Sites;
            ≤ 20 results; recent items when the query is empty
  FIX       placeholder and Search icon text-placeholder (were slate-400 = 2.56:1); the "Esc" kbd hint 10px slate-400
            → 11px text-muted
  a11y      role="combobox" + listbox with aria-activedescendant; arrows move, Enter opens, Escape closes
```

```
Popover / HelpTip                                                            NEW (small)
  purpose   the "Info" pattern: one-paragraph help next to a field label, instead of AWS's side help panel
  anatomy   ghost icon button (CircleHelp, aria-label "About <field>") → popover radius lg shadow menu, max-w-xs
  a11y      opens on click (not hover-only), Escape closes, content reachable by screen readers via aria-describedby
```

## Navigation and layout

```
AppShell rail                                                                shipped · FIX
  anatomy   navy 240px rail (≥ sm): wordmark, Search (Ctrl K), Dashboard, Apps, Organizations; account + Log out at the foot.
            Below sm: 56px white top bar
  states    item default (on-chrome-muted text), hover (white/5 bg), active
  FIX       active item bg nav-active (was brand-500 = 3.68:1 behind white)
  ADD       an "Account" link at the foot to the new account page (S04: password, MFA, recovery codes); the header
            "Account menu" button opened nothing at desktop width in the live walkthrough: wire it or remove it
  a11y      nav aria-label="Main navigation", aria-current="page", skip link first
```

```
Breadcrumbs                                                                  shipped (in PageHeader) · FIX
  FIX       include the workspace level (L10): Organizations / Org / Workspace / Project / Bucket
  a11y      nav aria-label="Breadcrumb", current item aria-current="page" plain text; separators aria-hidden
```

```
PageHeader                                                                   shipped
  anatomy   breadcrumbs → 24px title (DESIGN.md) — code uses text-xl (20px): align one to the other → description → actions
  rule      one primary action in actions
```

```
Tabs                                                                         NEW (DeveloperNav is a nav, not tabs)
  purpose   in-page views of one resource: file detail (Overview · Versions · Share links), bucket (Files · Settings ·
            Lifecycle), site (Overview · Logs · Versions · Environment), table (Data · Import · Analytics)
  anatomy   underline tabs, 14px/500, active text text + 2px accent underline, inactive text-muted
  keyboard  role="tablist"/"tab"/"tabpanel"; arrows move between tabs (automatic activation), Home/End
  rule      a tab with its own URL (?tab=versions) so it survives reload and can be linked
```

```
SubNav (DeveloperNav)                                                        shipped
  secondary nav inside content for the Developer portal; stays a <nav> with links, not tabs
```

```
Stepper (wizard)                                                             shipped (connect wizard) · reuse
  used on   F02 share link (File → Expiry → Done is short: use a Modal, not a stepper), import (Upload → Map → Preview
            → Confirm), new website/app (Name → Zip → Environment)
  a11y      ordered list, current step aria-current="step", errors keep the user on the step
```

## Domain blocks (compose the primitives)

```
DropZone + UploadQueue                                                        NEW
  purpose   S08 file and folder upload
  anatomy   the file table itself is the drop target (brand outline on drag, no full-screen overlay) + "Upload files"
            primary + "Upload folder" secondary (input webkitdirectory); queue rows pinned above the table with
            ProgressBar, per-file result, Cancel/Retry
  states    idle, dragging, uploading (n of m), partial failure (summary Banner: "3 of 40 failed — Retry failed"),
            done (Toast), over quota (ErrorBanner before upload starts)
  a11y      the buttons are the accessible path; drag-and-drop is an extra; announce progress per file, not per percent
```

```
ShareLinkPanel                                                               NEW (vertical slice)
  purpose   F02 on the file detail page
  anatomy   Banner if external sharing is off or unreachable (says why and who can turn it on) → "Create link"
            → Modal: expiry Select (1 h, 24 h, 7 days, 30 days), optional max downloads, optional password → SecretOnce
            with the URL → list of links: created, expires (relative + absolute title), downloads n/max, status Badge
            (Active / Expired / Revoked), Revoke (danger, confirmed)
  states    none yet, active links, all expired, sharing off, network unreachable
```

```
FolderTree breadcrumb + Trash toggle                                          NEW
  purpose   S07 folders and the Trash view (F03)
  anatomy   path breadcrumb above the table (every segment a link), folders first; a "Trash" segmented control
            (Files | Trash) switches the status filter; trash rows show deleted date + Restore (secondary sm)
```

```
VersionList                                                                  NEW
  purpose   S09 Versions tab (F03)
  anatomy   Table: version (n, current Badge), size, checksum (mono, truncated + Copy), created, by,
            actions: Download, Restore this version (confirmed: "Version 3 becomes current; the current file is kept as
            version 5")
```

---

## Built primitives

The primitives are built once, in isolation, at [primitives/design-page.tsx](primitives/design-page.tsx), as a
`/design` route. It renders every shipped primitive in every state, with the token fixes applied, so the fixes can be
checked in one screen before any feature screen changes. See [primitives/README.md](primitives/README.md) for how to
drop it in and what the screenshot showed.
