# Stage 14b: the admission year changes on 1 January (calendar rule)

Owner's rule (2026-11-24): the admission year changes automatically on 1 January of every year (2027-28 from 1 Jan 2027), not when Round I is published. The site must also help students fill the Round I option form.

## Why the cutoffs do NOT switch on 1 January
A cutoff list of a new year exists only after its CAP Round I allotment, which comes AFTER the Round I option form. Students filling the Round I form therefore need the cutoffs of the previous year (all four rounds) and the three years before it. So there are two years:
- **admission_year** = the year the student applies for = the calendar year on the day the plan is made (changes on 1 January).
- **cutoff_year** (also kept as `current_year` for older code) = the newest year with published, reachable cutoff lists (changes when its Round I cutoff list appears). Not changed in this stage.

## What changed
- ingestion/plan.py: new fields `admission_year`, `cutoff_year`, `admission_year_has_cutoffs`; main() uses the day the plan is made, so any publish run after 1 January switches the label at once.
- ingestion/build_vacancy.py: vacancy only for the admission year; last year's vacancy is never shown as this year's (cards say "Vacancy data unavailable" until the new Round IV/III vacancy list exists).
- ingestion/build_fees.py: the fee list of the admission year if it exists, otherwise the newest earlier list; every card already shows the year of its fee ("... · 2026-27"). Never presented as the new year's fee.
- ingestion/fra_fees.py: when the FRA portal address of the new year is not in FRA_SITES, the weekly run keeps reading the newest known list and prints "ACTION NEEDED: add the address ..." (no red failure); with no address at all it still fails.
- ingestion/package_real.py + frontend/app.js: the page is told `admission=<year>`; when it is ahead of the cutoff year the banner says: "Admission year 2027-28: its cutoff lists are published only after the CAP Round I allotment ... these results use the cutoffs of 2026-27 (CAP rounds I, II, III, IV) and the three years before it. They are last year's figures, not a prediction ...".
- Not changed: the engine, the cutoff plan and the history rule (3 previous years, last round each). After 1 Jan 2027 the 2026-27 Round IV figures are still "current" evidence until the first 2027-28 round exists.

## What the owner must do each year
When the FRA publishes the fee list of the new year (about mid-year): add its portal address to FRA_SITES (ingestion/fra_fees.py), a one-line edit I will do on request. Until then fees show the older, labelled list.

## Tests
tests/test_stage14b.py (12 tests: 1 Jan switch, 31 Dec stays, new cutoffs move the cutoff year, clock behind the portal, vacancy removed, fee fallback and labels, admission-year fee list wins, old plans unchanged, fee reader with unknown/known/no address, packaging, plan-making day wins), tests/phase_text.test.js (3 tests of the banner text). Also run with openpyxl/pandas/numpy blocked (as on GitHub).
## Not verified
The banner on the phone (needs "Publish website data (preview)" run by hand after 1 January, or a simulated date); a full end-to-end run on a 2027 data set (planned for the rehearsal in 14d).
