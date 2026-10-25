# Project status

## Completed
- Stage 1: repository structure and documents.
- Stage 2: student input form (frontend/). 10 automated checks passed; real phone/desktop look still to be confirmed by owner.
- Stage 3: database schema v0.3 (16 tables), validator, SYNTHETIC test data. 28 tests pass.
- Stage 4: recommendation engine v0.2 (+ sorted seat-type list fix), 47 tests pass.
- Stage 5 (optional now): Google Sheet workbook + Apps Script API, 22 tests pass in simulation. Owner decided NOT to depend on it (see docs/DECISIONS.md).
- Stage 5B: static data publisher (database/export_static.py), browser loader (frontend/dataloader.js), published synthetic data (frontend/data/), data-check page (frontend/data-check.html).

## Verified (Stage 5B, automated)
- Exporter: 15 tests pass (refuses invalid data and leaves old files untouched, only validated rows published, hashed file names match manifest, deterministic output, old files cleaned up, intake not published, unsafe seat-type codes rejected).
- Loader: 13 tests pass (answers identical to the engine on the full tables for 9 different students, only needed files downloaded, tampered/missing/damaged files rejected, one retry, manifest requested fresh, missing seat-type file treated as no data).
- Earlier suites re-run with the updated engine: Stage 4 (47) and Stage 5 Apps Script (22) pass.
- Stress test: synthetic data scaled to 4,740 choices / 110,220 cutoff rows ran in about 0.2 s in Node.

## NOT verified
- The pages in a real browser and on a real phone (owner: docs/STAGE5B_SETUP.md steps 5-8).
- Real data size and phone speed (estimates in docs/STATIC_DATA.md; to be measured in Stage 9).
- No real CET Cell data anywhere. Weights/thresholds uncalibrated. Reserved-can-use-Open-seats is an assumption. TFWS/Defence/PWD not applied.
- Form still not connected to the engine (Stage 6).

## Known issues / placeholders
- Seat types, categories, candidate types and branch names are provisional.
- Publishing is a manual command until Stage 14 automates it.

## Next task
Stage 6: connect the form to the loader and show the results table.
