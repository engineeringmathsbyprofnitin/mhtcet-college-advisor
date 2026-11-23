# Stage 13d-3: checks with other students, and a note on priorities without data

## Checks (engine on the published real data, as of 2026-11-23)
22 students: Mechanical, Civil, Information Technology, Computer Engineering; OPEN, OBC (female), SC, ST (female), NT1, SEBC, EWS claim, PwD and TFWS claims; Pune and Mumbai home universities; percentiles 0, 10, 40, 50, 60, 65, 70, 75, 80, 85, 88, 90, 99.9; three branches at once; budgets 90,000 and 10 lakh; tuition and total fee basis; one and two districts; every priority; one non-existent branch.
For every case: no exception; every score between 0 and 100; ranks 1,2,3... in descending score order; no component score outside 0-100; no result above the budget; seat types used are sensible (for example an OBC woman gets GOBC*, LOBC*, GOPEN*, LOPEN*; a ST woman gets G/L ST and OPEN seats; EWS claim adds the EWS seat; PwD adds PWD seats); the non-existent branch gives the message "No branch named ... exists in the data" and no results; percentile 0 gives 3 results with the warning "Only 3 choice(s) matched ...".

## Observations (no engine change)
- For a 70-percentile Mechanical student the first result has an expected cutoff of about 59: choices with a comfortable margin (about 5 or more) rank above choices closer to the student's level, which is what "realistically get" means.
- The "no cutoff data for the category EWS" warning appears only if "EWS" is picked as a category. The real form does not offer EWS as a category (it is a claim checkbox), so the warning cannot appear on the page.
- The priorities "Good placements", "Good teaching" and "Good infrastructure" have no data yet, so they behave almost like "Balanced" (Teaching also changes the accreditation bonus).

## Change
frontend/app.js + frontend/index.html: a short note under the priorities, shown only while placement or quality-indicator data is missing: "Data on placements and teaching quality and infrastructure is not available yet, so choosing the matching priority does not change your list for now. Lower fees, Admission chance and accreditation do." It disappears by itself when such data is published (Stage 12d). tests/ui_real.test.js +1 test.

## Tests
618 Python tests pass (2 skipped); JS with real data 123 tests, 117 pass, 6 skipped.
