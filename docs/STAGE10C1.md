# Stage 10c-1 - the automatic data plan (nothing hard-coded to one year)

Answer to "will the system detect the admission year and rounds by itself?": yes. The year decision already exists (Stage 6/7, `ingestion/admission_year.py`, saved in `data/raw/discovery/latest.json`; it uses published cutoff documents as evidence, not the calendar). Stage 10c-1 connects the data checks to it.

`python -m ingestion.plan` -> `data/normalized/data_plan.json`:
- current year (e.g. 2026-27), rounds done (I-IV), latest round, next round expected (none after Round IV);
- history = the three years before it, each with its last published round (today: 2025-26 IV, 2024-25 III, 2023-24 III);
- list of cutoff lists the website needs: ALL published rounds of the current year (students may see I-IV) + one list per history year.

`python -m ingestion.validate_cutoffs` now takes its expectations from this plan. New errors: PLANNED_LIST_NOT_PARSED (a round/year the plan needs has not been read: e.g. when Round I of 2027-28 appears), YEAR_OUTSIDE_PLAN. When a new year or round is published and discovered, the plan changes by itself and the check tells us what is still missing.

Tests: `tests/test_stage10c1.py` (6: real decision, mid-cycle next round, a new year 2027-28, history year with no cutoffs, year not established, previous-cycle status) and updated `tests/test_stage10b.py`.

## Not yet done (next parts)
- Wiring plan + validator into the weekly GitHub workflow (Stage 14 scheduled publish).
- 10c-2: build engine tables from the real data (per-course and per-year home university, closing figure per seat/section/round) and static files.
- 10c-3: engine matching, form (home-university dropdown, real categories), "data version / last updated" stamp.
## Not verified
"Next round expected" is only the next number in order; the CET Cell may announce extra or special rounds.
