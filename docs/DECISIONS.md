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
