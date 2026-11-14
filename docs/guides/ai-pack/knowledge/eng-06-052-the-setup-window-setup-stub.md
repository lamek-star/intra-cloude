# Chapter 6 — The shop kit: build, install, upgrade, operate — The Setup window (`setup-stub/`)

Topic for: software engineers. Source: IntraForge Engineering Handbook, Chapter 6 — The shop kit: build, install, upgrade, operate.

An 880×560 borderless window (`Ui/SetupForm.cs`, `Ui/Pages.cs`) over a self-extracting payload (`Payload.cs`: reads the
trailer, checks each part's SHA-256, unpacks). Modes: interactive, `/quiet`, `/check`, `/extractonly`,
`/uipreview=<screen>`. A fresh staging folder is used if an old one is still held open by another process.
