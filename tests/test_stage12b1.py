import json, os, sys, tempfile, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from ingestion import nba_probe as N
from ingestion.http_client import PoliteFetcher, host_allowed

BASE = "https://www.nbaind.org"
PROG = BASE + "/accreditationprogram/AccreditedProgram?ID=abc%3D%3D&tier=xyz%3D%3D&name=q"
HOME = """<html><nav><a href="/Home">Home</a><a href="/Accreditation">Accreditation</a>
<a href="/accreditationprogram/AccreditedProgram?ID=eng2&tier=t2&name=a">UG Tier II</a>
<a href="/accreditationprogram/AccreditedProgram?ID=abc%3D%3D&tier=xyz%3D%3D&name=q">UG Tier I (WA)</a>
<a href="https://evil.example/accreditationprogram/x">Evil</a><a href="javascript:void(0)">js</a></nav></html>"""
PAGE = """<html><form method="post" action="AccreditedProgram"><input type="hidden" name="__VIEWSTATE" value="zzz">
<select name="state"><option>Select</option><option>Maharashtra</option></select><select name="program"><option>Select</option><option>Computer Engineering</option></select>
<select name="inst"><option>Select</option><option>A COLLEGE</option><option>B COLLEGE</option></select><input type="submit" value="Search"></form>
<input type="button" value="Click here to Download in Excel" onclick="location.href='/Download/Excel?x=1'">
<table><tr><th>Name of the Institution</th><th>Program</th><th>Level</th><th>Accreditation Status</th><th>Accreditation Period</th></tr>
<tr><td>A COLLEGE</td><td>Computer Engineering</td><td>Under Graduate</td><td>ACCREDITED</td><td>1st July 2025 to 30th June 2028</td></tr></table>
<script>$.post('x.php')</script></html>"""


class Fake:
    def __init__(self, home=HOME, page=PAGE, robots=(404, b""), nav_page=None):
        self.home, self.page, self.robots, self.nav, self.calls = home, page, robots, nav_page, []
    def send(self, method, url, headers, max_bytes, data=None):
        self.calls.append((method, url))
        if url.endswith("/robots.txt"): return self.robots[0], {}, self.robots[1]
        if url.rstrip("/").endswith("/Home"): return 200, {}, self.home.encode()
        if url.endswith("/Accreditation") and self.nav is not None: return 200, {}, self.nav.encode()
        if "accreditationprogram" in url.lower(): return 200, {}, self.page.encode()
        return 404, {}, b""


def go(fake):
    d = tempfile.mkdtemp(); f = PoliteFetcher(transport=fake, min_delay=0, sleep=lambda s: None, max_requests=10)
    return N.run(f, out_dir=d), d


class Probe(unittest.TestCase):
    def test_finds_tier1_page_and_reports_structure(self):
        fake = Fake(); rep, d = go(fake)
        self.assertEqual(rep["picked"]["text"], "UG Tier I (WA)"); self.assertEqual(rep["picked"]["url"], PROG)
        self.assertTrue(rep["verdict"].startswith("Page read: 1 form(s), 1 table(s)"))
        self.assertEqual([x["options"] for x in rep["forms"][0]["fields"] if x["kind"] == "select"], [2, 2, 3])
        self.assertTrue(any("Excel" in h for h in rep["excel_hints"])); self.assertEqual(rep["tables"][0]["header"][0], "Name of the Institution")
        self.assertTrue(os.path.exists(os.path.join(d, "program_page.html"))); self.assertTrue(os.path.exists(os.path.join(d, "probe_report.json")))

    def test_no_search_is_submitted_and_few_requests(self):
        fake = Fake(); go(fake); self.assertTrue(all(c[0] == "GET" for c in fake.calls)); self.assertLessEqual(len(fake.calls), 6)

    def test_other_hosts_are_not_followed(self):
        rep, _ = go(Fake()); self.assertFalse(any("evil" in l[0] for l in rep["program_links"]))

    def test_second_hop(self):
        home = '<a href="/Accreditation">Accreditation</a>'
        nav = '<a href="/accreditationprogram/AccreditedProgram?ID=abc&tier=x">UG Tier I (WA)</a>'
        rep, _ = go(Fake(home=home, nav_page=nav)); self.assertEqual(rep["picked"]["text"], "UG Tier I (WA)"); self.assertEqual([s["step"] for s in rep["steps"]], ["home", "hop1", "program_page"])

    def test_no_link_found(self):
        rep, _ = go(Fake(home="<a href='/About'>About</a>")); self.assertIn("No accredited-programs link", rep["verdict"])

    def test_captcha_on_data_page_stops(self):
        rep, _ = go(Fake(page=PAGE + "<div class='g-recaptcha'></div>")); self.assertTrue(rep["verdict"].startswith("STOP"))

    def test_login_word_on_home_is_only_noted(self):
        rep, _ = go(Fake(home=HOME + "<input type='password' name='pw'>")); self.assertTrue(rep["login_words_on_home"]); self.assertTrue(rep["verdict"].startswith("Page read"))

    def test_robots_disallow_stops(self):
        fake = Fake(robots=(200, b"User-agent: *\nDisallow: /\n")); rep, _ = go(fake)
        self.assertTrue(rep["verdict"].startswith("STOP")); self.assertEqual(len([c for c in fake.calls if not c[1].endswith("robots.txt")]), 0)

    def test_robots_unreadable_stops(self):
        rep, _ = go(Fake(robots=(500, b""))); self.assertTrue(rep["verdict"].startswith("STOP"))

    def test_best_prefers_tier1_wa(self):
        self.assertEqual(N.best([("u1", "UG Tier II"), ("u2", "UG Tier I (WA)")])[0], "u2")
        self.assertEqual(N.best([("u1", "PG"), ("u2", "UG Tier II")])[0], "u2"); self.assertIsNone(N.best([]))

    def test_host_list(self):
        self.assertTrue(host_allowed("www.nbaind.org")); self.assertTrue(host_allowed("nbaind.org")); self.assertFalse(host_allowed("nbaind.org.evil.com")); self.assertFalse(host_allowed("nbaind.com"))

    def test_unexpected_error_leaves_report(self):
        import io, contextlib
        orig, od = N.run, N.OUT; N.run = lambda *a, **k: 1 / 0; N.OUT = tempfile.mkdtemp()
        try:
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf): code = N.main()
            self.assertEqual(code, 1); self.assertIn("ZeroDivisionError", json.load(open(os.path.join(N.OUT, "probe_report.json")))["verdict"])
        finally: N.run, N.OUT = orig, od


if __name__ == "__main__":
    unittest.main()
