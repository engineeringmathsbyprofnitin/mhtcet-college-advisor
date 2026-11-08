# Stage 10b - validating the real cutoff data, schema v0.4

Tool: `python -m ingestion.validate_cutoffs` (read-only; writes `data/normalized/validation_report.json`). Tests: `tests/test_stage10b.py` (10 tests).

## Result on the real data (7 State lists = 148,004 cells, 7 All India lists)
ERRORS: 0. Checked: percentile format/range, merit numbers, stage labels, choice code vs institute code, every institute / course / seat code / home university present in the master tables, one list per file, latest round per year (2026-27 IV, 2025-26 IV, 2024-25 III, 2023-24 III), only the current year plus the three before it.

## Documented oddities (kept exactly as printed, counted, never corrected)
1. **Conflicting cells**: 134 merit numbers carry two different percentiles inside one list (e.g. one with 71.7115000 and 73.6262684). They sit in different seat families (OPEN vs Ladies, PWD, Defence, EWS...).
2. **Merit number and percentile disagree in order**: in every list, about 1% of consecutive merit numbers have a higher percentile at the larger merit number (e.g. 968 -> 99.78 but 998 -> 99.79); 1,066 of these jump by more than half a percentile. So the printed merit number is NOT a single reliable ordering. Decision for the engine: use the printed **percentile** only; store the merit number but never compare students with it.
3. **Home university is blank in 34,978 State rows** (2023-24 to 2025-26 mostly). 33,859 of them belong to courses that print one single university in other lists; 1,119 belong to courses that never print one (mostly autonomous institutes). The rule for 10c: use the value printed in that row; if blank, use the course's single printed value and mark the row `home_university_inferred`; if the course has several values or none, mark the row "home university unknown" so the H/O sections are NOT matched for it.
4. **Colleges change home university over the years** (21 courses/institutes went from a university to "Autonomous Institute", e.g. 02114, 04135, 05106). 2,190 rows differ from the master's "latest" value. So the home university must be taken **per course and per year**, not once per college. One institute (02508) prints both values in the same list (per course).
5. All India: 6 rows with a blank score are kept blank.

## Schema v0.4 (database/schema.json, SCHEMA.md, templates, synthetic CSV headers)
`historical_cutoffs` and `current_cutoffs` gain optional columns `section`, `stage`, `merit_no`, `merit_exam`; their unique key now includes `section` and `stage`. Blank in the synthetic data. `build_schema.py` produces exactly this file.

## NOT verified
Why merit numbers and percentiles disagree (only the CET Cell can say); meaning of stages; whether blank home university in old lists means "not printed" or a parsing gap in those PDFs (not yet checked page by page).
