# Decisions log

## 2026-10-25: Static data files + engine running in the student's browser (replaces "Apps Script API as the main backend")
**Why:** the owner expects thousands of students, possibly at the same moment (for example on a results day). Google Apps Script allows about 30 simultaneous executions per user and Google can change its limits, so it could fail under a burst. Static files on a CDN have no such cap, cost nothing, and the engine already runs in a browser.
**What changes:** the pipeline publishes validated data as small files (`frontend/data/`); the website downloads only the files a student needs and runs `engine.js` locally. Student inputs never leave the device.
**What stays:** schema, validator, engine, tests, the form. The Google Sheet and Apps Script API (Stage 5 code) are kept as an optional admin/backup route but are not needed and need not be set up.
**Trade-offs accepted:** data files and engine code are public (all data is official and public anyway); first visit downloads data (measured/estimated in docs/STATIC_DATA.md); very old phones may be slow.
**Later:** if the owner buys hosting, only `DATA_BASE_URL` in `frontend/config.js` changes.
