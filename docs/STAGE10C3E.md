# Stage 10c-3e - "Download PDF" that works on phones

Problem (owner's phone): the page's "Print or save as PDF" button used the browser's print command (`window.print()`). Many phone browsers do not offer, or do not complete, "Save as PDF" from it: in-app browsers (WhatsApp, Telegram, Instagram), iOS browsers, some Android browsers. This is a property of the phone browser, not of the data; it cannot be fixed by changing the print styles alone.

Fix: `frontend/pdfexport.js` builds a real PDF file inside the browser (no library, no internet, no server) and downloads it through the normal download path. New button **Download PDF**; the old button is now **Print** (still works where the browser supports it). The PDF is text only (Helvetica, A4 portrait): title, data version / admission year / last update, the "guidance not a guarantee" notice, all warnings, then for each result: rank, college, branch, suitability and score, the three past years' cutoffs, the current year's latest cutoff with Rounds I-IV, vacancy, fee and the explanation lines, with page numbers. Characters outside Latin-1 (for example Devanagari) are shown as "?" (never dropped silently).

Also: the real package now writes a refresh-status row so the page and the PDF show "last successful data update" (time = when the CET Cell documents were last discovered) instead of "Not available".

## Tests
tests/test_stage10c3e.py (5): the generated PDF is read back with poppler (valid, A4, 6 pages for 20 results, every result present, notices present, update time present, no text off the page) and by its own xref structure; special characters; wrapping. tests/ui_real.test.js: button builds the report from the shown results. Engine 48, loader 14, old page tests 21 unchanged.

## NOT verified
- Opening/saving the PDF on a real phone (iOS Safari opens it in the viewer, Android Chrome downloads it: expected, not tested here). In-app browsers (e.g. WhatsApp) may block downloads: open the page in Chrome/Safari.
- Non-Latin text (Marathi) is not supported in the PDF yet.
- A phone with very little memory and 20 results: the PDF is small (about 20-30 KB).

## Observation for Stage 13 (ranking), not fixed here
For a 92-percentile student the top results are colleges whose cutoffs are far below 92, because the default priority is "admission chance". Some colleges' current-year cutoffs jump between rounds (e.g. 13.2, 16.8, 56.6, 24.0) because the lowest cutoff over all eligible seat types is used per round. Ranking and the choice of the representative seat type will be reviewed in Stage 13.
