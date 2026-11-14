# Stage 11b - vacancy tables and the "Read the vacancy lists" workflow

Code: `ingestion/read_vacancy.py`; workflow: `.github/workflows/read-vacancy.yml`; tests: `tests/test_stage11b.py` (13 tests).

- Selection rule (owner): Round IV vacancy position (seats open going into Round IV), else Round III (going into Round III); one round per admission year; never Round I/II; never the ACAP after-CAP list or court-order lists; never the seat matrix. If the Round IV file is listed but not stored yet, that year is BLOCKED and reported - there is no silent fall-back to Round III.
- Output (built in `build/`, copied to `data/normalized/vacancy/` only if everything is complete and problem-free): `<year>_round-<R>_vacancy.csv.gz` (one row per Choice Code; intake in its own column `intake_si`; `vacant_cap_seats` = printed value; `ms_seats`, `minority_seats`, `all_india_seats`, `institute_seats`, orphan seats, grid totals, PWD/DEF, EWS, TFWS code and seats, `grid_json` = the per-category General/Ladies cells) and `vacancy_report.json`.
- Dry run on the real manifest and Round IV PDF in the sandbox: 2,335 rows, 387 institutes, 1,013 of 1,013 pages, vacant total 23,107, table 64 KB.
- On failure the log line to paste is the first line starting with `FAIL:`.
- NOT done yet (11c): matching Choice Codes to website course keys, the year choice from the automatic plan, and showing it on the page.
