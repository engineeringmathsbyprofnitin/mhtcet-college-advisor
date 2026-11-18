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
- The owner's first file (UG Tier I (WA), State = Maharashtra, 2026-11-18): 258 rows, 42 institutions, 50 program names, all ACCREDITED, level "Under Graduate"/"UG". The file itself does not name the tier (recorded from the owner's choice).
- Period text (20+ free-text styles) -> dates only when printed: latest "upto DD/MM/YYYY" or a long-form date range; "3 YEARS W.E.F. <date>" gives a start date and NO end date (4 rows: validity not known); unreadable text is a warning and the row is kept without dates; impossible dates fail the run. 254 of 258 rows have an end date. 59 programs appear twice (an older and a newer cycle): both kept, the newest is used when matching.
- Institution text "Name (Place)": place `--Select--` = unknown; the export's repeated apostrophes are collapsed.
- NOT verified: that this one Excel is the complete Maharashtra Tier I list; the Tier II list (and PG/Diploma, not needed) has not been supplied yet.

## Next
12b-3 match institutions and programs to the website's colleges and branches by name (owner confirms doubtful pairs), parse validity periods, show on cards; then NAAC.
