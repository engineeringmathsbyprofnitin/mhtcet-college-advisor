# Stage 13d-2: accreditation gives a small ranking bonus

Decision (owner, 2026-11-23): choice B, NBA and NAAC accreditation get a small influence on the ranking; "no record" stays neutral.

## Rules (frontend/engine.js; copied to recommendation/engine.js and backend/apps-script/Engine.gs)
- A graded NAAC row counts while it is on NAAC's official list (grade score A++ 100 ... C 20). The list has no end date; its date ("as on 14 Aug 2025") is shown. Before this stage such rows were treated as "validity unknown" and never counted.
- Valid NBA for the program adds 15 to the grade score (valid NBA alone = 60), as before. An ended NBA period, a NAAC transition row (no grade) and "no record" give NO score.
- Accreditation is no longer part of the weighted average. It is a bonus added to the final score: 0.25 x accreditation weight x accreditation score (`accreditationBonusFactor`). Balanced: at most 1 point (like the vacancy nudge); Teaching priority: at most 2.5.
- Why a bonus and not a component: with the old averaging, a modest grade (for example B++ = 55) could rank a college BELOW a college with no record, because missing data is dropped from the average. Now having no record adds and subtracts nothing, and a lower grade never beats a higher one.
- New explanation line on a card: "Ranking: accreditation gave this choice a small bonus of x points ...".
- Why only 0.25: a first try with the full weight (up to 4 points) was worth about 14 cutoff percentile points of "strength", too much while our lists are incomplete (only some colleges are matched, so "no record" often means "not in our lists").

## Measured on the real data (male OPEN, Computer Engineering, Pune, any district, balanced)
Bonus on versus off: the top 20 keeps 18 of 20 colleges at 99.5 and 92 percentile, 19 at 80; the average college moves 2-3 places. With the Teaching priority the top 20 keeps 16 of 20.

## Tests
tests/engine.test.js +2 (counts / neutral cases, monotonic in grade), tests/real_data.test.js +1 (and the 13d-1 test), tests/test_stage10c3a.py now expects 13 real-data page tests. 618 Python tests pass (2 skipped); JS with real data 122 tests, 116 pass, 6 skipped.
## Not verified
Phone view. The weights remain judgement-based, not calibrated against admission outcomes.
