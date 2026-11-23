# Stage 13c: ranking meaning "best college I can realistically get"

Decision (owner, 13b): the default ranking means "the best college I can realistically get"; "Admission chance" stays "most likely to get".

## Change (frontend/engine.js, copied to recommendation/engine.js and backend/apps-script/Engine.gs)
- New score component **strength** = expected cutoff (percentile derived from past cutoffs), limited to the student's own percentile. Labelled as derived; it is not an official quality score.
- Weights re-balanced (rows still sum to 1; table in docs/RANKING_RULES.md). Balanced: fit .25, strength .20. Admission chance: strength 0, fit .55 as before.
- New explanation line "Strength: ... derived from past cutoffs ...".

## Result on the real data (male OPEN, Computer Engineering, any district, balanced)
- Top 20 for 99.5 and 92 percentile now share 0 colleges (before: 20 of 20). Top results at 99.5 have expected cutoffs 94-98 (before: the first such college was at rank 113).
- Admission chance priority is unchanged (cheapest-fee tie still shows there; that is the "most likely to get" view).

## Tests
tests/engine.test.js (+2), tests/real_data.test.js (+1, needs REAL_DATA_DIR). JS with real data: 118 tests, 112 pass, 6 skipped.
## Not checked yet (13d)
Round figures (Round IV lower than III), whether NAAC/NBA should influence ranking, other branches/categories/percentiles, phone check.
