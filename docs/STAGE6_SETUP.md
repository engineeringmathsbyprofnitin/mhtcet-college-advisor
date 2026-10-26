# Stage 6: connect the form to the results (about 15 minutes)

## Upload
1. Unzip `mhtcet-stage6.zip`.
2. In your GitHub repository click **Add file -> Upload files**. Drag in the folders `frontend`, `recommendation`, `backend`, `tests` and `docs`. Same-named files are replaced. Click **Commit changes**.
3. Wait about 2 minutes. If the page looks unchanged afterwards, force a refresh (Ctrl+F5 on a computer; on a phone, close the tab and open it again).
4. Open `https://YOURNAME.github.io/mhtcet-college-advisor/` (it opens the form).

## Check these (tick each)
1. At the top you should see a red banner **TEST DATA ...** and a line "Data version SYN-v1 - admission year 2026-27 - last updated 2026-10-20".
2. **Normal case.** Percentile 93.5, Maharashtra State candidate, category OBC, gender Female, branches 1 Computer Science and Engineering, 2 Information Technology, 3 Computer Engineering, districts Pune then Mumbai Suburban, budget 200000 (tuition only), priority "Good placements". Click **Show my recommendations**.
   - It shows "Showing the 5 leading choices of 9 suitable choices found."
   - A table (or, on a phone, cards) with 5 results; each has college name and code, branch name and code, three past-year cutoffs, latest cutoff and round, vacancy, fee, infrastructure, teaching, placement, NBA, NAAC and a suitability label.
   - Click **Show more suitable choices (6-20)**: 4 more appear.
   - Click **Why this choice?** on the first one: explanation lines and sources appear.
   - Some cells say "Not available" and some say "Vacancy data unavailable". That is correct for this test data.
3. **Any district.** Tick "Any district", percentile 85, only branch Civil Engineering, category Open, gender blank: 10 results.
4. **No match.** Percentile 75, Civil Engineering, district Nashik, category Open: a friendly "No choices matched" message, no table.
5. **Category without data.** Same as step 2 but category ST: a yellow note says no cutoff data for "ST" is loaded and only Open cutoffs were used.
6. **Phone view.** On your phone repeat step 2. Each result should appear as a card with labelled lines, readable without sideways scrolling. Take a screenshot.
7. **Computer view.** The table should scroll sideways inside its own box. Take a screenshot.
8. **Offline check.** Open the page, switch your internet off, press the button: you should see a friendly message about your internet connection, not a blank page. Switch the internet back on and press again: results appear.
9. **Print.** Click **Print or save as PDF** and look at the preview.

## Send me
Screenshots from steps 2, 6 and 7, and a note of anything that looked wrong, was hard to read, or was confusing.
