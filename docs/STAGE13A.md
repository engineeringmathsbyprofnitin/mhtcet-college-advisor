# Stage 13a: ranking diagnosis (no code changed)

Method: the engine (frontend/engine.js) was run on the published real data (frontend/data-real, 2026-27 Round IV) for a male OPEN State candidate,
Pune University, Computer Engineering, any district, budget 10 lakh, as of 2026-11-23. Percentiles 99.5, 92 and 80; priorities "balanced" and "admission_chance".

## Findings
1. The top 20 for 92 and for 99.5 percentile are the SAME 20 colleges (overlap 20 of 20). At 99.5 the first college with an expected cutoff of 97 or more is at rank 113 (14 such colleges).
2. Cause 1 - the fit score saturates. fit = clamp(70 + 6 x scaled margin, 0, 100) reaches 100 once the margin is 5 or more. A college whose cutoff is 20 points below the student and one whose cutoff is 3 points below get the same fit (100), so the engine cannot tell "easy" from "good".
3. Cause 2 - the tie is broken by fee only. Placement, teaching, infrastructure have no data yet (placements 0 rows, quality indicators 0 rows) and accreditation is empty for most colleges; branch and district scores are equal for everyone (one branch, any district). The top results are therefore sorted by cheapest fee (34,000, 49,000, 52,000, 53,000, 55,000 ...). Only about 61% of the "balanced" weight has data (79% for admission_chance).
4. At 99.5 percentile all 200 shown results are labelled "Historically more suitable"; nothing is ambitious. At 92: 138 suitable, 22 possible, 22 limited evidence, 7 ambitious.
5. Current-year round figures: Round IV can be lower than Round III for the same seat (72.4 vs 77.0 for one college) because the lowest cutoff over all eligible seat types is used (known issue; not examined further here).

## Proposed fix (needs the owner's decision, see Stage 13b)
Make the default ranking answer "the best college I can realistically get": among choices the student can reach, a higher expected cutoff (a data-driven strength measure, labelled as derived) ranks higher; very easy choices (margin far above 5) no longer score 100. Keep a separate "admission_chance" priority for "most likely to get".
