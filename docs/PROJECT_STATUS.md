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

## Stage 11a built (vacancy PDF reader, docs/STAGE11A.md); owner upload pending
Round IV file = seats open going into Round IV (owner confirmed); Round III file only as fallback; ACAP/court/seat-matrix never used. Dry run: Round IV 2,335 blocks / 1,013 pages / 0 problems; Round III 2,330 blocks / 946 pages / 0 problems. NOT verified: GitHub run, matching to website courses, engine/page/PDF display.

## Stage 11b built (docs/STAGE11B.md): vacancy tables + workflow "Read the vacancy lists"; owner upload and first run pending

## Stage 11c built (docs/STAGE11C.md): vacancy matched to website courses (tables/vacancy.csv); not yet shown on the page

## Stage 11d built (docs/STAGE11D.md): vacancy packaged and shown as "Seats open going into Round IV" (page, PDF, explanation). Owner upload + workflow run pending. Stage 11 complete after that check.

## Stage 12a-1 built (docs/STAGE12A.md): probe of the FRA fee page; owner upload + workflow run pending

## Stage 12a-2 built (docs/STAGE12A.md): fee reader + workflow "Read the approved fees" (owner upload + run pending); phone layout fix for cells

## Stage 12a-3 built (docs/STAGE12A3.md): FRA fees linked (301 colleges) and shown; owner upload + publish run + phone check pending; 8 colleges wait for the owner to confirm the name match

## Stage 12b-1 built (docs/STAGE12B.md): NBA probe + workflow "Probe the NBA site"; owner upload + run pending

## Stage 12b-2 built (docs/STAGE12B.md): NBA importer for the owner-downloaded Excel (258 rows/42 institutions, Tier I) + workflow "Read the NBA lists"; owner upload + run pending

## Stage 12b-3a built (docs/STAGE12B3A.md): NBA institution matcher (101 linked, 86 doubtful, 28 no college); owner confirmation of the doubtful list pending

## Stage 12b-3a2: owner confirmed 86 doubtful NBA pairs (data/manual/nba_institution_confirmations.csv): 175 institutions linked; 28 still unresolved (shown to owner)

## Stage 12b-3a complete: all NBA institutions resolved (192 linked, 23 not on the website); next 12b-3b

## Stage 12b-3b built (docs/STAGE12B3B.md): programs matched to branches (1,177 of 1,357 rows), accreditation table 1,206 rows packaged; display + phone check next (12b-3c)

## Stage 12b-3c built (docs/STAGE12B3C.md): ended NBA shown grey with date, NBA workflow now links + builds accreditation; owner to run "Publish website data" and check on phone

## Stage 12b done: NBA shown on cards (ended = grey with date, none = "No NBA record found"); phone-checked by owner. Next: Stage 12c (NAAC)

## Stage 12c-1 built (docs/STAGE12C1.md): NAAC probe workflow; owner to run "Probe the NAAC site" and tell the result

## Stage 12c-2 built (docs/STAGE12C2.md): NAAC probe failed (GitHub cannot read the site); owner file read: 2,324 Maharashtra rows, no end dates; next 12c-3 matching

## Stage 12c-3 built (docs/STAGE12C3.md): 233 colleges linked to NAAC records, 170 no record; NBA Marathwada/Maharashtra mapping corrected; next 12c-4 (rows, packaging, card)

## Stage 12c-4 built (docs/STAGE12C4.md): NAAC rows (233) packaged, card shows grade, CGPA, declaration date and list date, "No NAAC record found" in grey; owner to run "Publish website data" and check on phone

## Fix after the failed "Publish website data" run: NAAC reader and tests no longer need openpyxl (GitHub self-test step has only PyYAML); owner to upload and run it again

## Stage 12c-5 built (docs/STAGE12C5.md): NAAC transition sheet used: 17 more colleges show "accreditation extended until <date>"; owner to upload, run "Publish website data" and check K J Somaiya on phone

## Fix: backend/apps-script/Engine.gs (third engine copy) brought up to date with frontend/engine.js; a test now keeps all three identical

## Stage 12c-6 built (docs/STAGE12C6.md, docs/REFRESH_NBA_NAAC.md): workflow "Read the NAAC list" (by hand, and when data/manual/naac/** or the two NAAC answer files change; it does NOT start the publish workflow); owner to paste it as .github/workflows/read-naac.yml, run it once, then run "Publish website data (preview)"

## Stage 13a done (docs/STAGE13A.md): ranking diagnosis on the real data. Same top 20 for 92 and 99.5 percentile because fit saturates at margin 5 and ties are broken by cheapest fee (no placement/teaching/infrastructure data yet). No code changed; owner to decide the ranking philosophy (13b)

## Stage 13c built (docs/STAGE13C.md): default ranking = "best college I can realistically get" (new "strength" component from past cutoffs; engine only, so "Publish website data" does not need to be run); the three engine copies updated; owner to upload and check on the phone with ?preview=1

## Stage 13b recorded (docs/STAGE13B.md): owner chose A, default ranking = "best college I can realistically get"; implemented in 13c

## Stage 13d-1 built (docs/STAGE13D1.md): fixed the current-year cutoff ignoring the student's home university (engine only; three copies identical); round figures that rise are real data; owner to upload. Next 13d-2: NAAC/NBA in ranking, more test students

## Stage 13d-2 built (docs/STAGE13D2.md): accreditation (NAAC grade on the official list, valid NBA) is a small ranking bonus, no record = neutral; includes the 13d-1 fix; owner to upload (engine only: no workflow, no publish run)

## Stage 13d-3 built (docs/STAGE13D3.md): 22 different students checked, no engine problem; the form now says that placement/teaching/infrastructure priorities have no data yet (note disappears when the data exists); owner to upload and check on the phone

## Stage 13 wrap-up (docs/STAGE13.md, ROADMAP.md updated): Stage 13 done except the owner's phone check; public page deliberately stays on the old data; next: Stage 12d or Stage 14 (owner chooses)

## Stage 14b built (docs/STAGE14B.md): admission year changes on 1 January (calendar rule); cutoffs stay evidence-based so the Round I option form uses last year's cutoffs with a clear banner; vacancy follows the admission year, fees show the newest list with its year; fee reader no longer fails when the new year's FRA address is unknown. Owner to upload; run "Publish website data (preview)" by hand afterwards

## Stage 14c built (docs/STAGE14C.md): daily discovery, cutoff reading, vacancy reading and publish (institutes and fees stay weekly); publish no longer chained; publish guard ignores time stamps so quiet days make no commit. Owner: upload files first, then paste the four workflows by hand

## Stage 14d-1 built (docs/STAGE14D1.md, docs/RECOVERY.md): "Data updated on <date>" line (date the data last really changed; notice after 10 days without change) and the owner's recovery guide. Next 14d-2: rehearsal test of the 2027-28 rollover

## Stage 14d-2 built (docs/STAGE14D2.md): rollover rehearsal on pretend 2027 data (1 Jan switch and first 2027-28 round); found and fixed a bug (fees would have vanished after Round I of the new year); owner to upload
