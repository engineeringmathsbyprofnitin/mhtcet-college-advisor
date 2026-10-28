# The raw document archive (Stage 8)

## Where the original files live, and why
| What | Where | Why |
|---|---|---|
| The small record of every document (address, meaning, fingerprint, size, dates) | `data/raw/manifest.json` in the repository | Tiny, readable, tracked by git |
| The original PDF files | **GitHub Releases**, one release per admission year (`raw-2026-27`, `raw-2025-26`, ...) | Releases have no limit on total size or download bandwidth (each file must be under 2 GiB); a normal repository should stay under about 1 GB and blocks files over 100 MB (checked against GitHub's documentation, 28 Oct 2026) |
| Latest run reports | `data/raw/download_report.json`, `data/raw/discovery/latest.json` | Small |
Measured from the real report: the files we need are 17 files, about 57 MB; all 41 listed files are about 136 MB. Expect roughly 50 MB of new files per year.

## What is downloaded (ingestion/policy.py)
- Current year: cutoff lists of every available CAP round for Maharashtra State (MH) and All India (AI).
- Current year: vacancy positions of CAP Round IV and Round III only (never I or II).
- Current year: the seat matrix (sanctioned seats; kept apart from vacancy).
- Each of the three previous years: the final available cutoff round per group (2025-26 Round IV, 2024-25 and 2023-24 Round III).
- Not downloaded yet: Diploma lists, the after-CAP (ACAP) vacancy list, court-order / new-institute vacancy lists, Round II vacancy, earlier rounds of previous years, previous years' seat matrices.

## Rules the downloader follows
1. **Only new or changed files are downloaded.** A file counts as unchanged only if its size matches and at least one server validator (ETag or Last-Modified) matches the archived version. Size alone is never proof.
2. **Every file is checked before it is accepted:** not empty, not a web page, complete (matches the server's stated size), a PDF signature at the start and an end marker at the end, within the size limit (100 MB per file, 300 MB per run).
3. **A bad or failed download never replaces a good file.** The earlier version stays current.
4. **A changed document becomes a new version beside the old one.** Nothing is deleted or overwritten. The run reports "CHANGED" so that anything built from the old version is re-read.
5. **Identical content is stored once** even if it appears at two addresses.
6. **Files are named by fingerprint** (`<first 16 characters of SHA-256>__<original name>`), so a name can never point to different content.
7. Same politeness as discovery: robots.txt obeyed, official hosts only, about 1 request per second, request cap.
8. If an upload to the release fails, the file is fetched again on the next run and retried.

## Checking integrity
`python -m ingestion.archive verify` re-computes the fingerprint of every stored file present on the computer and compares it with the manifest.
Later stages fetch a file with `gh release download <tag> --pattern <asset name>` and verify its fingerprint before reading it.

## Risks and how they are handled
- **The release is deleted or the repository is lost:** the manifest still has each document's official address, size and fingerprint, so the file can be downloaded again from the official site (if it is still there) and proven identical. A once-a-year download of the releases to your own computer or drive is a sensible extra backup.
- **The official site replaces a file:** detected and recorded as a new version; the old one is kept.
- **The files are public:** they are official public documents and the repository is public, so the releases are public too.
