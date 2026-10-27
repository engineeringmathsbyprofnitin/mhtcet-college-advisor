# Project status

## Completed and owner-verified
Stages 1-4, 5B (static data files; 473 ms computer / 886 ms phone) and 6 (form -> ranked report; owner ran the checklist and it behaved as described).

## Stage 7 built (code + simulated-site tests); live run pending
- ingestion/admission_year.py: decides the current admission year from evidence; previous three years; statuses confirmed / previous_cycle_latest / new_cycle_announced / newer_documents_unreachable / unknown.
- ingestion/classify.py: cutoff, vacancy position, ACAP list, seat matrix, etc.; round, group (MH / AI / Diploma), year, qualifiers, reasons.
- ingestion/html_extract.py: links with menu and table context (colspan / rowspan).
- ingestion/http_client.py: polite fetcher (robots.txt, allow-list of official hosts, no redirects off-list, pacing, limited retries, request cap).
- ingestion/discover.py: orchestrates discovery, checks reachability with HEAD only, writes data/raw/discovery/latest.json (keeps the last good report if a run fails), step summary.
- .github/workflows/discover-sources.yml: manual + weekly run.
- docs/CETCELL_SOURCES.md: what the official portals look like (observed 26 Oct 2026).

## Verified (automated)
80 Stage 7 tests pass (year logic 17, classifier/reader 20, simulated-site discovery 38, workflow file 5): happy path with 41 documents, correct matrix and strict selection preview, robots.txt obeyed, CAPTCHA/password/403/503/timeouts handled, redirects off the allow-list not followed, request cap enforced, unreachable documents not counted as evidence, between-cycles behaviour, missing previous year chased through its own pages, failed run keeps the last good report. The workflow YAML was parsed and checked (a real syntax error was found and fixed).

## NOT verified
- The live CET Cell site: my test pages were modelled on what a web page reader showed (menu, CAP page, engineering portal). The real HTML may differ in detail. The GitHub Action run is the real test (owner: docs/STAGE7_SETUP.md).
- robots.txt of the official hosts has not been read by the project yet.
- No document has been downloaded or parsed yet (Stages 8-9). Discovering a link is not the same as parsing it.
- Earlier caveats still apply: no real data in the recommendation engine; uncalibrated weights; reserved-can-use-Open-seats assumption; TFWS/Defence/PWD not applied.

## Open questions (docs/CETCELL_SOURCES.md)
Which list counts as the Round IV vacancy (provisional position vs after-CAP ACAP list); Diploma lists; how OMS/J&K/Defence candidates appear in the cutoff lists.

## Next task
Owner runs the live discovery; I fix whatever differs from the real site; then Stage 8 (download + archive).
