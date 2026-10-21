# Project status

## Completed
- Stage 1: repository structure and documents.
- Stage 2: student input form (frontend/). Verified by 10 automated jsdom checks; real phone/desktop look to be confirmed by owner.
- Stage 3: database schema (15 tables), CSV templates, validator, SYNTHETIC test data.

## Verified (Stage 3)
- database/validate_data.py reports 0 errors on data/synthetic.
- 19 unit tests pass (tests/test_stage3_schema.py): clean data passes; bad percentile, vacancy round I, seat-matrix used as vacancy source, vacancy above intake, negative vacancy, duplicate rows, unknown college, missing required, unlabelled estimate, bad dates/years and two last-known-good versions are all rejected.
- While building, the validator caught a genuine bug in the synthetic generator (a reference to a non-existent branch), which was fixed.

## NOT verified / not implemented
- No real CET Cell data has been used anywhere. Synthetic data proves only that the schema and validator work.
- Recommendation engine, Google Sheet, API, ingestion, workflows, deployment.

## Known issues / placeholders
- Seat types, categories, candidate types and branch names are provisional (see frontend/config.js and seat_types table).
- Schema may need small changes once real documents are parsed (Stage 9).

## Next task
Stage 4: recommendation engine + documented rules + tests on synthetic data.
