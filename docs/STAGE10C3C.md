# Stage 10c-3c - publishing the real data: workflow, preview, go-public switch

## What was built
- `.github/workflows/publish-website-data.yml` ("Publish website data (preview)"): runs by hand (Actions -> Run workflow) and automatically after "Read the archived documents" succeeds. Steps in order: self-tests -> automatic plan -> check the read data -> build tables -> package and validate website files in a temporary folder -> replace `frontend/data-real` -> save (commit) only the expected paths. If any step fails nothing is replaced and the previous files stay (last-known-good). Reports are kept with the run.
- Preview: the page at `.../frontend/index.html?preview=1` loads `data-real/` (the real data) and shows a red PREVIEW banner. The normal address still loads `data/` (today: synthetic test data).
- **Go public = one line**: in `frontend/config.js` change `var PUBLIC_DATA_FOLDER = "data/";` to `var PUBLIC_DATA_FOLDER = "data-real/";`. (Reverse the same line to go back.)

## Tests (tests/test_stage10c3c.py, 10; tests/ui_real.test.js now 5)
Workflow structure (triggers, minimal permissions, order of steps, temporary folder, only expected paths committed, every module exists); preview switch (normal address -> data/, ?preview=1 -> data-real/, look-alikes like ?preview=10 do not switch, go-public line is unique); page shows the preview banner and real version.

## NOT verified
- The workflow has not run on GitHub yet (cannot be run from the build sandbox): first run is the real test. Needs "Read the archived documents" to have succeeded (it did for 9c).
- That a commit made by the workflow triggers the GitHub Pages build (normally yes; the earlier "Read the archived documents" job commits the same way).
- Phone/browser look; loading speed on a slow mobile connection.
- Each data change adds new data files to the repository history (about 4-8 MB); weekly runs only commit when the data actually changed.
