# Stage 14c: daily schedule and a publish run that stays quiet when nothing changed

Owner's decision (2026-11-24): option A, daily. During CAP the option-form windows last only a few days, so a weekly delay of up to 6 days is too long.

## Schedule (UTC; India = UTC + 5:30)
| Workflow | When | Before |
|---|---|---|
| Discover and archive official documents | every day 03:17 | Mondays 03:17 |
| Read institute information | Mondays 04:15 | unchanged (rarely changes, many requests) |
| Read the archived documents | every day 04:47 | Mondays |
| Read the vacancy lists | every day 05:07 | Mondays |
| Read the approved fees | Mondays 05:30 | unchanged (rarely changes, many requests) |
| Publish website data (preview) | **every day 06:30** (12:00 in India) | started after each reader (up to 4 runs a Monday) |
So a list that CET Cell publishes on a Wednesday is on the preview page the next day around noon (India), not the following Monday. "Read the NBA lists" and "Read the NAAC list" still start by hand or when you upload a file; their results are published by the next daily run.

## The publish run
Same steps as before (tests, plan, validate, build tables, fees, vacancy, package, replace, save). New: it is no longer started by other workflows, and a **guard** (ingestion/publish_guard.py) compares the new build with the published folder IGNORING the time stamps that change with every discovery run (data_version.created_at, refresh_status.started_at/finished_at, manifest.last_successful_update). If nothing else differs, the published files are kept: no commit and browsers keep their cached copies. If anything real differs (a table value, a cutoff file, the admission year), the folder is replaced as before. Unreadable or missing published data counts as changed. A failed step never replaces anything.
Expected daily noise in the repository: one small commit "Update source discovery and document archive reports" (the discovery report carries the run time). No commit from the publish run on quiet days.

## Cost
The repository is public, so GitHub Actions minutes are free. (If it were private the daily runs would use roughly 30-40 minutes a day.)

## Changed tests (deliberate)
tests/test_stage10c3c.py and tests/test_stage12c6.py no longer expect `workflow_run`; they expect a daily schedule. New tests/test_stage14c.py (8 guard tests, 4 schedule tests).

## Owner steps
1. Upload ingestion/, tests/, docs/ from the zip FIRST (the new workflow uses publish_guard).
2. Then replace the four workflow files by hand in the GitHub web editor (the folder .github/workflows is hidden on your computer): open each file with the pencil icon, replace everything with the text of the matching `workflow_*.yml` of the zip, Commit.
3. Run "Publish website data (preview)" by hand once and check the step "Has anything really changed?" (the log should say changed or unchanged), then run it a second time: it should say unchanged and make no commit.

## Not verified
The first scheduled runs on GitHub (cron times are not exact; GitHub may start them some minutes late, so 06:30 leaves about an hour after the last reader).
