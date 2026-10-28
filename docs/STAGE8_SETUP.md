# Stage 8: download and archive the documents (about 15 minutes)

## 1. Upload the new code
1. Unzip `mhtcet-stage8.zip`.
2. In your repository click **Add file -> Upload files**, drag in the folders `ingestion`, `tests` and `docs`, and click **Commit changes**. Same-named files are replaced; three new files appear in `ingestion` (`policy.py`, `archive.py`, `download.py`).

## 2. Replace the workflow text
3. In your repository open `.github/workflows/discover-sources.yml` and click the pencil icon (Edit).
4. Select all text, delete it, open the same-named file from the unzipped folder `.github/workflows/` in Notepad, copy everything, paste it, and click **Commit changes**.
   (The workflow is now called **Discover and archive official documents**.)

## 3. Optional tidy-up
5. Open `.gitignore` in your repository, click the pencil, and add these lines at the end, then commit:
```
data/raw/files/
plan.txt
uploaded.txt
*.tmp
```

## 4. Run it
6. **Actions** tab -> **Discover and archive official documents** -> **Run workflow** -> green **Run workflow** button.
7. Wait about 5-10 minutes (about 57 MB is downloaded at roughly one file per second).
8. Open the finished run. The **Summary** shows two reports: the source discovery report (as before) and a **Document archive report** listing 17 documents with the result `new` for each.
9. Open the step **Store new original files in GitHub Releases**: you should see 17 lines starting with `stored:`.
10. Go to the main page of your repository: on the right side **Releases** should now show 4 releases named `raw-2026-27`, `raw-2025-26`, `raw-2024-25`, `raw-2023-24`. Open `raw-2026-27` and check that 11 files are listed (8 cutoff lists, 2 vacancy lists, 1 seat matrix).
11. In `data/raw/` you should now see `manifest.json` and `download_report.json`.

## 5. Run it a second time (this tests change detection)
12. Run the workflow again. This time the Document archive report should say **unchanged 17** and **Downloaded this run: 0.0 MB**, and the storing step should say nothing to store.

## Send me
The Summary text of both runs (first and second), and any red step with its first error line. If a download is rejected, the report says why (for example "a web page was returned instead of a document"), and I will adjust.
