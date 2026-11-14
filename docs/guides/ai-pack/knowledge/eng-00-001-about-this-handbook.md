# About this handbook

Topic for: software engineers. Source: IntraForge Engineering Handbook, About this handbook.

This handbook is for the software engineer who takes over, extends or scales IntraForge. It explains how the whole
system is built, why it is built that way, and where every piece of code lives. Read Chapters 1–4 first: they are the
rules every change must keep. The last three parts are **generated from the code itself** and list every API endpoint
(Reference A), every database model (Reference B) and every source file (Reference C).

| If you want to… | Read |
|---|---|
| Understand the system in an hour | Chapter 1 (architecture), Chapter 4 (security) |
| Change the backend | Chapter 2, then the app's section in Reference C |
| Change a screen | Chapter 3 |
| Add or change a business application | Chapter 5 |
| Build a kit, install or upgrade a shop | Chapter 6 |
| Work on Pay, the wallet app or the standalone Spare Parts | Chapter 7 |
| Set up your machine, test and release | Chapter 8 |
| Know what is not finished or not proven | Chapter 9 |

**Where the truth is.** When this handbook and a document under `docs/` disagree, the document wins for its topic:
architecture decisions in `docs/architecture/adr/`, permissions in `docs/security/PERMISSIONS.md`, threats in
`docs/security/THREAT_MODEL.md`, operations in `docs/operations/`. `CLAUDE.md` at the repository root holds the
standing engineering rules. Regenerate the three reference parts after any change (Chapter 8).
