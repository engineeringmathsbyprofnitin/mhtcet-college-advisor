# Stage 10c-3b - the form and results page on real data

Still NOT live: the page shows the real-data features only when its data folder is the real package (`REAL-...` version). The live site keeps its synthetic data (and its old form) until the data is published (10c-3c).

## What changed (frontend)
- The form builds its lists from the data when the data is real: candidate types, categories (OPEN first, then SC, ST, VJ, NT1-3, OBC, SEBC as printed in the lists), the branch names (124 as printed, most common first).
- New "Home university" dropdown (12 universities, exactly as the lists print them; checked against the data by a test); blank = "Not sure": the engine checks both cases and uses the harder cutoff and warns.
- Claim boxes: EWS, Orphan, TFWS, Defence, PWD (shown when the data has those seat families).
- District: switched off and ticked "Any district" with the note "District data coming soon" because no district is printed in the lists (owner decision). It stays locked after "Clear form".
- Banner under the header, built from the data version row: shows the admission year, the rounds published, and the next round expected, or - before a new year's Round I - "Cutoffs for the new admission year are not published yet ... last year's figures, not a prediction". Expected CAP dates are NOT shown: no reliable schedule document is classified by the discovery yet (owner: only if reliable).
- Each result's "Latest current cutoff" cell shows a small row "Round I: x - Round II: y - Round III: z - Round IV: w" (a dash = no eligible cutoff in that round); the suitability label stays based on the latest round. A line says when the home university was unclear and the harder figure was used.
- `DataLoader.getBase()` loads the small base tables for the form.

## Tests
- tests/ui_real.test.js (4, real data in jsdom), tests/test_stage10c3b.py (config list equals data; runs the real-data page tests and the old 21 synthetic page tests). The 21 old page tests, engine 48 and loader 14 still pass.
- jsdom is needed for the page tests (`npm install jsdom`); where it is missing they are skipped. They were run with jsdom in the build sandbox: 25 of 25 passed. NOT run on real phones/browsers.

## NOT done / NOT verified
- Publishing the real data to the live site (10c-3c): a weekly GitHub workflow that builds and commits the data files.
- Looks on real phones; very long results rows on small screens not reviewed visually.
- Branch names are shown exactly as printed (e.g. "Electronics and Telecommunication Engg" and similar names are separate entries).
- Schedule dates in the banner; district data; All India / other-state candidate types.
