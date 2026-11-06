# Stage 9a: reading the Maharashtra State cutoff lists (done)

## What was built
- `ingestion/pdf_words.py`: reads every word of a PDF with its position on the page (uses the poppler program `pdftotext -bbox`; 1,275 pages in about 3 seconds).
- `ingestion/codes.py`: repairs and checks the official codes (see "Traps" below).
- `ingestion/parse_mh.py`: turns one State (Maharashtra and Minority) cutoff PDF into one record per published cell, and a command that does this for all archived State lists:
  `python -m ingestion.parse_mh --manifest data/raw/manifest.json --files <folder with the archived PDFs> --out data/normalized/cutoffs_mh`
  (needs poppler: `sudo apt-get install -y poppler-utils`).
- `data/normalized/cutoffs_mh/`: the result for all 7 archived State lists (2.4 MB), plus `parse_report_mh.json`, the verification report.

## What a record contains
`year_label, cap_round, list_type (MH), institute_code, institute_name, choice_code, course_name, status, home_university, section, seat_pool, allotted_to, stage, seat_code, merit_no, percentile, page, source_sha256`
`source_sha256` ties every row to the exact archived file; `page` to the page in it. Percentiles keep their printed text (for example `92.3369677`). A blank cell in the PDF produces no row (never a zero).

## How it was verified (all 7 files)
| List | Cells read | Percentiles printed in the PDF | Problems |
|---|---|---|---|
| 2023-24 Round III | 12,471 | 12,471 | 0 |
| 2024-25 Round III | 16,735 | 16,735 | 0 |
| 2025-26 Round IV | 13,745 | 13,745 | 0 |
| 2026-27 Round I | 36,059 | 36,059 | 0 |
| 2026-27 Round II | 34,391 | 34,391 | 0 |
| 2026-27 Round III | 19,839 | 19,839 | 0 |
| 2026-27 Round IV | 14,764 | 14,764 | 0 |
Total 148,004 cells. "Complete" is proven by counting every bracketed percentile printed in the file and comparing with the cells read. Also checked: no duplicate cells, every institute code has one name, every course code starts with its institute code, a spot check of conflicting cells directly against the PDF positions, and every file's fingerprint is verified before it is read.

## Traps found in the real files (each has its own test)
1. **Overflow pages (2026-27 Round I-III):** very wide tables print their last columns on the next page, with no title or course line. They are matched back to their table by vertical position, and their stage labels by row height.
2. **Wrapped column headings:** a long seat code can be split over two lines (`PWDROBC` / `S`).
3. **Course codes with letters:** one or two letters follow the digits (`0302524270U`, `0303337293LK`). An earlier version of the parser silently attached such a table to the previous course: now any code-like heading that is not recognised is reported as a problem.
4. **2023-24 codes lost their leading zero** (institute `1002`, course `100219110`). Codes are padded and checked (a course code must begin with its institute code).
5. **Stage labels** are not only Roman numerals: `I`, `II`, `VII`, `I-Non` (over `PWD` or `Defence`) and `MH` all occur.
6. **Title wording differs:** "A.Y. 2026-27" in some files, "for the Year 2026-27" in others. An unrecognised title block is reported, not skipped.
7. **Long course names wrap** onto a second line.

## What the lists contain (confirmed)
- Legend printed on every page: first letter G = General, L = Ladies; **last letter H = Home University, O = Other than Home University, S = State Level**. The number is the **State General Merit No.** and the bracket the **Merit Percentile**.
- 99 different seat codes across the files (regular codes such as GOPENS, LSCH; plus DEF…, PWD…, TFWS, EWS, MI, ORPHAN…).
- 7 kinds of section (counts over all files): State Level, Home University seats to Home University candidates, Other Than Home University seats to Other Than Home University candidates, Other Than Home University seats to Home University candidates, Home University seats to Other Than Home University candidates, Minority seats to Maharashtra State candidates, Maharashtra State seats to All India candidates.
- Stage labels: I, II, VII, I-Non (PWD / Defence), MH. What each stage means is not defined in the file; it is stored exactly as printed.
- The "Status" line of every course gives its **Home University** name, for example "Sant Gadge Baba Amravati University" (autonomous institutes say "Autonomous Institute").
- 2026-27 Round IV covers 387 institutes and 2,241 courses.

## Known limits (not hidden)
- **A few cells are slightly inconsistent in the official files themselves.** The same merit number sometimes appears with two different percentiles (0 in 2023-24, 1-17 per file later, out of 12,000-36,000 cells). I checked an example directly in the PDF; the parser reads exactly what is printed. These are counted in the report (`merit_number_conflicts`) and will be handled in Stage 10 (validation), never silently "corrected".
- The meaning of stages and the rules for which seat code applies to which student are not interpreted here (Stage 10).
- Only the State lists are read in 9a. The All India lists are 9b; the vacancy lists and seat matrix are Stage 11.
- The files were read on the developer's computer from the archived PDFs (fingerprints verified). The automatic GitHub run that repeats this comes in 9c.

## Next
- **9b:** the All India lists (a plain table; the merit exam JEE / MHT-CET / NEET is kept on every row).
- **9c:** master tables (colleges, courses, seat codes, home universities) and the automatic run on GitHub.
