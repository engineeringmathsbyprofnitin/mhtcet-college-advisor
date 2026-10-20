# Architecture

## Data flow
```
Official CET Cell / college / accreditation sources
        |  (GitHub Actions, scheduled + manual)
        v
Discovery -> Download -> Raw archive (data/raw, checksums)
        v
Parsing (Python) -> Normalization -> Validation
        v (only if valid; else keep last-known-good)
Google Sheets database (+ data version, last-updated record)
        v
Apps Script API (health, status, recommend, detail)
        v
GitHub Pages frontend -> ranked report
```

## Components and independence
| Component | Tech | Talks to |
|---|---|---|
| Ingestion pipeline | Python, GitHub Actions | Official sites; writes normalized data / Sheet |
| Database | Google Sheets (tabs below) | Pipeline writes, API reads |
| API | Google Apps Script web app | Sheet (read), frontend (JSON) |
| Frontend | HTML/CSS/JS on GitHub Pages | API only |
| Recommendation engine | Deterministic rules, documented | Runs inside API (same logic mirrored in tests) |

The frontend only needs the API URL (one config file). Pipeline and frontend never depend on each other, so data updates need no website rebuild, and the database or API can be migrated later with the same JSON contract.

## Planned Google Sheet tabs
Colleges, Branches, HistoricalCutoffs, CurrentCutoffs, Vacancies, Fees, Accreditation, Placements, QualityIndicators, SourceDocuments, RefreshStatus, DataVersion.
Seat intake (sanctioned/approved) is stored separately from vacancies and is never used as vacancy.

## Key design decisions
1. Stable college/branch codes are identifiers; names are never used alone to merge records.
2. Raw files are immutable; normalized records point back to them.
3. Publishing is all-or-nothing per validated dataset version.
4. Calculated ratings are labelled "system estimate" with a documented method.

## Known risks (to investigate in later stages)
- CET Cell portals may use changing URLs, CAPTCHA, or PDF-only layouts; fallback = manual upload of files to data/raw.
- Apps Script quotas (daily executions, URL fetch, runtime limits); migration path = same schema on a small free-tier hosted API.
- GitHub Actions scheduled runs are limited and can be delayed; cadence will be modest.
- Official admission-year boundaries must be verified from CET Cell, not assumed.
