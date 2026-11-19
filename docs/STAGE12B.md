# Stage 12b - accreditation (NBA, then NAAC)

## 12b-1 Probe of the NBA site (built)
- Official source: National Board of Accreditation, `www.nbaind.org` > Accredited Programs > Engineering (UG Tier I (WA), UG Tier II, PG, Diploma). The owner saw in a browser (2026-11-18): no login, no CAPTCHA; a search form (State, Program, Institute Name, Search), a "Click here to Download in Excel" button, and a table with Name of the Institution, Program, Level, Accreditation Status, Accreditation Period (example period text: "Accredited for Academic Year 1st July 2025 to 31st December 2025 and from 1st January 2026 to 31st December 2028").
- NBA accredits PROGRAMS, not whole colleges (NBA's own policy): a college is never shown as "NBA accredited" as a whole; the card column is per program (branch), and a program must be matched to the CET branch of that college.
- The page addresses carry long coded values (ID=..&tier=..&name=..), so the probe finds the links from the site's own pages. `ingestion/nba_probe.py` + workflow "Probe the NBA site" (by hand): at most 6 requests, robots.txt obeyed, stops at a login/CAPTCHA on the data page, submits no search, saves `data/raw/nba-probe/` (home.html, program_page.html, probe_report.json). `nbaind.org` added to the official host list.
- Tests: `tests/test_stage12b1.py` (12, offline).
- NOT verified: how the live pages really work (plain HTML, form posts, the Excel link).

## 12b-1 result: the NBA site refuses our robot
The probe workflow got HTTP 403 (118 bytes) on the first page (robots.txt said allowed). Rule: stop, never bypass (no browser disguise). Decision: the owner downloads the official Excel lists in his own browser (button "Click here to Download in Excel") and puts them in `data/manual/nba/`. The probe workflow stays only for the record (it is not needed again; it would get the same 403).

## 12b-2 Read the NBA lists (built)
- `ingestion/nba_import.py` (stdlib-only .xlsx reader), workflow "Read the NBA lists" (by hand and when `data/manual/nba/**` changes), tests `tests/test_stage12b2.py` (31). Input: `data/manual/nba/sources.csv` (file, tier, downloaded_on, note) + the .xlsx files. Output (only if everything read cleanly): `data/normalized/nba/nba_programs.csv`, `nba_report.json`.
- The owner's two files (State = Maharashtra, 2026-11-18): UG Tier I (WA) 258 rows / 42 institutions and UG Tier II 1,253 rows / 196 institutions; together 1,511 rows, 217 institutions, 113 program names, 1,081 (institution, program) pairs. Level "Under Graduate"/"UG". The files do not name the tier (recorded from the owner's choice).
- Period text (20+ free-text styles): the latest printed end date ("upto DD/MM/YYYY", "i.e. DD-MM-YYYY", or a long-form date range); for "N YEARS W.E.F. <date>" (many spellings, 701 rows) the start is the printed date and the end is COMPUTED as start + N years - 1 day and labelled `computed` in `validity_basis` (a decision of the assistant, to be reviewed: otherwise programs accredited in 2002-2016 would show "validity not known" instead of "expired"); an implausible year (a printed typo such as 2202), an academic-years-only text or no date -> the row is kept WITHOUT dates and reported (3 rows), never guessed; impossible calendar dates fail the run. An unknown status (PROVISIONALLYACCREDITED, 1 row) is stored as `unknown`, never as accredited or not accredited. Programs often appear several times (older and newer cycles): all kept, the newest is used when matching.
- Institution text "Name (Place)": place `--Select--` = unknown; the export's repeated apostrophes are collapsed.
- NOT verified: that the two Excel downloads are the complete Maharashtra lists.

## Next
12b-3 match institutions and programs to the website's colleges and branches by name (owner confirms doubtful pairs), parse validity periods, show on cards; then NAAC.
