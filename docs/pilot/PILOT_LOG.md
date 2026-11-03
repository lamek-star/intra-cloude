# Own-shop pilot log

Keep one row per issue, on this page, on paper or in a spreadsheet. **Severity:** **P0** data loss, a security problem, or
nobody can trade; **P1** a main shop workflow is broken; **P2** a significant inconvenience or slowness; **P3** minor
polish. P0/P1 are fixed **before** IntraForge becomes the shop's only record. Report P0 the same day.

## Issue log

| Date / time | Who | Workflow | What was attempted | Expected | Actual | Sev. | Diagnostics (status file / screenshot) | Workaround | Fixed? |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
|  |  |  |  |  |  |  |  |  |  |

## Timing and outliers (write every slow moment; never average it away)

Note the time of any action that felt slow (more than about 2 seconds), what it was, and press **Diagnostics** in the
IntraForge Control Center right away; keep the zip. Earlier observation, now explained and fixed in shop kit 1.1: ~2-second waits came from `localhost` resolving to
IPv6 `::1` first while IntraForge listened on IPv4 `127.0.0.1` only (Windows retries a refused connection for ~2 s); it
now listens on both loopback addresses (measured 2,100 ms -> 17-43 ms per request).

| Date / time | Action (search / open product / receive / sell / file / start) | Seconds (about) | Status file |
| --- | --- | --- | --- |
|  |  |  |  |

## Daily reconciliation

| Date | Sales in IntraForge | Sales in the existing records | Stock counts checked (item: shelf / IntraForge) | Differences and reason | Backup done and copied? |
| --- | --- | --- | --- | --- | --- |
|  |  |  |  |  |  |

## Measurements to record during the pilot

Start-up time after sign-in; backup duration (`C:\IntraForgeData\logs\backup.log`); memory in use (Status); free disk (Status);
search / open / receive / sale speed as you feel it, plus every outlier above.
