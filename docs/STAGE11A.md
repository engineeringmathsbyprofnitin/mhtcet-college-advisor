# Stage 11a - reading the official vacancy PDFs

Parser: `ingestion/parse_vacancy.py`. Tests: `tests/test_stage11a.py` (fixture: pages 1-2 of the real Round IV file).

## What the files mean (confirmed by the owner)
- `FE2026_Vacancy_For_CAP4.pdf` ("Provisional Vacancy for CAP Round IV") = seats open after Round III, going into Round IV. This is the Round IV vacancy position and is used first.
- `FE2026_Vacancy_For_CAP3.pdf` = seats open going into Round III. Used only if the Round IV file does not exist.
- The ACAP after-CAP list, court-order lists and the seat matrix are never used as vacancy. CAP has no Round V.

## Layout found in the real files
One block per course (Choice Code). A block shows: institute line (`01002 - name`, sometimes wrapped on a second line), kind (for example Government Autonomous), `Vacant CAP Seats`, a row `Choice Code | Course Name | SI | MS Seats | Minority | All India | Institute Seats | OrphanI | OrphanN`, a seat grid (State Level, or HU + OHU; General/Ladies for 9 categories), PWD and DEF rows, "Common Reserved" numbers, EWS seats and the TFWS choice code with seats.
Traps found and covered by tests: course names wrapped over two lines; choice codes with one or two trailing letters (F, LK); empty TFWS code (`Choice Code: Seats: 0`); institute names wrapped onto a second line; a page-top title line that repeats part of the institute name; a header printed at the bottom of one page with its block on the next page; rows of one block continuing after a page break.

## Rules proven on the real files (every block, no exceptions)
- MS Seats = seat-grid totals + PWD row + DEF row + OrphanI + OrphanN
- Vacant CAP Seats = MS Seats + All India + Minority Seats (Institute Seats are not included)
- "MS Seats" and "SI" (intake) are stored as separate numbers; intake is never used as vacancy.
The parser checks both rules for every block and reports a block that breaks them; it never corrects a number.

## Results of the dry run in the sandbox (not yet in GitHub Actions)
- Round IV: 2,335 course blocks, 387 institutes, 1,013 of 1,013 pages seen, 0 problems, 0 unrecognised lines. Totals: Vacant 23,107 = MS 17,639 + All India 4,200 + Minority 1,268.
- Round III: 2,330 course blocks, 946 of 946 pages, 0 problems, 0 unrecognised lines.

## Not done yet (11a-3 / 11b / 11c)
Writing the parsed rows to data/normalized, a GitHub workflow step, matching Choice Codes to the website course keys, the strict Round IV-then-III rule in the plan, and showing "Seats open going into Round IV" in the engine, page and PDF.
