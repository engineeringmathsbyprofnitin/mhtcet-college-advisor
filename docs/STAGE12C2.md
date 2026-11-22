# Stage 12c-2 - the NAAC list (owner-downloaded) is read

Probe result (2026-11-20): "Probe the NAAC site" ended with exit code 1 (screenshot from the owner: no pages, no file candidates). GitHub cannot read the NAAC site, so the official list is downloaded by the owner and uploaded, as for NBA. The NAAC dashboard address given by the owner (an IP address) is not reachable from the build environment either.

File: `data/manual/naac/Institutions_accredited_by_NAAC_having_valid_accreditation-as_on_14082025_1.xlsx` (NAAC list "valid accreditation as on 14-08-2025"; sheets "Colleges" 7,566 rows and "Transition Autonomous Colleges" 290 rows, the second one is not used: no grade).
`ingestion/naac_import.py` -> `data/normalized/naac/naac_institutions.csv` + `naac_report.json`: the 2,324 Maharashtra rows (state found by scanning the address for a state name), with name, affiliating university, address, cycle, CGPA, grade, date of declaration (ISO) and the list date. Grades: A++ 37, A+ 162, A 326, B++ 430, B+ 453, B 692, C 224. Problems (unknown grade, bad date, duplicate AISHE id, state unreadable...) are reported, not guessed; the CGPA-to-grade band check only warns.
Important facts for the next parts:
- The list has NO end date. 124 of the Maharashtra rows were declared more than five years before the list date although the list says "valid", so an end date (declaration + 5 years) would be wrong for them: none is computed. The website can show: grade, CGPA, date of declaration, "on NAAC's list as on 14 Aug 2025".
- The list is from 14 Aug 2025: colleges accredited after that date are missing, and accreditations that ended after it are still listed. A newer list must be downloaded and uploaded to refresh.
- Locality/district parts of the address are only hints (columns locality_hint, district_hint); matching to website colleges (12c-3) uses the name and the full address text.
Next: 12c-3 match NAAC institutions to the website colleges (owner confirms doubtful pairs, as for NBA), 12c-4 accreditation rows + packaging + card display, 12c-5 workflow wiring and phone check.

- Fix (2026-11-21): the reader and its tests use only the standard library (a named-sheet .xlsx reader, like the NBA one). The first version imported openpyxl, which is not installed in the "Publish website data" self-test step, so that step failed. A test now guards against any top-level openpyxl/pandas/numpy import.
