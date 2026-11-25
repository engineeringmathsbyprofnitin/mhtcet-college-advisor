# Stage 14e: fee wording and the robot finds the new FRA portal itself

Owner's request (2026-11-24): do not say "Not available" when an older fee list exists, and do not make the owner edit a line every year.

## 14e-1 Fee wording (frontend/results.js, pdfexport.js, app.js, engine copies)
- Since 14b the cards already show the last known fees. Now the card says which list it is: "... · 2026-27 fee list" and, when the fee list is older than the admission year, "· 2026-27 fee list (the 2027-28 fee is not published yet)". The same remark is added to the "Tuition alone ... total will be higher" case. "Not available" remains only for colleges that are not in any FRA list.
- New `meta.admissionYear` (engine, all three copies identical) = the year the student applies for (from the data version's "admission=" summary; older packages: the cutoff year). The results footer and the PDF say "admission year 2027-28 (latest cutoffs: 2026-27)" when they differ. The page header now says "latest cutoffs 2026-27" instead of "admission year 2026-27", because in January that was wrong (deliberate change of two old test patterns).

## 14e-2 The robot finds the new portal (ingestion/fra_fees.py, package_real.py)
- For a year with no known address the weekly run builds up to three candidates on the official FRA host (host `ay27-28.mahafraportal.org`; folder number of the newest known year and the next two) and sends ONE cheap request to each (the sub-type list the reader needs anyway). A candidate is accepted only if the portal answers with exactly one sub type coded ENGG; the reader then still checks the whole fee table as before. robots.txt is obeyed; a login, 401/403/429 or robots block stops the search at once (no bypass).
- A found address is saved in data/raw/fees/fra_sites_found.json (committed by the existing fees workflow) and used from then on, also for the source link on the cards. Only well-formed official addresses are accepted from that file.
- If nothing is found: the run is NOT red; it prints ACTION NEEDED and keeps re-reading the newest known list. The owner only has to act if that message persists for weeks after the FRA published the new fees (docs/RECOVERY.md).
- The folder number is a guess (25 for 2026-27). I could not test against the real portal from here: unverified until the FRA opens the 2027-28 portal.

## Tests
tests/test_stage14e.py (13), tests/results_fee_display.test.js (5), tests/test_stage14b.py (fee-reader tests now use a stub fetcher: no network in tests), data_status/ui_stage6 patterns updated.
