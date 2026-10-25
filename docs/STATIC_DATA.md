# Static data publishing (Stage 5B)

## How it works
1. **Source tables** (CSV files that follow `database/schema.json`) are checked by the full validator.
2. `python database/export_static.py <csv_folder> frontend/data` publishes them. It refuses to publish if there is any validation error and then leaves the previous files untouched (last-known-good stays live).
3. Output in `frontend/data/`:
   - `manifest.json`: the pointer. Data version, admission year, last successful update, synthetic flag, and the list of files with SHA-256 fingerprints. Written last.
   - `base.<hash>.json`: the small tables (colleges, branches, seat types, vacancies, fees, accreditation, placements, hostels, quality estimates, source documents, update log).
   - `cutoffs/<SEATTYPE>.<hash>.json`: all historical and current cutoffs for one seat type (for example GOPENS).
   File names contain a content hash, so a browser can never combine files from two versions, and files can be cached for a long time.
4. In the browser, `dataloader.js` reads the manifest (always fresh), loads the base file, works out which seat types apply to the student, downloads **only** those cutoff files, checks every fingerprint, and calls the engine. A missing or altered file stops everything with a clear message; partial data is never used.
5. Only validated rows are published. Seat intake is deliberately not published, so it can never be mistaken for vacancy. Internal columns (validation status, row ids, retrieval dates) stay in the database.

## Size and speed
Measured on my side with the synthetic data (not real):
- Published synthetic data: about 140 KB in all; a typical student (OBC, female) downloads about 111 KB from 4 files.
- Stress test: the synthetic data replicated about 60 times (4,740 branch choices, 110,000 cutoff rows) ran the engine in about 0.2 s in Node on a server computer. A phone may be several times slower.
- At that scale a cutoff file is about 1.8 MB before compression. My copies compressed to about 70 KB, but copies of the same rows compress unrealistically well, so **do not rely on that number**.
**My estimate, not a measurement:** real data may mean roughly 2-4 files and 1-2 MB compressed for a typical student. This will be measured in Stage 9 with the real files; if too large, files can be split further (for example by year or by round) without changing the website's design.
Hosting servers compress JSON automatically (GitHub Pages and Cloudflare Pages both do).

## Updating the data
Until Stage 14, publishing is a manual command (needs Python). In Stage 14 a GitHub Action will run it on a schedule, so you never have to; it will commit only validated output. **Rollback:** revert the data commit in GitHub; the manifest then points to the previous files.

## Moving to your own hosting later
Copy the `frontend/` folder to the new host. If the data lives elsewhere, change `DATA_BASE_URL` in `frontend/config.js`. Nothing else changes.

## Known limits
- Historical cutoffs older than three years are still published; pruning will be decided with real data.
- Browsers without the Web Crypto feature skip the fingerprint check (very old browsers, or pages not served over https).
- The data-check page is a technical tool, not for students.
