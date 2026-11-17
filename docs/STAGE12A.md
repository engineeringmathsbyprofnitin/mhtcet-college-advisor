# Stage 12a - fees (official source: Fees Regulating Authority, Maharashtra)

## 12a-1 Probe (built)
- Official source: the FRA portal `ay26-27.mahafraportal.org` page `ssi_prp_25/outer.php?q=fee_search_report` (public; the owner confirmed in a browser: no login/CAPTCHA seen; form = Institute Type "H&T", Sub Type "ENGG - Bachelor of Engineering", District; table = Inst ID, Inst Name, District, Stream, Status, Date of Meeting, Tuition Fee, Development Fee, Total Fee). Colleges' own copies of FRA pages are NOT used (not official hosts).
- FRA code "EN6283" = CET Cell institute 06283 (EN + 4 digits = CET code without the leading 0). Checked by name on 9 colleges; the real reader must still check every match by name and report mismatches.
- `ingestion/fra_probe.py` + workflow "Probe the fee portal" (by hand): at most 3 requests, robots.txt obeyed, stops at login/CAPTCHA, saves `data/raw/fees-probe/` (page.html, test_search.html, probe_report.json). `mahafraportal.org` was added to the official host list in `ingestion/http_client.py`; the client can now send a form POST.
- Tests: `tests/test_stage12a1.py` (12, offline).
- NOT verified: how the live page really works (plain form or JavaScript); that is what the probe reports.

## Next
12a-2 read all engineering fees (per district or all) with completeness checks; 12a-3 match to colleges, show on cards (fee basis: FRA approved total fee = tuition + development, base year-1 fee; categories, hostel and other charges are not included).
