# Stage 10d - district (and more) from the official Institute Summary pages

## Owner feedback this answers
1. "I chose Satara but got other districts." Cause: the cutoff lists print no district, so the website had none and said so ("District data is not available yet ..."). Not a bug, a missing source. Fixed here by reading the official source.
2. "Top blue text says last updated unknown." Cause: the data files on the preview were built before the refresh-status row existed (fixed in the 10c-3e zip), and the exporter had no fallback. Now the stamp comes from the refresh-status row and, if that is missing, from the data version's creation time. After you re-run "Publish website data" it shows a date.

## The official source (checked on the live site)
`fe2026.mahacet.org/StaticPages/frmInstituteList` lists all 387 participating institutes and links each to `frmInstituteSummary.aspx?InstituteCode=NNNNN`. That page prints Institute Address, **Region, District**, Status, Autonomy Status, Minority Status, and a Course Details table: choice code, course name, **University**, status, autonomy, minority status, shift, accreditation (shown as "-" for the one page I read), gender, total intake. Example read: 06270 = Karmaveer Bhaurao Patil College of Engineering, Satara: Region Pune, District Satara.

## What was built
- `ingestion/institutes.py` (`python -m ingestion.institutes`): reads the list and every institute page (official host only, robots.txt, ~1 request per second, no login/CAPTCHA bypass - a wall stops the run), records each page's SHA-256 and URL, checks that the number of codes found equals the count printed, that each page is for the code asked, that district/name exist, every course belongs to the institute and has a numeric intake. Output `data/normalized/institutes/` (institutes.csv, institute_courses.csv, report) is replaced ONLY if every institute was read completely.
- `.github/workflows/read-institutes.yml` ("Read institute information"): by hand and every Monday 04:15 UTC; "Publish website data" now also starts after it.
- `build_tables`: colleges get their official district, status, autonomy; each college's provenance is its Institute Summary page (a source document of type college_list). For rows whose home university was blank, the current-year university from the course table is used (label `institute_page`) when it is a known university.
- The form offers exactly the districts found in the data (instead of the built-in list) once they exist; a district choice then filters. Colleges without a district are still included under "Any district".

## Tests
tests/test_stage10d.py (14) and tests/test_stage10c3c.py (+3 workflow tests). **The test pages are RECONSTRUCTED from the page text the CET Cell website shows; the real HTML may differ, so the first live run is the real test.** If the real HTML is different the run stops with a clear list of problems and keeps the old files.

## NOT verified
- The real page HTML; the first run on GitHub (about 8 minutes). Whether every institute page prints a district. Whether the "Accreditation" column carries NBA/NAAC data (only "-" seen); not used yet.
- District spellings are used exactly as printed (e.g. a district renamed by the government may appear under one name only).

## First live run (owner report): "request budget of 600 used up"
The reader stopped after 600 requests (about 21 minutes) with no information. What is known: the list page was read and passed its count check, then the run made 600 requests; the pages number about 387, so roughly 1.5 requests were made per institute, which points to many retried requests (timeouts or temporary server errors), not to missing pages. What is NOT known: the exact server answers (the first version logged nothing). Fixes in this version:
- request budget follows the list (4 per institute + 20; retries count) and running out is caught and reported instead of crashing;
- every failed page is printed with its reason and number of attempts, progress every 25 institutes; `institutes_last_run_report.json` is always saved (and attached to the run);
- gentler pace: 2 seconds between requests, up to 3 retries; a time limit of 40 minutes stops the run cleanly;
- **quick probe**: Actions -> Read institute information -> Run workflow -> probe = 5 reads only the list and 5 pages (a minute) and shows what the site answers; nothing is saved. Use it first.
Tests added (5): budget follows the list, budget exhaustion caught, failures logged with reasons, probe, time limit.
