# Stage 7: run the live source discovery (about 10 minutes, nothing to install)

This makes GitHub's computers read the official CET Cell pages once, politely, and write a report. It does not download the large PDF files yet.

## Upload
1. Unzip `mhtcet-stage7.zip`.
2. In your repository click **Add file -> Upload files** and drag in the folders `ingestion`, `tests`, `docs` and the hidden folder `.github`. 
   - If your computer hides `.github` (it starts with a dot): on Windows open the unzipped folder, click **View -> Show -> Hidden items**; on a Mac press Command+Shift+. (dot). 
   - If you cannot upload `.github`, instead click **Add file -> Create new file**, type the name `.github/workflows/discover-sources.yml` (typing the slashes creates the folders), open the same file from the zip in Notepad, copy everything, paste, and click **Commit changes**.
3. Click **Commit changes**.

## Run it
4. Open the **Actions** tab of the repository. If GitHub asks, click **I understand my workflows, enable them**.
5. In the left list click **Discover official sources**, then **Run workflow** (right side) and the green **Run workflow** button.
6. Wait 2-4 minutes. A green tick means finished; a red cross means the run found a problem or a wall (that is useful information, not a break).
7. Click the run, then look at the **Summary** at the top. You should see "Current admission year: 2026-27 (confirmed)", a table of years and rounds, and "Would use for 2026-27: cutoff round IV; vacancy round IV".
8. The full report is saved in your repository as `data/raw/discovery/latest.json`.

## Send me
Copy the Summary text (or a screenshot). If the run is red, also copy the line starting with OBSTACLE. Do not worry if something looks different from what I expected: the point of this run is to check my reading of the real site.

Notes: the same job runs automatically every Monday. GitHub switches scheduled jobs off if a repository has no activity for 60 days; pressing Run workflow once switches them back on.

## Re-run after the fix (27 Oct 2026)
1. Unzip `mhtcet-stage7-fix1.zip` and upload its folders (`ingestion`, `tests`, `docs`) the same way. Same-named files are replaced.
2. Actions -> Discover official sources -> Run workflow. Wait 3-4 minutes (it is slightly slower now).
3. In the Summary you should see **"Documents found: 41; unreachable: 0."** and about 48 requests. The year table is unchanged.
4. Send me the Summary lines again (or just "unreachable: 0").
