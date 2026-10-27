# What the official CET Cell sources look like (observed 26 Oct 2026)

I read these pages with a web page reader, not with the project's own downloader. Page structure below is what the reader showed; the live GitHub Action run (docs/STAGE7_SETUP.md) is what proves the project's code can read the same pages.

## Route to the engineering documents
1. `https://cetcell.mahacet.org/` has a **CAP** menu listing years: 2026-2027, 2025-2026, 2024-2025, 2023-2024, 2022-2023. A separate **CETs** menu lists the same years but is the entrance-exam portal, not admissions.
2. Each year links to a CAP page. **The addresses follow no pattern** (`/cap-_2026-27/`, `/cap-_2025-26/`, `/2024-2025/`, `/admissions/`, `/2022-2023-3/`), so addresses must be read from the menu, never guessed.
3. The 2026-27 CAP page lists every course. Under "Under Graduate Courses", **B.E/ B.Tech** leads to `https://fe2026.mahacet.org/StaticPages/HomePage` (other courses have their own portals, for example `me2026`, `bca2026`, `dse2026`).
4. That engineering portal's home page has an "Important Links" list and a table "Seat Matrix and Cut Off Lists of CAP Round for Previous Years" covering 2023-24, 2024-25 and 2025-26.

## What exists for admission year 2026-27 (portal status: admission process closed)
- Cutoffs, CAP Rounds I, II, III, IV, each for **MH** (Maharashtra State) and **AI** (All India); plus a Diploma list for Round IV.
- Vacancy positions for CAP Rounds II, III and IV (named "Provisional Vacancy Position for CAP Round-N").
- A separate list "Vacant Seats after CAP IV (ACAP)" and a special list "Provisional Vacancy Position for New Institute as per Court Order in CAP Round-III".
- Seat matrix (Round I), merit lists, allotment lists, brochure, off-campus institute list.
- Documents sit on a Microsoft Azure file server (`cappublicdocs2026.blob.core.windows.net`). The year is part of that host name, so the host changes each year.

## Previous years (from the portal's own table)
| Year | Cutoff rounds published |
|---|---|
| 2025-26 | I, II, III, IV (MH, AI, Diploma for IV) |
| 2024-25 | I, II, III (MH, AI; Diploma for III). **No Round IV** |
| 2023-24 | I, II, III (MH, AI; Diploma for III). **No Round IV** |
Consequence: for the two older years the "latest round" is Round III. The engine already uses the highest round available for each year and shows that round; Round III cutoffs are not exactly comparable with Round IV cutoffs, which the report already labels.

## Traps the code was written to avoid (all covered by tests)
- File names are inconsistent: `2026ENGG_CAP1_MH_CutOff_V1.pdf` (with a version suffix) but `2026ENGG_CAP4_MH_CutOff.pdf`; older years omit the group (`2025ENGG_CAP1_CutOff.pdf` is the MH list) and use `View` as the link text. Meaning is therefore read from link text and table headings first, file name second.
- Two look-alike vacancy lists: **"Provisional Vacancy Position for CAP Round-IV"** (used for the Round IV rule) versus **"Vacant Seats after CAP IV (ACAP)"** (seats left after all rounds; stored separately, not used).
- A court-order vacancy list for new institutes is flagged as supplementary and kept apart from the main round list.
- The seat matrix is never treated as vacancy.
- Placeholder "-" links in the table (no Round IV in older years) are ignored.

## Walls and limits found
- **Cutoff Explorer** (`cetcell.mahacet.org/cutoff-explorer/`) is **password protected**. It is not used and no attempt is made to get past it. The public PDFs are the route.
- robots.txt of the three hosts has not been read yet; the code reads and obeys it at run time. If it cannot be read, that host is skipped and the report says so.
- The project only talks to `*.mahacet.org`, `*.mahacet.org.in` and `cappublicdocsYYYY.blob.core.windows.net`. Redirects to any other address (for example a login server) are not followed.
- About 1 request per second per host, hard cap of 150 requests per run, at most 2 retries and only for temporary errors. It checks that each file opens (HEAD request only) and downloads nothing yet.

## Open questions for the owner (no action needed now)
1. **Which list is "the Round IV vacancy"?** The brief says "CAP Round IV vacancy position", so the code uses the "Provisional Vacancy Position for CAP Round-IV" list. The ACAP list is kept separately. To be confirmed in Stage 11 (a possible later feature: show ACAP seats as extra information).
2. **Diploma lists**: not used for first-year admissions unless you decide otherwise.
3. **Candidate groups**: only MH and AI cutoff lists exist for each round. How "Other Than Maharashtra (OMS)", J&K and Defence candidates appear (they have their own merit lists) will be examined when the documents are read in Stage 9.
