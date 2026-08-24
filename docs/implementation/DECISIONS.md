# Decisions Log

Lightweight decisions for this initiative. Anything architecturally
significant enough for a real ADR still goes in `docs/architecture/adr/`,
not here — this file is for smaller, still-worth-recording calls.

## Icon library: lucide-react

Decided (and already committed, `39c19ca`) before this log existed.
MIT-licensed, tree-shakeable SVG components, TypeScript-native, no runtime
deps beyond React. Convention: every new page uses `lucide-react` icons,
never emoji (emoji render inconsistently across platforms/fonts).

## Plugin marketplace names differ from source repo names

`claude plugin marketplace add <repo>` names the marketplace from the
repo's own manifest, not the repo name. `anthropics/claude-code` ->
`claude-code-plugins`; `headroomlabs-ai/headroom` -> `headroom-marketplace`.
Install with the registered name (`plugin@claude-code-plugins`), not a
guessed one.

## Headroom plugin: installed despite missing runtime

`headroom@headroom-marketplace`'s hooks call `headroom init hook ensure`
on every session start and before every Bash/PowerShell tool call. The
separate `headroom` binary isn't installed on this machine, so those hook
calls currently no-op/fail harmlessly. Installed anyway at explicit user
request, with the tradeoff surfaced first. Not a blocker for any other
work; revisit only if the user installs the `headroom` binary or reports
the hook failures as noisy.

## docs/implementation/ vs docs/development/

`docs/development/` already existed pre-session (`CONTRIBUTING.md`) and is
about contributing to the repo generally. `docs/implementation/` is new,
narrower, and specific to this UI/UX initiative's durable checkpoint state
— kept separate rather than merged into `docs/development/` so a future
session scanning for "what's the state of the current initiative" doesn't
have to separate it from general contributor docs.
