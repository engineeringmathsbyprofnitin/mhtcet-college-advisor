# Project status

## Completed and owner-verified
Stages 1-4, 5B, 6 and 7 (live discovery on the real CET Cell site: 2026-27 confirmed, 41 documents, 0 unreachable).

## Stage 8 built (code + simulated-site tests); live run pending
- ingestion/policy.py: which documents are needed and why (17 files, about 57 MB measured from the real report).
- ingestion/download.py: polite download, change detection (size + ETag/Last-Modified), content checks (complete, right type, size limits), SHA-256 fingerprint, versions, never replaces a good file with a bad one.
- ingestion/archive.py: manifest (data/raw/manifest.json), content-based file names, upload plan / confirm / verify.
- .github/workflows/discover-sources.yml: discover -> download -> store originals in GitHub Releases (one per year) -> save reports; weekly + manual, optional force.
- docs/RAW_ARCHIVE.md: design, limits (checked against GitHub's documentation), risks.

## Verified (automated)
146 Python tests pass across Stages 7 and 8 (Stage 8: 12 policy, 39 download/archive, 8 workflow): first run archives 17 files with safe names and records address, meaning and fingerprint; a second run downloads nothing; a replaced file becomes a second version with the old one kept and a CHANGED alert; same bytes with new validators are not a change; a file whose earlier upload failed is fetched again; identical content at two addresses stored once; truncated downloads, web pages in place of PDFs, wrong signatures, missing end markers, empty replies, 404s, repeated 503s, robots.txt refusals, file-size and total-size limits and the request budget all fail safely without damaging earlier good copies; manifest is deterministic and written atomically; file names cannot escape their folder; the workflow uses only GitHub's built-in token, never overwrites an original, never commits original files to git.

## NOT verified
- The real servers: whether the real PDFs pass the content checks (complete-file and PDF-signature checks), whether Last-Modified/ETag are honest on the fe2026 server, upload to GitHub Releases from the Action. The first live run (docs/STAGE8_SETUP.md) tests all of this.
- Nothing has been read inside the documents yet (Stage 9). Earlier caveats still apply: no real data in the recommendation engine, uncalibrated weights, reserved-can-use-Open-seats assumption, TFWS/Defence/PWD not applied.

## Open questions (docs/CETCELL_SOURCES.md)
Which list counts as the Round IV vacancy; Diploma lists; OMS/J&K/Defence; whether to add a home-university question to the form; JEE/NEET-based All India rows.

## Next task
Owner runs the live archive twice; I fix anything it shows; then Stage 9 (read the PDFs into tables).
