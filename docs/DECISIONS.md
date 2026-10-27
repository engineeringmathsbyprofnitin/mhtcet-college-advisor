# Decisions log

## 2026-10-25: Static data files + engine running in the student's browser
(see the entry's reasons in the earlier version of this file; summary) Capacity must not depend on a server: data is published as small hashed files, the browser loads only what it needs and runs engine.js locally. Google Sheet / Apps Script is optional only.

## 2026-10-26: Source discovery follows links, never guesses addresses
The official addresses follow no pattern (menu slugs differ every year; the file server host contains the year), so discovery starts at https://cetcell.mahacet.org/, reads the CAP menu and follows only links it finds.

## 2026-10-26: The admission year is decided by evidence, not by the calendar
A year counts as established only when real, reachable CAP cutoff documents exist for it. Between cycles the last established year stays current and is flagged. No January or July boundary is assumed.

## 2026-10-26: Walls are respected, never bypassed
robots.txt is obeyed (unreadable robots.txt = host skipped); CAPTCHA, login and password pages stop the run and are reported; the password-protected Cutoff Explorer is not used; redirects to hosts outside the official allow-list are not followed; about 1 request per second, hard request cap.

## 2026-10-26: Look-alike documents are kept apart
'Vacant Seats after CAP IV (ACAP)', court-order/new-institute vacancy lists, Diploma cutoff lists and the seat matrix are classified separately and never substituted for the Round IV / Round III vacancy position or the main cutoff lists.
