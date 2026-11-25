# What to do when something goes wrong (steps for the site owner)

Rule of the whole system: **a failed step never publishes anything**. When a workflow is red, the website keeps showing the last good data. Nothing is urgent just because one run is red.

## How to look
GitHub repository -> **Actions** tab. Each line is one run: green tick = fine, red cross = failed, yellow dot = running. The names (what each does) are in docs/STAGE14C.md. You do not have to understand the log: say **"red"** plus the workflow name in the chat and I read the saved report and give you the exact fix.

## The page says "The data has not changed for N days"
- Outside CAP (no new list published) this can be normal.
- During CAP: open Actions -> "Discover and archive official documents" and "Publish website data (preview)". If either shows red crosses for several days, say "red". If both are green, CET Cell has simply not published a new list.
- Also check the official CET Cell site; this site is a helper, not the official source.

## A workflow is red
1. Open the red run, note the workflow name (and the red step name if you can see it).
2. Tell me "red" + the name. If you can, paste the line that starts with FAIL or Error; the real reason is usually higher up in the step, not at the end.
3. The previous data stays on the site meanwhile.
You can try "Re-run all jobs" once yourself (top right of the run): official sites sometimes have a short outage.

## Run something by hand
Actions -> choose the workflow on the left -> **Run workflow** (green button) -> Run workflow. The publish workflow ("Publish website data (preview)") is the one that puts new data on the page; run it by hand after you upload an NBA or NAAC file (it also runs by itself every day around 12:00 noon in India).

## Make the public page show the old test data again (undo "going public")
Open `frontend/config.js` in GitHub (pencil icon), find the line `var PUBLIC_DATA_FOLDER = "data-real/";` and change it back to `"data/"`, Commit. (Today the public page still uses "data/".)

## Once a year: the fee list of the new admission year
Nothing to do in the normal case: the weekly "Read the approved fees" run looks for the new year's FRA portal itself (it tries a few likely addresses on the official FRA host and keeps one only if the portal answers with the expected list). Until the FRA publishes the new list, the cards show the last known fees, labelled "2026-27 fee list (the 2027-28 fee is not published yet)".
Only if the log of that run says **ACTION NEEDED** for several weeks after the FRA has published the new fees, tell me "FRA new year" and send the portal address (copy it from the browser); I prepare a one-line change for you. The run is not red in this case.

## Once or twice a year: NBA and NAAC lists
Follow docs/REFRESH_NBA_NAAC.md (download the Excel list, replace the file, wait for the green run, then run the publish workflow by hand).

## Notifications
GitHub normally emails you when a run fails. In GitHub -> your profile picture -> Settings -> Notifications, look for the Actions section and make sure failed workflow runs are switched on for email. (I cannot check your account from here.)

## Never do
- Never edit files inside `data/normalized`, `data/archive` or `frontend/data-real` by hand: the workflows own them.
- Never delete a file that is tracked by the repository to "clean up".
