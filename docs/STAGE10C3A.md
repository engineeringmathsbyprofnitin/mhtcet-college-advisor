# Stage 10c-3a - real data through the loader and engine (no change to the live page yet)

## What was built
- `python -m ingestion.package_real [out_dir]` packages the real tables as the website's static files using the SAME validator and exporter as before (all 16 tables; tables without data yet are empty = "Not available"). Output today: version `REAL-2026-27-RIV-eda910ed`, 99 cutoff files + 1 base file, 7.5 MB in total; the biggest file is about 72 KB after normal web compression. A student downloads only the seat-type files that apply to them. NOT written to `frontend/data` yet: the live page still shows the synthetic data until 10c-3b (form) is done.
- Schema v0.6: seat_types gets `family` and `variant`; cutoff tables carry section, home_university, home_university_basis. Repeated long texts in the cutoff files are stored once (dictionary) so the files stay small; the loader expands them.
- Engine (recommendation/engine.js, copied to frontend/engine.js and Engine.gs):
  * seat types by family: regular (G/L, category, open seats for reserved students as before), EWS, TFWS, PWD/PHC, Defence, Orphan need the student's claim; seat variants whose meaning is undefined (R, I, N, 2) and Minority seats are never matched;
  * Home University / Other Than Home University sections are decided row by row from the student's home university (new input `homeUniversity`); autonomous institutes have State Level seats only; All India section never applies to Maharashtra candidates;
  * if the course's home university is unclear (505 rows) or the student has not chosen one, both possibilities are tried and the HARDER (higher) cutoff is used, flagged `homeUniversityUnclear`, with a warning (owner decision: show, with warning);
  * `currentRounds`: the closing figure of each round I, II, III, IV of 2026-27 for every result (owner decision: students see all four rounds);
  * category names are compared ignoring capital letters (OPEN = Open); "Ladies" seats need a female student.

## Tests
- tests/real_data.test.js (10, browser loader + engine on real data), tests/test_stage10c3a.py (4, includes an independent check: for two student profiles the engine's 1,365 per-round cutoff figures equal the Python rules' figures, 0 differences).
- Existing engine 48/48 and loader 14/14 still pass on the synthetic data.

## NOT done / NOT verified
- Form: home-university dropdown, real category list, claim checkboxes (EWS/TFWS/PWD/Defence/Orphan), district switched off, banner with data version/phase/last updated -> 10c-3b. Results page showing the four rounds -> 10c-3b.
- Publishing into the live site (weekly workflow that builds and commits the files) -> 10c-3c / Stage 14.
- Seat variants R/I/N/2, minority seats, All India candidates, OMS/J&K: not matched yet.
- Real phones / slow networks not measured.
