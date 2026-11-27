# Stage 16a: "How to read these results" on the page

The page already had a disclaimer (footer, results footer, PDF) and a privacy statement, but nothing that explained the labels, the cutoff figures, the order, the data sources or the gaps. Added a closed-by-default section (HTML `<details>`, no script, works under the Content-Security-Policy) above the footer of frontend/index.html:
- what the page does (earlier CAP rounds, not a prediction);
- where the numbers come from (CET Cell lists, FRA fees, NBA/NAAC lists; the top line shows when the data changed; NBA/NAAC lists are downloaded by hand a few times a year and each card shows its list date);
- what a cutoff is, and that a later round can show a higher figure (as printed);
- the four labels exactly as the engine shows them: Historically more suitable, Possible but uncertain, Ambitious choice, Limited evidence;
- how the order is chosen (higher past cutoffs first = demand, not an official quality score; priorities, branch order, fees, accreditation adjust a little);
- what is not known yet (placements, teaching, infrastructure; "No NBA/NAAC record found" is not "not accredited");
- check the official CET Cell website before filling the option form.
The text contains no years, percentages or counts, so it cannot go stale.

tests/help_page.test.js (4 tests) keeps the text honest: every label equals an engine label; the claims (three earlier years, vacancy rounds, no placement/teaching/infrastructure data yet, strength weight) are checked against the engine's settings. If someone later adds placement data or changes a label, the test fails and the text must be updated. (The test caught my first draft: the engine label is "Ambitious choice", not "Ambitious".)
