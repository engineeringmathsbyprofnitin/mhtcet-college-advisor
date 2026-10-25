# Architecture (updated 2026-10-25)

## Data flow
```
Official CET Cell / college / accreditation sources
        |  (GitHub Actions, scheduled + manual)
        v
Discovery -> Download -> Raw archive (data/raw, checksums)
        v
Parsing (Python) -> Normalization -> Validation (database/validate_data.py)
        v  only if valid; otherwise the previous published data stays live
Publishing (database/export_static.py) -> frontend/data/  (manifest + hashed files)
        v
Static hosting (GitHub Pages now; Cloudflare Pages or own hosting later)
        v
Student's browser: loads only needed files -> runs engine.js locally -> ranked report
```
See docs/DECISIONS.md for why the engine runs in the browser instead of on a server.

## Components
| Component | Tech | Notes |
|---|---|---|
| Ingestion pipeline | Python, GitHub Actions | Stages 7-14 |
| Source tables | CSV following database/schema.json | Validated before publishing |
| Publisher | database/export_static.py | All-or-nothing; keeps last-known-good |
| Website | HTML/CSS/JS | frontend/ ; engine.js + dataloader.js |
| Recommendation engine | recommendation/engine.js | Same file runs in browser, Node tests and Apps Script |
| Optional admin/backup API | Google Sheet + Apps Script | Built in Stage 5; not required; not part of the student path |

## Key design decisions
1. Stable college/branch codes are identifiers; names are never used alone to merge records.
2. Raw files are immutable; normalized records point back to them.
3. Publishing is all-or-nothing per validated dataset version.
4. Calculated ratings are labelled "system estimate" with a documented method.
5. No server computes anything per student, so capacity does not depend on a server.

## Known risks (to investigate in later stages)
- CET Cell portals may use changing URLs, CAPTCHA, or PDF-only layouts; fallback = manual upload of files to data/raw.
- Real data file sizes and phone speed must be measured (Stage 9).
- GitHub Pages bandwidth is a soft 100 GB per month; Cloudflare Pages (free, unlimited bandwidth) is the planned fallback.
- Official admission-year boundaries must be verified from CET Cell, not assumed.
