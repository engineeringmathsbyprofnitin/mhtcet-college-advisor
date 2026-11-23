# Stage 13d-1: current-year cutoff bug and round figures

## Bug found and fixed
In frontend/engine.js the current-year cutoff was picked with `pickCutoff(rows, eligible, cfg)` WITHOUT the student, while the past years and the four round figures shown on the card used the student. So the current-year cutoff used for ranking ignored the student's home university: every Home University / Other Than Home University row counted as "unknown" and the HARDER of the two readings was used and flagged "unclear".
Effect on the real data (male OPEN, Pune University, 92 percentile): for 77 of 182 choices the figure used for ranking differed from the Round IV figure shown on the card (up to 75 percentile points apart, e.g. 78.89 used against 3.97 shown); 142 of 182 carried the "home university unclear" flag.
Fix: pass `student` (one word). After the fix: used and shown figures agree for every choice; the "unclear" flag appears only when no home university is chosen (then the harder of the two readings is still used, as designed). The three engine copies are identical.

## Not a bug
- Round figures that rise from one round to the next (for example 86.10 in Round II, 86.30 in Round III) occur in 142 of 189 choices. They are the published cutoffs; the engine shows them as printed and does not smooth them.
- A "no home university" student can see a LOWER current figure than a Pune student for 6 of 188 choices. In these the Pune student has no Round IV row, so the engine falls back to Round III, while the "no home university" reading also accepts rows of other universities. Only figures from the same CAP round are comparable; the real-data test now says so.

## Tests
tests/real_data.test.js: +1 test (used = shown, no "unclear" with a home university) and the same-round rule above. tests/test_stage10c3a.py now expects 12 real-data page tests. 618 Python tests pass (2 skipped); JS with real data 119 tests, 113 pass, 6 skipped.

## Still open in 13d (13d-2)
Whether NAAC/NBA should influence the ranking; checks with other branches, categories and percentiles; phone check.
