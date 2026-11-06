# Stage 9b: reading the All India cutoff lists (done)

## What was built
- `ingestion/parse_ai.py`: turns one All India cutoff PDF into one record per table row, and a command for all archived All India lists:
  `python -m ingestion.parse_ai --manifest data/raw/manifest.json --files <folder with the archived PDFs> --out data/normalized/cutoffs_ai --mh-dir data/normalized/cutoffs_mh`
  (needs poppler, like 9a).
- `data/normalized/cutoffs_ai/`: the result for the 7 archived All India lists (0.3 MB) and `parse_report_ai.json`.

## What a record contains
`year_label, cap_round, list_type (AI), sr_no, merit_no, score, choice_code, institute_code, institute_name, course_name, merit_exam, merit_exam_kind, ai_type, seat_type, page, note, source_sha256`
`score` is the bracketed figure exactly as printed. `merit_exam` is the exam named in the row; `merit_exam_kind` is JEE, MHT-CET or NEET.

## How it was verified (all 7 files)
| List | Rows | Blank-cutoff rows | Complete | Problems | Cross-check with the State list: course not in State list / institute name differs / course name shortened / course name differs |
|---|---|---|---|---|---|
| 2023-24 Round III | 1,299 | 0 | yes | 0 | 16 / 0 / 91 / 0 |
| 2024-25 Round III | 1,399 | 3 | yes | 0 | 5 / 0 / 75 / 0 |
| 2025-26 Round IV | 1,353 | 3 | yes | 0 | 12 / 0 / 68 / 0 |
| 2026-27 Round I | 2,004 | 0 | yes | 0 | 0 / 0 / 121 / 0 |
| 2026-27 Round II | 1,753 | 0 | yes | 0 | 0 / 0 / 116 / 0 |
| 2026-27 Round III | 1,472 | 0 | yes | 0 | 0 / 0 / 88 / 0 |
| 2026-27 Round IV | 1,335 | 0 | yes | 0 | 0 / 0 / 86 / 0 |
Total 10,615 rows. "Complete" means: serial numbers run 1, 2, 3 ... with no gap, every row has its choice code and institute, and the count of rows equals the count of printed choice codes. Independent cross-check: every institute name equals the State list's name for the same course code (0 differences in all 7 lists); every course-name difference is the All India table cutting a long name short, which is harmless.

## Traps found in the real files (each has a test)
1. **From row 1,000 the serial numbers are printed with a comma ("1,000").** My first version did not understand them and merged about 400 rows per list into row 999. My earlier note "about 999 rows per file" was wrong; the completeness check exposed it.
2. **The columns sit at different positions in each year's file** (and the exam heading reads "Exam (JEE/MHT-CET)" in 2023-24 but "Merit Exam" later). Column boundaries are measured from each page's own headings, and a word that straddles a boundary is reported.
3. **The choice code is printed a little lower than the institute name**, so it is read by its shape, separately.
4. **Blank cutoffs:** 6 rows (2024-25 and 2025-26) have no merit number and no score (no one was allotted to that seat type). They are kept as rows with empty cutoff and the note "no cutoff printed in the source", never filled in or turned into zero.
5. **Exam names vary:** 13 forms, such as `JEE`, `JEE(Main)`, `JEE(Main)-2026`, `NEET-2025`, `MHT-CET`, `MHT-CET-PCB 2026`, `MHT-CET-PCM 2024`. They are stored as printed, plus a simple kind.
6. **Long course names are shortened** in the All India table (for example "...Engineering(Artificial"). The full name is available from the State list through the choice code.

## What the lists contain
- Rows by exam kind: 2023-24 JEE 1,119 / MHT-CET 180; 2024-25 JEE 1,253 / MHT-CET 133 / NEET 13; 2025-26 JEE 1,228 / MHT-CET 115 / NEET 10; 2026-27 Round I JEE 1,520 / MHT-CET 484; Round II 1,509 / 244; Round III 1,327 / 145; Round IV 1,203 / 132.
- Rows by type over all files: "AI to AI" 10,099 (All India seats to All India candidates), "MH to AI" 485 (Maharashtra seats to All India candidates, with a State seat code such as GNT1H), "MI to AI" 31 (minority seats).
- A few MHT-CET rows are PCB (biology group) rather than PCM. They are stored as printed; I believe they should not be compared with an engineering (PCM) percentile.

## What this means for recommendations
For an **All India candidate with an MHT-CET percentile**, only the MHT-CET rows are comparable: about 10% of the rows in 2026-27 Round IV (132 of 1,335). The JEE and NEET rows carry a different kind of score and must never be compared with it. The rules for using these rows belong to Stage 10.

## Known limits
- Only the cutoff number and score are read; what "AI to AI", "MH to AI" and "MI to AI" mean for a given student is for Stage 10.
- The reading was done here from the archived PDFs (fingerprints verified); the automatic GitHub run is 9c.
