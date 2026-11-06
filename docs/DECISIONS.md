# Decisions log

## 2026-10-25: Static data files + engine running in the student's browser
Capacity must not depend on a server: data is published as small hashed files, the browser loads only what it needs and runs engine.js locally. Google Sheet / Apps Script is optional only.

## 2026-10-26: Source discovery follows links, never guesses addresses
The official addresses follow no pattern, so discovery starts at https://cetcell.mahacet.org/, reads the CAP menu and follows only links it finds.

## 2026-10-26: The admission year is decided by evidence, not by the calendar
A year counts as established only when real, reachable CAP cutoff documents exist for it. Between cycles the last established year stays current and is flagged.

## 2026-10-26: Walls are respected, never bypassed
robots.txt is obeyed; CAPTCHA, login and password pages stop the run; the password-protected Cutoff Explorer is not used; redirects to hosts outside the official allow-list are not followed; about 1 request per second, hard request cap.

## 2026-10-26: Look-alike documents are kept apart
ACAP list, court-order / new-institute vacancy lists, Diploma cutoff lists and the seat matrix are classified separately and never substituted for the Round IV / Round III vacancy position or the main cutoff lists.

## 2026-10-28: Original documents are stored in GitHub Releases, not in git
17 needed files are about 57 MB (about 50 MB more each year). A repository should stay under about 1 GB and blocks files over 100 MB; Releases have no total size or bandwidth limit (each file under 2 GiB). The repository keeps only `data/raw/manifest.json` (address, meaning, SHA-256 fingerprint, size, dates, release asset name). One release per admission year; files named by fingerprint; never overwritten.

## 2026-10-28: A bad download never replaces a good file
Downloads are checked (complete, right file type, size limits). A rejected or failed download keeps the earlier archived version current. A replaced official file becomes a new version beside the old one and is reported as CHANGED.

## 2026-10-28: Only what the pipeline needs is downloaded
Current year MH and AI cutoffs of all rounds, vacancy positions of Rounds IV and III only, the current seat matrix, and the final round per group of each of the previous three years. Diploma, ACAP, court-order lists and others stay undownloaded until the owner decides.

## 2026-10-29: Nothing the parsers do may be silent
A reader must (1) prove completeness by counting what is printed against what was read (every bracketed percentile), (2) report any line or code it cannot place instead of absorbing it, (3) never turn a blank into zero, never correct source figures, and (4) refuse to read a file whose fingerprint does not match the archive. Real-file traps (overflow pages, wrapped headings, multi-letter codes) each get a test.

## 2026-10-29: Stage 9 is split into 9a, 9b, 9c
9a State lists (done), 9b All India lists, 9c master tables and the automatic GitHub run. Vacancy lists and the seat matrix stay in Stage 11.

## 2026-10-29: Normalized cutoff files are kept in the repository
data/normalized/cutoffs_mh/ is 2.4 MB compressed for 7 lists (148,004 cells) and is regenerated, byte for byte, from the archived PDFs.

## 2026-10-31: All India rows are never mixed across exams; blank cutoffs stay blank
Each All India row keeps its merit exam (JEE, NEET, MHT-CET, with PCB/PCM variants) and its bracketed score as printed. Only MHT-CET rows may later be compared with an MHT-CET percentile. A row with no printed cutoff is kept as an empty cutoff with a note, never filled or zeroed.

## 2026-10-31: Uploads are batched
To spare the owner repeated uploads, each new zip of Stage 9 is cumulative (the 9b zip contains 9a; the 9c zip will contain 9a and 9b). The owner may upload once after 9c.

## 2026-11-04: Master tables only contain what the lists contain
Colleges and courses are derived from the cutoff lists; district, city, website, fees, accreditation and similar facts stay blank until a real source provides them. Names are kept in histories (renames never destroy history); a State-list course name is never replaced by the shortened All India name. Seat codes are split only where the lists' legend defines the letters; other parts stay as printed.

## 2026-11-04: The automatic reading run keeps last-known-good data
New tables are built in a temporary folder and replace data/normalized only if every reader reports complete and problem-free; otherwise nothing is replaced and the run page says so.
