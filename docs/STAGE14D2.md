# Stage 14d-2: rehearsal of the admission-year rollover (pretend data, temporary folders)

tests/test_stage14d2.py builds two pretend situations with the REAL builders and the REAL packaging, never touching real data folders, and tests/rollover_rehearsal.test.js loads the packaged data with the real engine and the real banner functions of frontend/app.js:
1. **15 January 2027** (new admission year 2027-28, no 2027-28 cutoff list yet): plan admission 2027-28 / cutoffs 2026-27; packaged data says admission=2027-28; the banner is the Round I option-form text; every result uses 2026-27 cutoffs (Round IV for most choices, an earlier 2026-27 round for the few that have no Round IV row); history years 2025-26, 2024-25, 2023-24; NO vacancy on any card; fees still shown but labelled 2026-27.
2. **20 July 2027** (Round I of 2027-28 published; PRETEND rows: the 2026-27 Round I rows relabelled 2027-28 become the current year, the 2026-27 Round IV rows join the history, 2023-24 leaves it): current year 2027-28 with Round I only (Round II expected next); history years 2026-27 (last round IV), 2025-26, 2024-25; no vacancy; fees labelled 2026-27, never 2027-28.

## Bug found by the rehearsal (fixed)
Once Round I of 2027-28 is published, the cutoff year is 2027-28 too, and the fee builder looked for a fee list only for the admission year and the cutoff year, both 2027-28. With no 2027-28 FRA list yet, ALL fees would have disappeared from the cards. Now the fee builder uses the admission year's list if it exists, otherwise the newest EARLIER list (never a later year's); the weekly fee reader likewise keeps re-reading the newest known FRA address up to the admission year and prints ACTION NEEDED. Tests added to tests/test_stage14b.py (3).

## FRA address of a new year
Not probed: this sandbox cannot reach the FRA portal. The address pattern differs each year, so it is still a one-line edit that the owner asks for once a year (docs/RECOVERY.md). A probe workflow could look for a link from the FRA portal's home page; I have not verified that such a link exists.

## Tests
tests/test_stage14d2.py (4 tests) + tests/rollover_rehearsal.test.js (3 tests, started by the Python test), tests/test_stage14b.py (+3 +1). Also run with openpyxl/pandas/numpy blocked.
## Not verified
The real switch on 1 January 2027 (only simulated); the phone view of the banner.
