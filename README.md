# MHT-CET College Advisor

A free, public website that helps Maharashtra students (MHT-CET / CAP admissions) shortlist engineering colleges and branches based on their percentile, category, preferred branches and districts, budget, and priorities.

> **Status: Stage 1 of 16 complete (planning and structure only). No website, API or data pipeline exists yet.** See `docs/PROJECT_STATUS.md`.

## How it will work
Official CET Cell sources -> automated ingestion (GitHub Actions + Python) -> raw archive -> parsing -> validation -> Google Sheets database -> Apps Script API -> GitHub Pages website -> ranked report.

## Folders
| Folder | Purpose |
|---|---|
| `frontend/` | Student-facing website (HTML/CSS/JS) for GitHub Pages |
| `backend/apps-script/` | Google Apps Script API code |
| `ingestion/` | Python scripts: discover, download, parse CET Cell documents |
| `database/` | Schema and Google Sheet tab definitions |
| `data/raw/` | Original downloaded files (never edited) |
| `data/normalized/` | Cleaned, validated records |
| `recommendation/` | Ranking engine rules and code |
| `tests/` | Automated tests (synthetic data clearly labelled) |
| `docs/` | Requirements, architecture, status, decisions |
| `.github/workflows/` | Scheduled updates and Pages deployment |

## Core rules (never to be broken)
- Never invent cutoffs, vacancies, fees, accreditation or placement data. Missing = "Not available".
- Vacancy comes only from CAP Round IV, else Round III vacancy-position documents. Never from intake/seat matrix.
- A cutoff is not an admission guarantee.
- Publish only validated data; keep last-known-good data on failure.

## Disclaimer
Final eligibility, option selection and admission depend on official CET Cell rules, the CAP process, seat availability and verified credentials.
