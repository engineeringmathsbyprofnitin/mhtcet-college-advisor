# Project status

## Completed and owner-verified
Stages 1-4, 5B, 6, 7 and 8.

## Stage 9 done; live GitHub run of 9c confirmed (all lists complete, 0 problems)
- 9a State lists: 148,004 cells, every printed percentile accounted for. 9b All India lists: 10,615 rows. 9c master tables: 403 colleges, 2,511 courses, 105 seat codes (all recognised), 14 home-university values; 0 problems (docs/STAGE9A.md, STAGE9B.md, STAGE9C.md).
- Normalized data in data/normalized (cutoffs_mh, cutoffs_ai, master; about 4.1 MB). 236 Python tests pass across Stages 7-9.
- New workflow .github/workflows/parse-documents.yml repeats the reading on GitHub from the archived PDFs and replaces the data only if everything is complete.
- Owner action pending: upload the Stage 9 files once (the 9c zip is cumulative), create the new workflow file, run it (docs/STAGE9C_SETUP.md).

## NOT verified
- The live GitHub run of the reading (poppler version there, release downloads, committing the data).
- Stage meaning and seat-code matching (Stage 10); vacancy and seat-matrix parsing (Stage 11); real data size/speed in the browser.
- Earlier caveats: no real data in the recommendation engine yet; uncalibrated weights; reserved-can-use-Open-seats assumption; TFWS/Defence/PWD not applied.

## Findings that change later work
- Seat codes end in H / O / S and each course names its Home University: a home-university dropdown (13 universities) is needed in the form (owner to decide).
- A few official State-list cells are internally inconsistent (same merit number, two percentiles): to be handled in Stage 10.
- Only MHT-CET rows (about 10%) of the All India lists are comparable with an MHT-CET percentile.

## Open questions
Home-university dropdown; Round IV vacancy = provisional position vs ACAP list; Diploma lists; OMS/J&K/Defence; treatment of JEE/NEET-based All India rows.

## Stage 10a built (seat-code / section eligibility, docs/STAGE10A.md); owner upload pending

## Stage 10b built (cutoff validator: 0 errors, oddities documented in docs/STAGE10B.md; schema v0.4); owner upload pending

## Stage 10c-1 built (automatic data plan, docs/STAGE10C1.md); owner upload pending

## Stage 10c-2 built (real website tables, schema v0.5, docs/STAGE10C2.md); owner upload pending

## Stage 10c-3a built (real data through loader + engine, docs/STAGE10C3A.md); owner upload pending

## Stage 10c-3b built (form + results page on real data, docs/STAGE10C3B.md); owner upload pending

## Stage 10c-3c built (publish workflow + preview switch, docs/STAGE10C3C.md); owner: create workflow, run it, test ?preview=1

## Stage 10c-3d fixes after phone test (show-more bug, candidate types, district always available, docs/STAGE10C3D.md)

## Stage 10c-3e Download PDF built (docs/STAGE10C3E.md)

## Stage 10d built (official institute pages: district etc., docs/STAGE10D.md); owner: upload, run 'Read institute information', then 'Publish website data'

## Next task
Owner runs the reading workflow; then Stage 10 (validation, which seat codes apply to which student, historical comparison and current-round fallback), split into small parts.
