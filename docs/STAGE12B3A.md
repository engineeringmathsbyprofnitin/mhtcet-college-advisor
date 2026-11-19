# Stage 12b-3a - match NBA institutions to website colleges

Input: `data/normalized/nba/nba_programs.csv` (NBA lists downloaded by the site owner) and `data/normalized/tables/colleges.csv`.
Output: `data/normalized/nba/nba_institution_match.csv` (+ `nba_institution_match_report.json`), one row per NBA institution (name + place).

Status of each row:
- `linked` - clear match. Automatic only when the name score is >= 0.80 with a clear lead over the second best, or 0.65-0.80 with a bigger lead AND the printed place found in the college name/district. A different known district blocks a link. The printed place is also a tie-breaker (two "Government College of Engineering" in different cities).
- `doubtful` - plausible but not certain. NOT used until the owner confirms it in `data/manual/nba_institution_confirmations.csv` (columns: nba_institution, nba_place, decision yes/no, college_code).
- `no_college` - no plausible college on the website (for example a university that does not take part in CAP, or a college not in the CAP list). Not guessed.

Name handling: initials are kept together (D.Y. = dy), text in brackets is ignored, "&" = "and", common abbreviations (Engg, Mgt, Govt...) are expanded, rare words weigh more than common ones (IDF).
Known trap (tested): "D.Y. Patil College of Engineering and Technology" must not link to "Dr. V.K. Patil College" (Dharashiv).
Known data quirk: some NBA names contain mojibake (for example an apostrophe shown as "â€™"); the matcher still works, the importer is not changed in this stage.
Next: 12b-3a2 (owner confirms the doubtful list), 12b-3b (match programs to branches, write accreditation rows, package), 12b-3c (show on cards, tests, phone check).
