# Chapter 8 — Working on IntraForge: setup, tests, release — Branches and commits

Topic for: software engineers. Source: IntraForge Engineering Handbook, Chapter 8 — Working on IntraForge: setup, tests, release.

- Work on a branch (current integration branch: `integration/1.5.0`); never push to `master`/`main` and never
  force-push. Changes reach `master` through pull requests the owner merges.
- Small commits, one concern each, in the conventional style: `feat(storage): …`, `fix(kit): …`, `docs(guides): …`.
- Ask before changing a separate repository (Pay, Spare Parts).
