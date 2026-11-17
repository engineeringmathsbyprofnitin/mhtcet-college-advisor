# Stage 12a - fees (official source: Fees Regulating Authority, Maharashtra)

## 12a-1 Probe (built)
- Official source: the FRA portal `ay26-27.mahafraportal.org` page `ssi_prp_25/outer.php?q=fee_search_report` (public; the owner confirmed in a browser: no login/CAPTCHA seen; form = Institute Type "H&T", Sub Type "ENGG - Bachelor of Engineering", District; table = Inst ID, Inst Name, District, Stream, Status, Date of Meeting, Tuition Fee, Development Fee, Total Fee). Colleges' own copies of FRA pages are NOT used (not official hosts).
- FRA code "EN6283" = CET Cell institute 06283 (EN + 4 digits = CET code without the leading 0). Checked by name on 9 colleges; the real reader must still check every match by name and report mismatches.
- `ingestion/fra_probe.py` + workflow "Probe the fee portal" (by hand): at most 3 requests, robots.txt obeyed, stops at login/CAPTCHA, saves `data/raw/fees-probe/` (page.html, test_search.html, probe_report.json). `mahafraportal.org` was added to the official host list in `ingestion/http_client.py`; the client can now send a form POST.
- Tests: `tests/test_stage12a1.py` (12, offline).
- NOT verified: how the live page really works (plain form or JavaScript); that is what the probe reports.

## 12a-1 result (probe ran)
The page has no form: two buttons call plain GET addresses `admin/reports/ajax/get_sub_type_ajax.php?val1=HT` and `admin/reports/ajax/get_report_ajax.php?sub_type=..&district=..&institute=&type=HT`; the district list has an "All District" choice; no login/CAPTCHA words in the page; robots.txt: nothing disallowed. The page's introductory text still mentions 2023-2024 (old text; the table title says 2026-27).

## 12a-2 Read the fees (built, not yet run on the live portal)
- `ingestion/fra_fees.py`, workflow "Read the approved fees" (by hand + Mondays 05:30 UTC), tests `tests/test_stage12a2.py` (29, offline). Output `data/normalized/fees/fra_fees_<year>_engg.csv` (inst_id, cet_institute_code, name, district, stream, status, meeting date, tuition, development, total, whether total = tuition + development, source URL, retrieved date) and `fra_fees_report.json`; raw answer in `data/raw/fees/`.
- Checks: exactly one ENGG sub type; the table must have the 10 known columns; Sr. No. 1..N without gaps; stream ENGG; Inst ID like EN####; same institute twice with different numbers = FAIL; unreadable number/date = FAIL; missing number stays empty (never 0); a printed total that differs from tuition + development is kept as printed and flagged; a new status or extra rows are reported. Any FAIL keeps the previous data.
- The FRA address is per year (FRA_SITES); a year without an entry is not read (reported) - to be handled in the Stage 14 year rollover.
- NOT verified: the real answer of the portal (the table structure is taken from the owner's screenshot).

## Next
12a-3 match the fees to colleges by FRA code + name check, show on cards (basis: FRA approved total = tuition + development for the first year; categories, hostel and other charges not included); 

## Phone layout fix (Stage 11d follow-up)
On phones the lines inside one cell (value, round figures, warnings) were laid side by side and ran out of the card. Each cell's lines now sit in one inner box (`.cv`) that stacks and wraps (`frontend/results.js`, `frontend/styles.css`); test added to `tests/ui_stage6.test.js`. Not seen on a real phone yet.
