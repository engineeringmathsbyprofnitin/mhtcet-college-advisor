# Stage 13 summary: ranking and explanation review (2026-11-23)

| Part | What | Page |
|---|---|---|
| 13a | Diagnosis: same top 20 for 92 and 99.5 percentile (fit saturates, ties decided by cheapest fee) | STAGE13A.md |
| 13b | Owner's decision: default ranking = "best college I can realistically get"; "Admission chance" stays "most likely to get" | STAGE13B.md |
| 13c | New "strength" component (expected cutoff, capped at the student's percentile, labelled derived); weights re-balanced | STAGE13C.md, RANKING_RULES.md |
| 13d-1 | Bug: current-year cutoff ignored the student's home university; fixed. Rising round figures are real data | STAGE13D1.md |
| 13d-2 | Owner's decision B: accreditation is a small bonus (graded NAAC row on the official list, valid NBA; at most about 1 point; no record neutral) | STAGE13D2.md |
| 13d-3 | 22 student profiles checked, no engine problem; form notes that placement/teaching/infrastructure priorities have no data yet | STAGE13D3.md |

## How the default ranking works now (short)
Filter by branch, district, budget and eligible seat types -> expected cutoff (weighted past years + current round) -> margin = percentile minus cutoff -> score = weighted average of fit, strength, branch, district, fee (and placement, teaching, infrastructure when data exists; missing data is dropped, never zero) -> small vacancy nudge (+1/-1) and small accreditation bonus -> sorted. Details: docs/RANKING_RULES.md.

## Known limits
- Weights are judgement, not calibrated on real admission outcomes.
- Strength means "high past cutoffs" (demand), not an official quality score.
- No placement, teaching or infrastructure data yet (Stage 12d).
- NAAC list is as on 14 Aug 2025 and has no universities; "no record" means "not in our lists".
- Only some NBA/NAAC colleges are matched.

## Open before going public (owner decides; public page still on old data)
Phone check of the preview; one line in frontend/config.js (`PUBLIC_DATA_FOLDER = "data-real/"`); optional disclaimer line about list dates and missing data.
