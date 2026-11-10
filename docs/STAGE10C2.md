# Stage 10c-2 - building the website tables from the real data (schema v0.5)

`python -m ingestion.build_tables` -> `data/normalized/tables/`: colleges (403), branches (2,510), seat_types (105), source_documents (7), current_cutoffs (104,225 rows: 2026-27 rounds I-IV), historical_cutoffs (42,602 rows: 2025-26 IV, 2024-25 III, 2023-24 III). The lists used come from the automatic plan (docs/STAGE10C1.md). Tests: `tests/test_stage10c2.py` (12).

## Rules applied
- One closing row per round / course / section / seat code: the lowest percentile over the stages present (rule from 10a, provisional).
- Home university is resolved per row and labelled: `printed` (112,122 rows), `inferred` (20,622: the course prints exactly one university elsewhere), `not_needed` (13,594: State Level etc.), `unknown` (505: several values or none). Unknown rows are kept; the website will show them with a "home university unclear" warning (owner decision).
- **16 cells print a percentile of 0.0000000 next to a real merit number** (TFWS seats, 2024-25 round III and 2025-26 round IV, e.g. merit no 5776). That cannot be a real cutoff, so they are kept in the normalized data but EXCLUDED from the website tables and counted (validation warning PRINTED_ZERO_PERCENTILE, build report).
- District: the lists do not print it, so every college has `Not available`. Districts need another official source (open item; the form's district preference cannot filter until then).
- Schema v0.5: the two cutoff tables also get `home_university` and `home_university_basis`.

## NOT verified
- Whether the 16 zero percentiles are an error in the CET Cell file or mean something else.
- Whether `inferred` home universities are right for years in which the college's university may have changed (only unambiguous courses are inferred).
- The tables have not yet been read by the engine or loaded in the browser (10c-3).
- Published/retrieved dates are blank (not in the lists).
