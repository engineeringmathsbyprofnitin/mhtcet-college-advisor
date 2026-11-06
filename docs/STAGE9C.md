# Stage 9c: master tables and the automatic reading run (built; GitHub run pending)

## Master tables (data/normalized/master/, 1.4 MB, built from the 14 normalized cutoff files)
| File | What it holds |
|---|---|
| `colleges.csv` | one row per institute code: latest name, latest status, latest home university, first/last year listed, number of courses, number of name changes, which lists. `district` and `city` are blank on purpose (the cutoff lists do not contain them). |
| `courses.csv` | one row per choice code: base code (10 digits) and letter suffix, institute code, full course name (from the State list), where the name came from, status, home university, years listed, name changes |
| `seat_codes.csv` | every seat code split into its printed parts (family, General/Ladies, category, H/O/S letter and its meaning, variant), where and when it appears, how many cells |
| `home_universities.csv` | the 14 home-university values with how many colleges and courses use each |
| `college_name_history.csv`, `course_name_history.csv` | every name each code has used, by year (renames never destroy history) |
| `master_report.json` | counts and any problems |

## Numbers (real data)
- **403 colleges** (387 in the 2026-27 lists, 16 only in older years); 33 colleges and 12 courses changed name at some point (all kept in the histories).
- **2,511 courses**; only 1 appears solely in an All India list (its shortened name is used and marked).
- **105 seat codes, all recognised** (regular 54, PWD 24, defence 17, orphan 4, PHC 2, and TFWS, EWS, minority, all-India-seat). Only the first letter G/L and the last letter H/O/S are interpreted, because the lists' own legend defines them. Other parts (the R in DEFR.../PWDR..., the final letter of ORPHAN codes, the older PHC codes) are stored as printed.
- **0 problems:** one name per institute per list, every course code begins with its institute code.

## Home universities (for the form's possible dropdown)
Savitribai Phule Pune University (85 colleges), Mumbai University (47), Dr. Babasaheb Ambedkar Marathwada University (25), Shivaji University (20), Kavayitri Bahinabai Chaudhari North Maharashtra University (19), Rashtrasant Tukadoji Maharaj Nagpur University (15), Punyashlok Ahilyadevi Holkar Solapur University (14), Sant Gadge Baba Amravati University (12), Swami Ramanand Teerth Marathwada University (11), Gondwana University (7), plus three single/special cases: Deemed to be University (2 colleges), Dr. Babasaheb Ambedkar Technological University, Lonere (1), SNDT Women's University (1). A further value, **"Autonomous Institute"** (132 colleges, 962 courses), is not a university: autonomous institutes have no home university.

## The automatic run (.github/workflows/parse-documents.yml, "Read the archived documents")
1. Installs the PDF tool, runs the offline self-tests.
2. Downloads the 14 archived cutoff PDFs from the releases (`gh release download`); the readers refuse any file whose fingerprint does not match the archive.
3. Reads the State lists, then the All India lists, then builds the master tables, **all into a temporary folder `build/normalized`**.
4. Writes a readable summary on the run page.
5. **Only if every step succeeded** replaces `data/normalized` and commits it. If anything is incomplete or wrong, the previous data is kept (last-known-good).
Runs by hand and every Monday 04:47 UTC (after the archive job).

## Known limits
- The first run on GitHub is the live test: poppler (the PDF tool) there may be a different version from the one used so far, which could shift word positions slightly. The readers' completeness checks would then fail loudly instead of publishing wrong data.
- The master tables hold only what the cutoff lists contain; district, city, fees, accreditation, placement, hostel etc. come in later stages.
