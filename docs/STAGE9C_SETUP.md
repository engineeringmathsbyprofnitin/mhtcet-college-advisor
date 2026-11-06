# Stage 9: upload once and run the reading on GitHub (about 15 minutes)

This zip is cumulative: it contains everything from Stage 9a, 9b and 9c. You do not need the earlier Stage 9 zips.

## 1. Upload the files
1. Unzip `mhtcet-stage9c.zip`.
2. In your repository click **Add file -> Upload files**, drag in the folders `ingestion`, `tests`, `data` and `docs`, and click **Commit changes**. (Same-named files are replaced. The folder `data` adds `data/normalized/` with the readings of all 14 lists.)

## 2. Create the new workflow file
3. Click **Add file -> Create new file**. In the name box type exactly: `.github/workflows/parse-documents.yml` (typing each slash makes a folder).
4. Open `.github/workflows/parse-documents.yml` from the unzipped folder in Notepad, copy everything, paste it into the big text box, and click **Commit changes**.

## 3. Run it
5. **Actions** tab -> **Read the archived documents** -> **Run workflow** -> green **Run workflow** button. Wait about 5-8 minutes.
6. Open the finished run and look at the **Summary**. Success looks like three blocks (State lists, All India lists, Master tables), every list showing "yes" under Complete, and at the bottom "Overall: everything complete, no problems".
7. In the step "Save the normalized data in the repository" you will see either "Normalized data unchanged" (best case) or a new commit. Either is fine if the Summary says everything is complete.

## Send me
The Summary text. If the run is red, copy the first error line of the red step. A red run keeps your previous data, so nothing is damaged.
