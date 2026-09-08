# SBOM retrieval and release handling

Verified 2026-09-08 against CI run `34205104070`, commit
`da9f5b50bbc10e6f1b5dd322a4e72bc88c6d85b1`. This is not CI evidence
for the subsequent local restore commit.

The `security-scan` job in `.github/workflows/ci.yml` builds backend and
frontend images, then uses `anchore/sbom-action@v0` to generate three
CycloneDX JSON documents: backend image, frontend image, and frontend
source dependency inventory. All three are uploaded as the `sboms` artifact.
The downloaded documents declare CycloneDX 1.6. A source inventory is not
a complete inventory of the Windows appliance, Ubuntu rootfs, or all
third-party infrastructure images.

## Retrieve an existing inventory

1. Open the repository's Actions page and select the CI run for the exact
   commit being reviewed. Confirm the `SBOM and container image scan` job
   succeeded, not merely that a workflow was started.
2. Download `sboms` under Artifacts, or use authenticated GitHub CLI:

   ```powershell
   gh run view 34205104070 --json headSha,conclusion
   gh run download 34205104070 -n sboms -D ./sboms-34205104070
   ```

3. Check each JSON document's `bomFormat`, `specVersion`, `metadata`, and
   `components`. Preserve the run URL and commit alongside the documents.
   Compare image identities with the actual release images; do not attach
   an older run's inventory to a newly rebuilt image and imply equivalence.

The workflow has no explicit `retention-days`. The inspected artifacts
were created September 8 and expire December 7, 2026 (90 days from run
creation). That observed retention is not a permanent archival guarantee;
repository policy can change and runs can be deleted.

## New generation and distribution

CI runs on pull requests and pushes to main/master. There is no manual
dispatch trigger in `ci.yml`; an ordinary local build alone does not create
these artifacts. Use the CI job's declared generation steps when reproducing
locally, with the exact images being inventoried. No new scan was required
for this retrieval verification.

Before release, retain the exact release inventories with the release
artifacts and checksums in durable storage. `Build-ReleaseBundle.ps1` does
not currently copy SBOMs into the offline bundle, and no workflow publishes
them as permanent GitHub Release assets. This automation remains open.

Status: **SBOM AUTOMATION COMPLETE** for the three configured CI outputs;
operator retrieval documentation complete. Full-appliance inventory and
automatic release attachment remain **OPEN / INCOMPLETE**. Vulnerability
reports and license policy enforcement are separate from SBOM generation.
