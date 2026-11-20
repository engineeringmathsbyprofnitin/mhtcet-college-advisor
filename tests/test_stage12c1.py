import json, os, sys, tempfile, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from ingestion import naac_probe as N
from ingestion.http_client import PoliteFetcher, host_allowed

BASE = "https://www.naac.gov.in"
HOME = """<html><nav><a href="/">Home</a><a href="/index.php/assessment-accreditation">Assessment &amp; Accreditation</a>
<a href="https://evil.example/accreditation">Evil</a><a href="https://assessmentonline.naac.gov.in/">Portal</a><a href="javascript:void(0)">js</a>
<a href="/images/docs/ACCREDITATION_STATUS/Institutions_valid_2026.xls">Institutions with valid accreditation</a><a href="/images/docs/other/Annual_report.pdf">Annual report</a></nav></html>"""
HOP = """<html><a href="/images/docs/ACCREDITATION_STATUS/Accredited_institutions_list.pdf">Accredited institutions list</a><a href="/contact">Contact</a></html>"""


class Fake:
    def __init__(self, home=HOME, hop=HOP, robots=(404, b""), home_status=200):
        self.home, self.hop, self.robots, self.home_status, self.calls = home, hop, robots, home_status, []
    def send(self, method, url, headers, max_bytes, data=None):
        self.calls.append((method, url))
        if url.endswith("/robots.txt"): return self.robots[0], {}, self.robots[1]
        if url.rstrip("/") == BASE: return self.home_status, {}, self.home.encode()
        if url.endswith("/assessment-accreditation"): return 200, {}, self.hop.encode()
        if url.lower().endswith((".xls", ".pdf")):
            return 200, {"Content-Type": "application/vnd.ms-excel" if url.endswith(".xls") else "application/pdf", "Content-Length": "12345", "Last-Modified": "Mon, 02 Nov 2026 10:00:00 GMT"}, b""
        return 404, {}, b""


def go(fake):
    d = tempfile.mkdtemp(); f = PoliteFetcher(transport=fake, min_delay=0, sleep=lambda s: None, max_requests=10)
    return N.run(f, out_dir=d), d


class Probe(unittest.TestCase):
    def test_finds_candidate_files_and_checks_them_without_downloading(self):
        fake = Fake(); rep, d = go(fake)
        self.assertTrue(rep["verdict"].startswith("Site read: 3 candidate file link(s)") or rep["verdict"].startswith("Site read: 4"), rep["verdict"])
        urls = {c["url"]: c for c in rep["file_candidates"]}
        xls = [c for u, c in urls.items() if u.endswith("Institutions_valid_2026.xls")][0]
        self.assertEqual((xls["status"], xls["content_type"], xls["content_length"]), (200, "application/vnd.ms-excel", "12345"))
        self.assertTrue(any(u.endswith("Accredited_institutions_list.pdf") for u in urls))                     # found one page deeper
        self.assertFalse(any(u.endswith("Annual_report.pdf") for u in urls))                                     # off topic
        self.assertTrue(all(m == "HEAD" for m, u in fake.calls if u.lower().endswith((".xls", ".pdf"))))       # a file is only asked about, never downloaded
        self.assertTrue(os.path.exists(os.path.join(d, "probe_report.json"))); self.assertTrue(os.path.exists(os.path.join(d, "home.html")))

    def test_never_fetches_other_sites_but_reports_them(self):
        fake = Fake(); rep, d = go(fake)
        self.assertFalse(any("evil.example" in u for m, u in fake.calls)); self.assertIn("evil.example", rep["other_hosts_seen"]); self.assertIn("assessmentonline.naac.gov.in", rep["other_hosts_seen"])

    def test_request_budget(self):
        fake = Fake(); go(fake); self.assertLessEqual(len(fake.calls), 10)

    def test_unreadable_home_stops_with_a_clear_verdict(self):
        rep, d = go(Fake(home_status=403)); self.assertTrue(rep["verdict"].startswith("STOP: home not readable")); self.assertIn("403", rep["verdict"])

    def test_robots_disallow_stops(self):
        rep, d = go(Fake(robots=(200, b"User-agent: *\nDisallow: /\n"))); self.assertTrue(rep["verdict"].startswith("STOP")); self.assertIn("robots", rep["verdict"])

    def test_login_or_captcha_on_a_page_stops(self):
        rep, d = go(Fake(hop="<html>Please log in. <input type='password'></html>")); self.assertTrue(rep["verdict"].startswith("STOP: hop1 mentions a login or CAPTCHA"))

    def test_an_unreadable_side_page_is_noted_but_does_not_end_the_probe(self):
        rep, d = go(Fake())                                                                   # the Fake answers 404 for the portal page: skipped, files still found
        self.assertTrue(rep["verdict"].startswith("Site read: ")); self.assertTrue(any("skipped" in n for n in rep.get("notes", [])))

    def test_host_rules(self):
        for h in ("www.naac.gov.in", "naac.gov.in", "assessmentonline.naac.gov.in"): self.assertTrue(host_allowed(h), h)
        for h in ("naac.gov.in.evil.com", "evilnaac.gov.in", "naac.gov.in.cn"): self.assertFalse(host_allowed(h), h)
        self.assertTrue(host_allowed("www.nbaind.org")); self.assertFalse(host_allowed("evil.com"))


if __name__ == "__main__":
    unittest.main()
