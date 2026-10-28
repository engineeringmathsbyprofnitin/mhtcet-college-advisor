# Project status

## Completed and owner-verified
Stages 1-4, 5B (static data files; 473 ms computer / 886 ms phone) and 6 (form -> ranked report; owner ran the checklist and it behaved as described).

## Stage 7 DONE and verified live (27 Oct 2026)
- ingestion/admission_year.py: decides the current admission year from evidence; previous three years; statuses confirmed / previous_cycle_latest / new_cycle_announced / newer_documents_unreachable / unknown.
- ingestion/classify.py: cutoff, vacancy position, ACAP list, seat matrix, etc.; round, group (MH / AI / Diploma), year, qualifiers, reasons.
- ingestion/html_extract.py: links with menu and table context (colspan / rowspan).
- ingestion/http_client.py: polite fetcher (robots.txt, allow-list of official hosts, no redirects off-list, pacing, limited retries, request cap).
- ingestion/discover.py: orchestrates discovery, checks reachability with HEAD only, writes data/raw/discovery/latest.json (keeps the last good report if a run fails), step summary.
- .github/workflows/discover-sources.yml: manual + weekly run.
- docs/CETCELL_SOURCES.md: what the official portals look like (observed 26 Oct 2026).

## Verified (automated)
87 Stage 7 tests pass (year logic 17, classifier/reader 20, simulated-site discovery 43, workflow file 7): happy path with 41 documents, correct matrix and strict selection preview, robots.txt obeyed, CAPTCHA/password/403/503/timeouts handled, redirects off the allow-list not followed, request cap enforced, unreachable documents not counted as evidence, between-cycles behaviour, missing previous year chased through its own pages, failed run keeps the last good report. The workflow YAML was parsed and checked (a real syntax error was found and fixed).

## Live result (owner ran the GitHub Action)
Status ok, 47 requests, no obstacles, robots.txt read and obeyed; 41 documents found exactly as predicted; current year 2026-27 confirmed, cutoff round IV, vacancy round IV; previous years 2025-26 / 2024-25 / 2023-24. Bug found: previous-year files reported 404 because that server answers 404 to HEAD requests; fixed with a one-byte GET fallback (tests reproduce it). Second live run confirmed the fix: status ok, 48 requests, 41 documents, 0 unreachable (15 opened by the quick check, 26 by the one-byte fallback).
A second defect was found from the run page: the self-tests (which pretend the site is down) had been writing their pretend 'failed' reports into the real GitHub summary page. Fixed: the summary is now written only by the real run (`--github-summary`), with a test. The report now also records each file's true size (needed to plan Stage 8 downloads), and the workflow uses current action versions on a pinned Ubuntu 24.04 runner.

## NOT verified
- No document has been downloaded or parsed yet (Stages 8-9). Discovering a link is not the same as parsing it.
- Earlier caveats still apply: no real data in the recommendation engine; uncalibrated weights; reserved-can-use-Open-seats assumption; TFWS/Defence/PWD not applied.

## Open questions (docs/CETCELL_SOURCES.md)
Which list counts as the Round IV vacancy (provisional position vs after-CAP ACAP list); Diploma lists; how OMS/J&K/Defence candidates appear in the cutoff lists.

## Next task
Owner runs the live discovery; I fix whatever differs from the real site; then Stage 8 (download + archive).
