# Stage 14d-1: "Data updated" line and the recovery guide

Owner's decision (2026-11-24): the line shows the date the published data last REALLY changed.
- frontend/app.js `dataStatusText`: "Data updated on 23 Nov 2026 · data version ... · admission year ...". The date is manifest.last_successful_update, which the daily publish guard (14c) leaves untouched when nothing changed, so it is the date of the last real change (UTC date; in India the clock may be a few hours ahead).
- More than 10 days without change (the earlier limit was 14): adds "The data has not changed for N days. Outside the CAP season that can be normal; during CAP please also check the official CET Cell website." Exactly 10 days gives no notice.
- Missing or unreadable date: "Data update date unknown", no notice, no crash.
- docs/RECOVERY.md: plain-English guide for red workflows, a stale page, going back to the old data, the yearly FRA address, NBA/NAAC refresh, notifications.

## Tests
tests/data_status.test.js (4 tests; the function is cut out of app.js and run alone). tests/ui_stage6.test.js line 47 now expects the new wording (deliberate change of the old pattern "Data version ... last updated 2026-10-20"); its pass count stays 22.
## Not verified
How the line looks on the phone.
