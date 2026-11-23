# How to refresh the NBA and NAAC lists (steps for the site owner)

The official sites cannot be read by the GitHub robot, so you download the Excel lists in your own browser.

## NAAC (about once or twice a year)
1. On www.naac.gov.in download the newest "Institutions accredited by NAAC having valid accreditation" Excel file. Keep the date (ddmmyyyy) in the file name.
2. GitHub repository -> folder `data/manual/naac/` -> open the old .xlsx -> three dots -> Delete file -> Commit. (Only ONE .xlsx may be there.)
3. Add file -> Upload files -> drag the new .xlsx into `data/manual/naac/` -> Commit.
4. This starts "Read the NAAC list" by itself (Actions tab). Wait for the green tick. If it is red, say "red".
5. Actions -> "Publish website data (preview)" -> Run workflow. Wait for green.
6. Open the site with `?preview=1` and check a college you know.
If new NAAC colleges are "doubtful", they are listed in `data/normalized/naac_link/naac_college_match_report.json`; they wait for your answer in `data/manual/naac_confirmations.csv`.

## NBA (when NBA publishes new lists)
1. On www.nbaind.org download the UG Tier I and UG Tier II lists (State = Maharashtra) as Excel.
2. Replace the files in `data/manual/nba/` the same way (delete old, upload new, update `sources.csv` lines).
3. "Read the NBA lists" starts by itself. Then run "Publish website data (preview)" by hand, as in step 5 above.

Note: "No NBA/NAAC record found" means only "not in our lists", never "not accredited".
