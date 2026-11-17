import json, os, sys, tempfile, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from ingestion import fra_probe as F
from ingestion.http_client import PoliteFetcher, host_allowed
from urllib.parse import parse_qs

PAGE = F.PAGE
FORM = """<html><body><form method="post" action="outer.php?q=fee_search_report"><input type="hidden" name="tok" value="abc">
<select name="itype"><option value="">--</option><option value="1">H&amp;T</option><option value="2">Medical</option></select>
<select name="stype"><option value="">--</option><option value="E">ENGG - Bachelor of Engineering</option><option value="P">PHARM</option></select>
<select name="dist"><option value="">--</option><option value="14">Mumbai-City</option><option value="22">Pune</option></select>
<input type="submit" value="Get Report"></form></body></html>"""
RESULT = """<table><tr><th>Sr. No.</th><th>Inst ID</th><th>Inst Name</th><th>District</th><th>Stream</th><th>Status</th><th>Date of Meeting</th><th>Tuition Fee</th><th>Development Fee</th><th>Total Fee</th></tr>
<tr><td>1</td><td>EN3139</td><td>VIDYALANKAR INSTITUTE</td><td>Mumbai-City</td><td>ENGG</td><td>Approved</td><td>15-06-2026</td><td>176521</td><td>26479</td><td>203000</td></tr>
<tr><td>2</td><td>EN3182</td><td>THADOMAL SHAHANI</td><td>Mumbai-City</td><td>ENGG</td><td>Approved</td><td>05-05-2026</td><td>189034</td><td>26466</td><td>215500</td></tr></table>"""


class Fake:
    def __init__(self, page=FORM, result=RESULT, robots=(404, b"")):
        self.page, self.result, self.robots, self.calls = page, result, robots, []
    def send(self, method, url, headers, max_bytes, data=None):
        self.calls.append((method, url, data))
        if url.endswith("/robots.txt"): return self.robots[0], {}, self.robots[1]
        if method == "POST": return 200, {}, self.result.encode()
        return 200, {}, self.page.encode()


def go(fake, **kw):
    d = tempfile.mkdtemp(); f = PoliteFetcher(transport=fake, min_delay=0, sleep=lambda s: None, max_requests=6)
    return F.run(f, out_dir=d), d


class Probe(unittest.TestCase):
    def test_full_probe(self):
        fake = Fake(); rep, d = go(fake)
        self.assertEqual(rep["verdict"], "Test search answered: 3 table rows")
        self.assertEqual(rep["result_table"]["header"][1], "Inst ID"); self.assertEqual(rep["result_table"]["first_rows"][0][1], "EN3139")
        post = [c for c in fake.calls if c[0] == "POST"][0]; q = parse_qs(post[2].decode())
        self.assertEqual((q["itype"], q["stype"], q["dist"], q["tok"]), (["1"], ["E"], ["14"], ["abc"]))
        self.assertTrue(os.path.exists(os.path.join(d, "probe_report.json"))); self.assertTrue(os.path.exists(os.path.join(d, "page.html")))

    def test_at_most_three_requests(self):
        fake = Fake(); go(fake); self.assertLessEqual(len(fake.calls), 3)

    def test_captcha_stops_without_submitting(self):
        fake = Fake(page=FORM.replace("<form", "<div class='g-recaptcha'></div><form")); rep, _ = go(fake)
        self.assertTrue(rep["verdict"].startswith("STOP")); self.assertFalse(any(c[0] == "POST" for c in fake.calls))

    def test_login_stops(self):
        fake = Fake(page="<form><input type='password' name='p'></form>"); rep, _ = go(fake)
        self.assertTrue(rep["verdict"].startswith("STOP"))

    def test_captcha_in_answer_stops(self):
        rep, _ = go(Fake(result="<div>Please enter CAPTCHA</div>")); self.assertTrue(rep["verdict"].startswith("STOP"))

    def test_robots_disallow_stops(self):
        fake = Fake(robots=(200, b"User-agent: *\nDisallow: /\n")); rep, _ = go(fake)
        self.assertTrue(rep["verdict"].startswith("STOP")); self.assertEqual([c[0] for c in fake.calls], ["GET"]); self.assertTrue(fake.calls[0][1].endswith("robots.txt"))

    def test_robots_unreadable_stops(self):
        rep, _ = go(Fake(robots=(500, b""))); self.assertTrue(rep["verdict"].startswith("STOP"))

    def test_options_loaded_by_javascript_means_no_search(self):
        page = FORM.replace('<option value="E">ENGG - Bachelor of Engineering</option><option value="P">PHARM</option>', "") + "<script>$.post('sub.php', {t:1})</script>"
        fake = Fake(page=page); rep, _ = go(fake)
        self.assertIn("not in the HTML", rep["verdict"]); self.assertFalse(any(c[0] == "POST" for c in fake.calls)); self.assertTrue(rep["script_hints"])

    def test_no_form(self):
        rep, _ = go(Fake(page="<html><script>var a=1;</script></html>")); self.assertIn("No form", rep["verdict"])

    def test_get_form(self):
        fake = Fake(page=FORM.replace('method="post"', 'method="get"'), result=RESULT)
        orig = fake.send
        fake.send = lambda m, u, h, mb, data=None: (200, {}, RESULT.encode()) if "itype=" in u else orig(m, u, h, mb, data)
        rep, _ = go(fake); self.assertEqual(rep["result_table"]["rows"], 3)

    def test_host_list(self):
        self.assertTrue(host_allowed("ay26-27.mahafraportal.org")); self.assertTrue(host_allowed("fe2026.mahacet.org"))
        self.assertFalse(host_allowed("mahafraportal.org.evil.com")); self.assertFalse(host_allowed("evil.com"))

    def test_other_host_never_contacted(self):
        fake = Fake(); f = PoliteFetcher(transport=fake, min_delay=0, sleep=lambda s: None)
        r = f.fetch("https://evil.example/x"); self.assertEqual(r.blocked, "host_not_allowed"); self.assertEqual(fake.calls, [])


if __name__ == "__main__":
    unittest.main()
