# Recommendation engine: ranking rules (Stage 4, v0.2)

Code: `recommendation/engine.js`. Everything below is deterministic: the same input and data always give the same output.
**None of the numbers below has been statistically calibrated.** They are sensible starting values, kept in one place (`DEFAULTS` in the engine) so they can be tuned later against real data. The output must never be described as a "probability" or "chance".

## 1. Steps
1. **Validate the student's input.** Percentile 0–100; candidate type and category present; at least one branch and one district (or ANY); whole-rupee budget; fee basis tuition/total. Invalid input returns error messages and no results.
2. **Find the current admission year.** Use the year the student chose; if "auto", use the admission year of the last-known-good data version. If neither is known, stop with a clear error. Never guess.
3. **Historical years** = the three admission years *before* the current one (for 2026-27: 2025-26, 2024-25, 2023-24). The current year is never counted as one of the three.
4. **Eligible cutoff groups (seat types).** A seat type applies when candidate type matches, category matches (or is "Open"), and its gender scope is blank or matches the student's gender. If several apply, the engine uses the **lowest** cutoff among them (the most favourable group the student can compete in). *Assumption to verify against official rules: reserved-category students may also compete for Open seats (switch: `includeOpenSeatsForReserved`).* If no seat type matches, no recommendation is made.
5. **Filter** by acceptable branches (exact official branch name), districts (names normalised; old names like Aurangabad/Osmanabad/Ahmednagar map to current ones; "ANY" accepts all), and budget.
6. **Compare with cutoffs and label** each remaining choice (section 3).
7. **Score and rank** (section 4). Return at most 20; fewer if fewer match. The first 5 are the main list, 6–20 go under "Show more suitable choices".

## 2. Which data is used
| Item | Rule |
|---|---|
| Current-year cutoff | Latest published round for that choice: **IV, then III, then II, then I**. The round used is recorded and shown. |
| Past-year cutoff | For each of the 3 previous years, the final available round (same priority order). A missing year stays "Not available". |
| Vacancy | One round for the whole dataset: **Round IV if any genuine Round IV vacancy data exists, otherwise Round III.** A choice missing from that round shows "Vacancy data unavailable" and is **never** filled from another round. Round I/II rows and seat-matrix/intake data are never used (the source document must be of type `vacancy_position`). Zero is shown only if officially reported. |
| Fee | Fee type matches the student's choice (tuition or total). Latest academic year available. If several scopes exist, the highest is used (conservative). If "total" is requested but only tuition exists, tuition is shown as a lower bound only (total is never lower than tuition), and the choice is excluded only if tuition alone exceeds the budget. Unknown fee: choice kept and flagged. Fee from an older year is flagged. |
| Accreditation | NAAC is institution-level; NBA is per program (one accredited program never makes other programs accredited). Expired, or with no validity date, = flagged and **not counted**. No NBA row = "Not available", not "not accredited". |
| Teaching/infrastructure | Only the system's labelled **estimates** (0–10). Never shown as official scores. |
| Placement | Latest year of `placement_percent` (branch-level if it exists, else institution-level). |
| Validation | Only rows with `validation_status = validated` are used. |

## 3. Suitability labels

**Expected cutoff** = weighted average of the available cutoffs, plus a small trend adjustment.
- Weights: the three past years 0.3, 0.2, 0.1. The current-year weight depends on the round it comes from, because earlier rounds show higher cutoffs than the final round: Round IV 0.40, III 0.35, II 0.30, I 0.20. Weights are re-scaled when some data points are missing.
- Trend: if the past-year cutoffs were rising, add 0.5 x the yearly rise (maximum +3). Falling cutoffs are **not** credited (conservative, because one easy year may not repeat). The trend uses past years only, so a partial current round never fakes a trend.

**Percentile gaps are scaled (new in v0.2).** One percentile point is worth far more ranks near the top than lower down, so a gap is multiplied by `20 / (100 - cutoff)` (the distance 100 - cutoff is limited to between 2 and 40). At a cutoff of 80 the factor is 1, so nothing changes mid-range.

| Cutoff | Factor | Raw gap of 1 point counts as |
|---|---|---|
| 99.0 or higher | 10.0 | 10 points |
| 95 | 4.0 | 4 points |
| 90 | 2.0 | 2 points |
| 80 | 1.0 | 1 point |
| 60 or lower | 0.5 | 0.5 points |

Scaled margin = scaled gap between the student's percentile and the expected cutoff. The raw margin is also reported.

| Label | Rule |
|---|---|
| Insufficient data | No usable cutoff at all. Listed separately, **not ranked**. |
| Limited evidence | Only one cutoff data point. Ranked, with a 15% score reduction. |
| Historically more suitable | Scaled gap between the student and the **highest** available cutoff is at least +1.0 |
| Possible but uncertain | Scaled margin of at least -2.0 (and not in the row above) |
| Ambitious choice | Scaled margin between -6.0 and -2.0 |
| (not shown) | Scaled margin below -6.0: not realistic, counted but excluded |

Vacancy never changes a label. It only nudges the ranking score by +1 or -1 point (some vacancy reported / zero reported) and is explained to the student as "not a guarantee". When the current cutoff comes from a round before IV, the explanation warns that earlier rounds usually show higher cutoffs than the final round.

## 4. Ranking score (0-100)
Each component is scored 0-100. A component with **no data is left out and the others are re-scaled** (missing data is never turned into zero or an invented rating):
- **fit** = 70 + 6 x scaled margin, limited to 0-100
- **branch** = 100 - 15 x (rank - 1), minimum 40
- **district** = same for district rank; "ANY" = 70 for all
- **placement** = placement percent
- **teaching / infrastructure** = estimate x 10
- **fee** = 100 - 70 x fee / budget
- **accreditation** = NAAC grade (A++ 100, A+ 85, A 70, B++ 55, B+ 40, B 30, C 20) + 15 if the program has valid NBA; valid NBA alone = 60

**Evidence-coverage factor (new in v0.2).** Leaving out missing components is fair, but it could let a college with little data edge past one with the same scores and more data. So the final score is multiplied by `0.90 + 0.10 x (share of the total weight that has data)`. A college with every component known is not reduced; the maximum reduction is small. The share is reported as `dataCompleteness`.

Weights by priority (each column sums to 1; if several priorities are chosen, their weights are averaged):

| Component | Balanced | Placements | Teaching | Infrastructure | Lower fees | Admission chance |
|---|---|---|---|---|---|---|
| fit | .30 | .30 | .30 | .30 | .30 | .55 |
| branch | .15 | .15 | .15 | .15 | .15 | .12 |
| district | .10 | .10 | .10 | .10 | .10 | .08 |
| placement | .12 | .25 | .06 | .05 | .06 | .06 |
| teaching | .12 | .08 | .22 | .08 | .05 | .06 |
| infrastructure | .10 | .05 | .04 | .25 | .04 | .05 |
| fee | .06 | .03 | .03 | .03 | .27 | .04 |
| accreditation | .05 | .04 | .10 | .04 | .03 | .04 |

Ties are broken by branch preference rank, then district preference rank, then choice code (so results are stable).

## 5. Known limitations (be honest with students)
- Thresholds and weights are judgement-based, not calibrated against outcomes. The percentile-gap scaling is a simple approximation (it does not use real rank data); real rank/percentile tables could replace it later.
- Past cutoffs do not guarantee a future cutoff or a seat.
- Extra eligibility claims (TFWS, Defence, PWD) are **not applied** yet; the response says so.
- Home-university vs other-than-home-university rules, and other CAP details, will need real seat-type data (Stages 7–9).
- Results are only as good as the data loaded; synthetic data is flagged in `meta.usingSyntheticData`.

## 6. What the engine returns (per result)
rank, college name/code, branch name/code, district, website, autonomy, three past-year cutoffs (year, value, round, seat type), current cutoff (value, round), vacancy (value, round or "Vacancy data unavailable"), fee (value, type, year, status), infrastructure/teaching estimates, placement, NBA, NAAC, suitability label, expected cutoff, raw and scaled margin, component scores, data completeness, plain-language explanation lines, and source documents. Missing items are `null`; the web page will display "Not available".
