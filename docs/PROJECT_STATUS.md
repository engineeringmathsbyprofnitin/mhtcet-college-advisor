# Project status

## Completed
- Stage 1: repository structure and documents.
- Stage 2: student input form (frontend/index.html, styles.css, app.js, config.js) + root index.html redirect.

## Verified (automated, simulated browser jsdom, 10 checks passed)
- Empty form blocked; percentile range/decimals checked; duplicate branch rejected; fee with commas parsed; "Any district"; Balanced/priority exclusivity; valid input produces expected request JSON.

## NOT yet verified
- Appearance on real phones/desktops, screen-reader use, GitHub Pages deployment (owner must check after upload).

## Not implemented
- No database, recommendation engine, API, data ingestion, results table, workflows.

## Known issues / placeholders
- Category, candidate-type, extra-eligibility and branch lists in frontend/config.js are PROVISIONAL, typed by hand; to be replaced with official CET Cell lists (Stages 7-9).
- "Automatic" admission year is only a flag for now; real detection is Stage 7.
- Some seat types (e.g., ladies, state-level vs home-university) may need extra inputs once official rules are checked.

## Next task
Stage 3: database schema + synthetic test data (docs/PROMPTS.md has the prompt).
