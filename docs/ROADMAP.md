# Roadmap (updated 2026-11-23)
1-4. Requirements, form, schema, engine - done
5B. Static data publishing + browser loader - done (owner verified)
6. Form connected to results table - done (owner verified)
7. Official source discovery + admission-year detection - done (verified live)
8. Download and archive the documents - done (verified live)
9a. State cutoff lists - done (148,004 cells)
9b. All India cutoff lists - done (10,615 rows)
9c. Master tables + automatic reading run - **built and tested; first live GitHub run pending (docs/STAGE9C_SETUP.md)**
10. Validation, historical comparison, which seat codes apply to which student, current-round fallback
11. Vacancy lists and seat matrix (Round IV -> III only); owner confirms which list counts as Round IV vacancy
12. Fees (12a), NBA (12b), NAAC (12c) - done. 12d placement, infrastructure, teaching, hostel evidence - NOT started (official/verifiable sources only; probe first)
13. Ranking and explanation review - built and tested (13a-13d-3, docs/STAGE13.md); owner's phone check pending; public page still on old data by owner's decision (switch = one line in frontend/config.js)
14. Scheduled updates (publish step) + failure recovery + admission-year rollover after CAP Round IV (fees, vacancy, NBA, NAAC year logic, FRA_SITES) + optional CAP-schedule banner
15. Deployment hardening
16. Public testing, documentation, own-domain integration
