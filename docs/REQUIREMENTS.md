# Requirements checklist (from the project brief)

Legend: [ ] not started

## Product
- [ ] Inputs: percentile (decimals), admission year (auto, changeable), candidate type, category, gender/other only if rules need it
- [ ] Ranked preferred branches (2-3+), ranked preferred districts (2-3+ or "Any district")
- [ ] Max annual fee budget; tuition vs total cost clearly distinguished
- [ ] Priorities: balanced, placements, teaching, infrastructure, lower fees, higher admission probability
- [ ] Output: top 5, plus "Show more suitable choices (6-20)"; fewer than 20 if fewer matches
- [ ] Per row: rank, college+code, branch+code, district, 3 historical cutoffs, latest current cutoff + round, vacancy + round, fee, infra, teaching, placement, NBA, NAAC, suitability label, sources
- [ ] Explanation per recommendation; "Not available" for missing data
- [ ] Mobile-friendly, accessible; data-version/last-updated shown; disclaimer shown

## Data rules
- [ ] Admission year computed dynamically (current + 3 previous completed years)
- [ ] Current-year cutoff priority: CAP IV > III > II > I; record round used
- [ ] Vacancy: CAP IV, else CAP III only; else "Vacancy data unavailable"; never from intake/seat matrix
- [ ] Provenance on every record (source, URL, file, year, publication date, retrieval date, validation status)
- [ ] Verified facts separated from system-estimated ratings (methodology documented)
- [ ] Do not assume NBA applies to all branches or NAAC is current without validity check

## Technology
- [ ] GitHub Pages frontend; Apps Script API; Google Sheets database
- [ ] Python + GitHub Actions ingestion, independent of frontend
- [ ] Last-known-good dataset, rollback on failed update
- [ ] No credentials in repo; no student personal data stored

## Process
- [ ] 16 staged development steps, each tested and recorded in PROJECT_STATUS.md
- [ ] Never claim a feature works unless verified
