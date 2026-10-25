# Stage 5B: put the data files online and check them (about 10 minutes)

1. Unzip `mhtcet-stage5b.zip`.
2. Open your repository `mhtcet-college-advisor` on github.com. Click **Add file -> Upload files**.
3. Drag in the folders `frontend`, `database`, `recommendation`, `tests`, `docs` and `backend` from the unzipped folder. Same-named files are replaced (for example `frontend/config.js` and `docs/ARCHITECTURE.md`).
   If GitHub says there are too many files, upload the folders in two or three batches.
4. Click **Commit changes**.
5. Wait about 2 minutes, then open (replace YOURNAME with your GitHub user name):
   `https://YOURNAME.github.io/mhtcet-college-advisor/frontend/data-check.html`
   (If Pages is not on: Settings -> Pages -> Source "Deploy from a branch", branch main, folder / (root), Save.)
6. You should see a line starting **OK - data version SYN-v1, admission year 2026-27 (SYNTHETIC test data, not real). 4 cutoff files, about 139 KB in all.**
7. Click **Run sample**. Expected: "Done in ... ms. Downloaded about 111 KB from 4 file(s). 9 results (synthetic data)." followed by five colleges.
8. Open the same page on your phone and run it there. Note the milliseconds shown.
9. Tell me: what the OK line says, the "Done in ... ms" line on computer and phone, and any line starting PROBLEM.
