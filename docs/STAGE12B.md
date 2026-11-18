# Stage 12b - accreditation (NBA, then NAAC)

## 12b-1 Probe of the NBA site (built)
- Official source: National Board of Accreditation, `www.nbaind.org` > Accredited Programs > Engineering (UG Tier I (WA), UG Tier II, PG, Diploma). The owner saw in a browser (2026-11-18): no login, no CAPTCHA; a search form (State, Program, Institute Name, Search), a "Click here to Download in Excel" button, and a table with Name of the Institution, Program, Level, Accreditation Status, Accreditation Period (example period text: "Accredited for Academic Year 1st July 2025 to 31st December 2025 and from 1st January 2026 to 31st December 2028").
- NBA accredits PROGRAMS, not whole colleges (NBA's own policy): a college is never shown as "NBA accredited" as a whole; the card column is per program (branch), and a program must be matched to the CET branch of that college.
- The page addresses carry long coded values (ID=..&tier=..&name=..), so the probe finds the links from the site's own pages. `ingestion/nba_probe.py` + workflow "Probe the NBA site" (by hand): at most 6 requests, robots.txt obeyed, stops at a login/CAPTCHA on the data page, submits no search, saves `data/raw/nba-probe/` (home.html, program_page.html, probe_report.json). `nbaind.org` added to the official host list.
- Tests: `tests/test_stage12b1.py` (12, offline).
- NOT verified: how the live pages really work (plain HTML, form posts, the Excel link).

## Next
12b-2 read the NBA lists (Tier I and Tier II, Maharashtra) with completeness checks; 12b-3 match institutions and programs to the website's colleges and branches by name (owner confirms doubtful pairs), parse validity periods, show on cards; then NAAC.
