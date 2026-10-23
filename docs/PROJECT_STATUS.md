# Project status

## Completed
- Stage 1: repository structure and documents.
- Stage 2: student input form (frontend/). 10 automated checks passed; real phone/desktop look to be confirmed by owner.
- Stage 3: database schema v0.3 (16 tables), templates, validator, SYNTHETIC test data. 28 tests pass.
- Stage 4: recommendation engine (recommendation/engine.js), rules in docs/RANKING_RULES.md, 46 tests in tests/engine.test.js; rules v0.2.

## Verified (Stage 4)
- 46 of 46 tests pass (Node.js, synthetic + small hand-made datasets): admission-year calculation, 3-year history window, round priority IV>III>II>I, vacancy IV-else-III only (no mixing, no Round I/II, seat matrix rejected, zero vs missing), seat-type matching, branch/district filters and renamed districts, fee filtering (tuition vs total), labels and thresholds, trend handling, priority-based ranking, missing data, accreditation validity, NBA program scope, ignoring unvalidated rows, result limits and honest messages, determinism, input not modified.
- Engine loads and runs outside Node (simulated Apps Script/browser environment).
- A sample student on synthetic data gave a sensible, explainable ranking.
- v0.2 review fixes: (1) percentile gaps near the top are scaled up, (2) earlier current rounds get lower weight, (3) small evidence-coverage factor so missing data cannot win near-ties. Each has tests.

## NOT verified / not implemented
- No real CET Cell data used anywhere. Passing tests prove the rules are coded as written, not that real data is handled correctly.
- Thresholds and weights are not calibrated.
- Not yet connected to a Google Sheet, API or the web form (Stages 5-6).
- Extra eligibility (TFWS/Defence/PWD) not applied. Whether reserved-category students may use Open seats is an assumption to verify.

## Known issues / placeholders
- Seat types, categories, candidate types and branch names are provisional.
- Schema may need small changes once real documents are parsed (Stage 9).

## Next task
Stage 5: Google Sheet setup + Apps Script API.
