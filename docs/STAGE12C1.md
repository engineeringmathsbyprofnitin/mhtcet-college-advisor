# Stage 12c-1 - probe of the official NAAC site

Goal: find the current official list of NAAC-accredited institutions (name, state, CGPA, grade, validity) so Stage 12c can show the NAAC grade of each college.
Findings before building (2026-11-20): NAAC's own list pages could not be read from the build environment; the only official Excel files cited publicly are old (2020, 2022 editions); websites that republish lists (news and college-portal sites, Scribd copies, Wikipedia) are unofficial and are NOT used as a source. NAAC's data service is reported to need an India-based connection.
So: `ingestion/naac_probe.py` + workflow "Probe the NAAC site" (run by hand). It sends at most 10 requests (robots.txt, home page, up to 2 pages that look like accreditation/institution pages, then HEAD/first-byte checks of up to 4 candidate Excel/PDF files), obeys robots.txt, stops at any login/CAPTCHA, downloads no list, submits no form. It saves what it saw in `data/raw/naac-probe/` (home.html, hop pages, probe_report.json).
`ingestion/http_client.py`: the host allowlist now also contains naac.gov.in and its subdomains (nothing else changed).
If the probe says the site cannot be read from GitHub (blocked, time-out) or shows no list file, the owner downloads the official list by hand (browser in India) and uploads it, as was done for NBA.
Tests: tests/test_stage12c1.py (8 offline tests, no website is contacted).
