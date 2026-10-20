# Prompts for each stage
Paste the SHARED HEADER first, then the stage line. If the chat is new, also paste the latest checkpoint from the end of the previous reply.

## SHARED HEADER
You are building my MHT-CET College Advisor website (GitHub Pages + Google Apps Script + Google Sheets + Python/GitHub Actions). I am a maths professor, not a developer; give browser-only, step-by-step instructions. Rules: never invent data; vacancy only from CAP Round IV else Round III vacancy documents (never intake/seat matrix); current cutoff priority IV>III>II>I; use 3 previous completed admission years; keep last-known-good data; never claim anything works unless verified. Work in one small stage only. At the end give: files created, what was actually tested, what is not done, my exact next action (separating what I must do from what you did), a ZIP of only new/changed files, and a copyable checkpoint.

## STAGE LINES
- Stage 3: Start Stage 3: create the database schema (all tabs/columns, keys, provenance fields, validation rules) as docs + CSV templates, plus clearly-labelled SYNTHETIC test data (about 12 colleges, several branches, 3 years of cutoffs, current-year rounds, vacancies, fees).
- Stage 4: Start Stage 4: write the deterministic recommendation engine (JavaScript so it can run in Apps Script and the browser), document the ranking rules and limitations, and write tests using the synthetic data (including missing data and each priority setting).
- Stage 5: Start Stage 5: help me create the Google Sheet from the CSV templates and write the Apps Script API (health, status, recommend, detail endpoints). Give exact click-by-click steps for deployment and explain public-access implications first.
- Stage 6: Start Stage 6: connect the frontend to the deployed Apps Script URL, show the ranked results table (top 5 + "Show more suitable choices (6-20)"), and test the real endpoint including CORS.
- Stage 7: Start Stage 7: investigate https://cetcell.mahacet.org/ and discover the engineering CAP portal and documents; implement dynamic admission-year detection with tests. Report honestly any CAPTCHA/login/format obstacles and propose a manual-upload fallback.
- Stage 8: Start Stage 8: write the Python downloader and raw-file archive (checksums, source URLs, change detection) and a GitHub Actions workflow I can run manually; verify with real downloads.
- Stage 9: Start Stage 9: write real parsers for the downloaded Excel/CSV/HTML/PDF files and produce normalized data; test on the actual files.
- Stage 10: Start Stage 10: add validation, three-year historical cutoff comparison and the current-round fallback (IV>III>II>I) with tests.
- Stage 11: Start Stage 11: implement genuine vacancy processing with the strict Round IV then Round III rule, rejecting seat-matrix/intake data, with tests on real documents.
- Stage 12: Start Stage 12: collect fees, NBA/NAAC accreditation, placement, infrastructure and teaching evidence from official sources with provenance; document any estimated 0-10 ratings methodology.
- Stage 13: Start Stage 13: finalize ranking, per-college explanations and the full report table (all required columns, mobile-friendly, data-version stamp).
- Stage 14: Start Stage 14: set up scheduled GitHub Actions updates with validation, rollback to last-known-good data, and freshness reporting; prove it with a real run and a deliberate failure test.
- Stage 15: Start Stage 15: deploy to GitHub Pages and publish the Apps Script API; verify the public URL end to end.
- Stage 16: Start Stage 16: public testing checklist, user and maintenance documentation, and connecting my own domain/website without duplicating the app.
