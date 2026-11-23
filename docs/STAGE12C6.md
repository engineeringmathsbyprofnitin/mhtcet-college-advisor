# Stage 12c-6: the workflow "Read the NAAC list"

File: `.github/workflows/read-naac.yml` (the owner pastes it by hand; a copy is delivered as `workflow_read-naac.yml`).

## Starts
- by hand (Actions tab -> Read the NAAC list -> Run workflow);
- when something changes in `data/manual/naac/`, `data/manual/naac_confirmations.csv` or `data/manual/naac_transition_confirmations.csv`.
It does NOT start "Publish website data (preview)" (tests/test_stage10c3c.py pins the list of workflows that start it). After it, run the publish workflow by hand.

## Steps
1. Self-tests (offline): tests/test_stage12c2.py, 12c3, 12c4 (stdlib only; no openpyxl needed).
2. `ingestion.naac_import`: reads the ONE .xlsx in data/manual/naac/ (refuses two files, a missing date in the file name, bad grades/dates). If it reports a problem the step fails and nothing is saved.
3. `ingestion.naac_match`: pass 1 colleges -> graded records, pass 2 colleges without a grade -> transition rows.
4. `ingestion.build_accreditation`: rebuilds tables/accreditation*.csv (NBA rows are kept; they are read from data/normalized/nba*).
5. Saves data/normalized/naac, naac_link and tables/accreditation* in the repository (only if something changed).

## Tested
tests/test_stage12c6.py pins triggers, step order, files saved, and that the publish workflow does not start from it. The three Python steps were run on a clean copy with openpyxl/pandas/numpy blocked: all succeeded and only `build_date` in accreditation_build_report.json changed.
## Not verified
The real run on GitHub (done by the owner).
