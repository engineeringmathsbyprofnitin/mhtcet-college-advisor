# Project status

## Completed
- Stages 1-4: structure, form, schema v0.3 (16 tables), recommendation engine v0.2.
- Stage 5 (optional): Google Sheet workbook + Apps Script API. Not used by the website.
- Stage 5B: static data publishing (database/export_static.py), loader (frontend/dataloader.js), data-check page. Verified by owner on computer (473 ms) and phone (886 ms): 111 KB from 4 files, 9 results.
- Stage 6: the form now loads the data files, runs the engine in the browser and shows the ranked report (frontend/results.js, app.js, index.html, styles.css).

## Verified (automated)
148 tests pass in six suites: engine 48, loader 14, UI 21 (real page in a simulated browser), Apps Script API 22, exporter 15, schema 28. The UI tests cover: header and test-data banner; empty-form errors; top-5 table with working "Show more suitable choices (6-20)"; all 15 report columns with correct year headings; "Not available" / "Vacancy data unavailable" instead of blanks; tuition never presented as total cost; estimates labelled; explanations and sources per result; honest messages for few/zero results, unknown category, unsupported candidate type; focus handling; double-submit protection; friendly network-failure message and retry; tampered file refused; HTML injection impossible; accessibility basics; print and clear; no data typed by the student is sent anywhere or stored.
Changes made while building Stage 6: engine now warns when the student's own category has no cutoff list (previously silent); loader gained getManifest().

## NOT verified
- How the pages look and feel on real phones/computers (layout and CSS were not seen by me): owner checks per docs/STAGE6_SETUP.md.
- Real CET Cell data (none used). Real data size and phone speed (Stage 9).
- Weights/thresholds are uncalibrated; reserved-can-use-Open-seats is an assumption; TFWS/Defence/PWD not applied.
- Fingerprint check is skipped on browsers without Web Crypto (very old browsers / non-https).

## Known issues / placeholders
- Seat types, categories, candidate types and branch names are provisional (frontend/config.js and seat_types).
- Publishing data is a manual command until Stage 14.
- The results table has 15 columns; on desktop it scrolls sideways inside its box.

## Next task
Fix whatever the owner finds in the Stage 6 real-device check, then Stage 7: official CET Cell source discovery and dynamic admission-year detection.
