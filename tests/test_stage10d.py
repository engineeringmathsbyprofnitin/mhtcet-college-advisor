"""Stage 10d: official institute information (district etc.). The fixtures are RECONSTRUCTED from the page text shown by the CET Cell website; the first
live run in GitHub Actions is the real test of the HTML. Run: python -m unittest tests/test_stage10d.py -v"""
import csv, hashlib, json, os, shutil, sys, tempfile, unittest
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from ingestion import institutes as I
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."); FX = os.path.join(ROOT, "tests", "fixtures", "institutes")
def fx(n): return open(os.path.join(FX, n), encoding="utf-8").read()
HOST = "https://fe2026.mahacet.org"
NODE = shutil.which("node")

class R:                                                  # minimal stand-in for http_client.Response
    def __init__(self, text="", status=200, blocked=None):
        self.body = text.encode("utf-8"); self.status = status; self.blocked = blocked; self.error = None
    @property
    def ok(self): return self.status is not None and 200 <= self.status < 300 and not self.blocked
    @property
    def text(self): return self.body.decode("utf-8")
class Fake:
    def __init__(self, pages): self.pages, self.calls = pages, []
    def fetch(self, url, **k):
        self.calls.append(url); return self.pages.get(url, R(status=404))
def pages(**over):
    p = {HOST + "/StaticPages/frmInstituteList": R(fx("list.html"))}
    for c in ("01002", "06270", "06305"): p["%s/StaticPages/frmInstituteSummary.aspx?InstituteCode=%s" % (HOST, c)] = R(fx("summary_%s.html" % c))
    p.update(over); return p

class Parse(unittest.TestCase):
    def test_list_codes_and_count(self):
        codes, printed = I.institute_codes(fx("list.html")); self.assertEqual(codes, ["01002", "06270", "06305"]); self.assertEqual(printed, 3)
    def test_summary_fields(self):
        info, courses, probs = I.parse_summary(fx("summary_06270.html"), "06270")
        self.assertEqual(probs, []); self.assertEqual((info["district"], info["region"], info["status"], info["autonomy_status"], info["minority_status"]), ("Satara", "Pune", "Un-Aided", "Autonomous", "Non-Minority"))
        self.assertIn("Sadar Bazar", info["address"]); self.assertEqual(len(courses), 10)
        c = courses[1]; self.assertEqual((c["choice_code"], c["total_intake"], c["gender"]), ("0627019111T", "3", "Co-Education"))
        self.assertTrue(c["university"].endswith("Lonere"))
    def test_wrong_page_missing_district_foreign_course_bad_intake(self):
        self.assertTrue(any("asked for" in p for p in I.parse_summary(fx("summary_06270.html"), "06305")[2]))
        self.assertIn("missing district", I.parse_summary(fx("summary_06270.html").replace("<td>Satara</td></tr>\n<tr><td>Status", "<td></td></tr>\n<tr><td>Status"), "06270")[2])
        self.assertTrue(any("does not belong" in p for p in I.parse_summary(fx("summary_06270.html").replace("0627024210", "0999924210"), "06270")[2]))
        self.assertTrue(any("not a number" in p for p in I.parse_summary(fx("summary_06270.html").replace("<td>180</td>", "<td>many</td>"), "06270")[2]))
        self.assertIn("no course rows", I.parse_summary("<html><table><tr><td>Institute Code</td><td>06270</td></tr></table></html>", "06270")[2])

class Run(unittest.TestCase):
    def test_complete_run(self):
        f = Fake(pages()); insts, courses, rep = I.run(f, 2026, "2026-11-12T00:00:00Z")
        self.assertTrue(rep["complete"]); self.assertEqual((len(insts), len(courses), rep["requests"]), (3, 13, 4))
        self.assertEqual(rep["districts"], {"Amravati": 1, "Satara": 2}); self.assertEqual(insts[1]["total_intake"], "480"); self.assertEqual(rep["warnings"], [])
        self.assertEqual(insts[1]["page_sha256"], hashlib.sha256(fx("summary_06270.html").encode()).hexdigest())
    def test_one_failed_page_makes_the_run_incomplete(self):
        _, _, rep = I.run(Fake(pages(**{HOST + "/StaticPages/frmInstituteSummary.aspx?InstituteCode=06305": R(status=500)})), 2026, "t")
        self.assertFalse(rep["complete"]); self.assertTrue(any("06305" in p for p in rep["problems"]))
    def test_count_mismatch_on_list_page(self):
        _, _, rep = I.run(Fake(pages(**{HOST + "/StaticPages/frmInstituteList": R(fx("list.html").replace("<td>3.</td>", "<td>4.</td>"))})), 2026, "t")
        self.assertFalse(rep["complete"]); self.assertTrue(any("prints 4" in p for p in rep["problems"]))
    def test_a_wall_stops_everything(self):
        with self.assertRaises(I.Wall): I.run(Fake(pages(**{HOST + "/StaticPages/frmInstituteSummary.aspx?InstituteCode=06270": R("<html>Please enter the CAPTCHA to continue</html>")})), 2026, "t")
        self.assertFalse(I.looks_like_wall(fx("summary_06270.html")))
    def test_blocked_by_robots_is_reported(self):
        _, _, rep = I.run(Fake({HOST + "/StaticPages/frmInstituteList": R(blocked="robots_disallow_or_unreadable")}), 2026, "t")
        self.assertFalse(rep["complete"])
    def test_main_writes_nothing_when_incomplete(self):
        out = tempfile.mkdtemp(); real = I.PoliteFetcher
        try:
            I.PoliteFetcher = lambda **k: Fake(pages(**{HOST + "/StaticPages/frmInstituteSummary.aspx?InstituteCode=06305": R(status=404)}))
            self.assertEqual(I.main(["--out", out, "--year", "2026"]), 1); self.assertEqual(os.listdir(out), ["institutes_last_run_report.json"])      # only the report, no data files
            I.PoliteFetcher = lambda **k: Fake(pages()); self.assertEqual(I.main(["--out", out, "--year", "2026"]), 0)
            self.assertEqual(sorted(os.listdir(out)), ["institute_courses.csv", "institutes.csv", "institutes_last_run_report.json", "institutes_report.json"])
        finally: I.PoliteFetcher = real; shutil.rmtree(out)

class Build(unittest.TestCase):
    def test_districts_reach_the_website_tables(self):
        from ingestion import build_tables as B
        tmp = tempfile.mkdtemp()
        try:
            base = os.path.join(tmp, "n"); shutil.copytree(os.path.join(ROOT, "data", "normalized"), base, ignore=shutil.ignore_patterns("tables", "institutes"))
            insts, courses, rep = I.run(Fake(pages()), 2026, "2026-11-12T00:00:00Z"); I.write(os.path.join(base, "institutes"), insts, courses, rep)
            out = os.path.join(tmp, "tables"); r = B.build(base=base, outdir=out)
            cols = {c["college_code"]: c for c in csv.DictReader(open(os.path.join(out, "colleges.csv"), encoding="utf-8"))}
            self.assertEqual(r["colleges_with_district"], sum(1 for c in cols.values() if c["district"] != "Not available"))
            for code, d in (("06270", "Satara"), ("01002", "Amravati"), ("06305", "Satara")):
                if code in cols: self.assertEqual(cols[code]["district"], d); self.assertTrue(cols[code]["source_doc_id"].startswith("DOC-"))
            docs = {x["doc_id"]: x for x in csv.DictReader(open(os.path.join(out, "source_documents.csv"), encoding="utf-8"))}
            for c in cols.values(): self.assertIn(c["source_doc_id"], docs)
            self.assertTrue(any(x["doc_type"] == "college_list" for x in docs.values()))
            self.assertEqual(B.autonomy("Autonomous"), "autonomous"); self.assertEqual(B.autonomy("Non-Autonomous"), "non_autonomous"); self.assertEqual(B.autonomy("?"), "unknown")
        finally: shutil.rmtree(tmp)
    def test_institute_page_university_resolves_unknown_current_year_only(self):
        from ingestion import build_tables as B
        row = dict(year_label="2026-27", choice_code="0000111110", section="Home University Seats Allotted to Home University Candidates", home_university="")
        self.assertEqual(B.resolve_hu(row, {}, {"0000111110": "Mumbai University"}, "2026-27"), ("Mumbai University", "institute_page"))
        self.assertEqual(B.resolve_hu(dict(row, year_label="2025-26"), {}, {"0000111110": "Mumbai University"}, "2026-27")[1], "unknown")
        self.assertEqual(B.resolve_hu(row, {"0000111110": {"Pune", "X"}}, {"0000111110": "Mumbai University"}, "2026-27")[1], "institute_page")
class Diagnostics(unittest.TestCase):
    """The first live run died with 'request budget of 600 used up' and no information. Now: the budget follows the list, failures are logged, and a probe is quick."""
    def test_budget_follows_the_number_of_institutes(self):
        f = Fake(pages()); f.max_requests = 200; I.run(f, 2026, "t"); self.assertEqual(f.max_requests, 3 * 4 + 20)
    def test_budget_exceeded_is_caught_and_reported(self):
        class Tight(Fake):
            count = 0
            def fetch(self, url, **k):
                self.count += 1
                if self.count > 2: raise I.BudgetExceeded("request budget of 2 used up")
                return super().fetch(url)
        insts, _, rep = I.run(Tight(pages()), 2026, "t"); self.assertFalse(rep["complete"]); self.assertTrue(any("request budget" in p for p in rep["problems"]))
    def test_failures_are_logged_with_the_reason_and_listed_in_the_report(self):
        lines = []; _, _, rep = I.run(Fake(pages(**{HOST + "/StaticPages/frmInstituteSummary.aspx?InstituteCode=06305": R(status=503)})), 2026, "t", log=lines.append)
        self.assertTrue(any("06305" in x and "503" in x for x in lines)); self.assertTrue(any("06305" in x for x in rep["failures"]))
        self.assertTrue(any("list page read: 3 institute codes" in x for x in lines))
    def test_probe_reads_a_few_pages_and_never_claims_completeness(self):
        f = Fake(pages()); lines = []; insts, _, rep = I.run(f, 2026, "t", probe=2, log=lines.append)
        self.assertFalse(rep["complete"]); self.assertEqual(len(insts), 2); self.assertEqual(len(f.calls), 3); self.assertTrue(any("district='Satara'" in x or "district='Amravati'" in x for x in lines))
    def test_time_limit_stops_cleanly(self):
        ticks = iter(range(0, 1000, 100)); _, _, rep = I.run(Fake(pages()), 2026, "t", max_seconds=150, clock=lambda: next(ticks))
        self.assertFalse(rep["complete"]); self.assertTrue(any("time limit" in p for p in rep["problems"]))

@unittest.skipUnless(NODE, "node not installed")
class NoDistricts(unittest.TestCase):
    """If a data package ever has no district at all (institute pages not read), a district choice must not hide every college: it is not applied and the page says so."""
    def test_choice_not_applied_and_warning(self):
        import subprocess
        from ingestion import build_tables as B, package_real as PR
        tmp = tempfile.mkdtemp()
        try:
            base = os.path.join(tmp, "n"); shutil.copytree(os.path.join(ROOT, "data", "normalized"), base, ignore=shutil.ignore_patterns("tables", "institutes"))
            B.build(base=base, outdir=os.path.join(tmp, "tables")); data = os.path.join(tmp, "data"); PR.main(data, tables=os.path.join(tmp, "tables"))
            r = subprocess.run([NODE, os.path.join(ROOT, "tests", "helpers", "district_check.js")], env=dict(os.environ, DISTRICT_DATA_DIR=data, DISTRICT_PICK="Pune"), capture_output=True, text=True, cwd=ROOT)
            self.assertEqual(r.returncode, 0, r.stderr[-600:]); out = json.loads(r.stdout)
            self.assertIn("District data is not available yet", " ".join(out["warnings"])); self.assertGreater(len(out["satara"]), 0)
        finally: shutil.rmtree(tmp)

class Intake(unittest.TestCase):
    def test_intake_mismatch_is_a_warning_not_an_error(self):
        _, _, rep = I.run(Fake(pages(**{HOST + "/StaticPages/frmInstituteList": R(fx("list.html").replace("<td>480</td>", "<td>500</td>"))})), 2026, "t")
        self.assertTrue(rep["complete"]); self.assertTrue(any("06270" in w and "500" in w for w in rep["warnings"]))

NODE = shutil.which("node")
@unittest.skipUnless(NODE, "node not installed")
class WithDistricts(unittest.TestCase):
    """Real cutoff data + official districts for 3 colleges (from the reconstructed fixtures): the engine and the form must use them."""
    @classmethod
    def setUpClass(cls):
        import subprocess
        from ingestion import build_tables as B, package_real as PR
        cls.tmp = tempfile.mkdtemp(); base = os.path.join(cls.tmp, "n")
        shutil.copytree(os.path.join(ROOT, "data", "normalized"), base, ignore=shutil.ignore_patterns("tables", "institutes"))
        insts, courses, rep = I.run(Fake(pages()), 2026, "2026-11-12T00:00:00Z"); I.write(os.path.join(base, "institutes"), insts, courses, rep)
        B.build(base=base, outdir=os.path.join(cls.tmp, "tables")); cls.data = os.path.join(cls.tmp, "data"); PR.main(cls.data, tables=os.path.join(cls.tmp, "tables"))
    @classmethod
    def tearDownClass(cls): shutil.rmtree(cls.tmp)
    def test_engine_filters_by_district(self):
        import subprocess
        r = subprocess.run([NODE, os.path.join(ROOT, "tests", "helpers", "district_check.js")], env=dict(os.environ, DISTRICT_DATA_DIR=self.data), capture_output=True, text=True, cwd=ROOT)
        self.assertEqual(r.returncode, 0, r.stderr[-800:]); out = json.loads(r.stdout)
        self.assertTrue(all(d == "Satara" for d in out["satara"])); self.assertNotIn("District data is not available yet", " ".join(out["warnings"]))
        self.assertGreater(len(out["satara"]), 0); self.assertIn("Satara", out["anyDistricts"]); self.assertGreater(out["anyCount"], len(out["satara"]))      # "any district" still searches every college
    def test_form_offers_the_official_districts(self):
        import subprocess
        j = subprocess.run([NODE, "-e", "require('jsdom')"], capture_output=True, cwd=ROOT)
        if j.returncode: self.skipTest("jsdom not installed")
        r = subprocess.run([NODE, "--test", "--test-name-pattern=official districts", os.path.join(ROOT, "tests", "ui_real.test.js")], env=dict(os.environ, REAL_DATA_DIR=self.data, DISTRICT_DATA_DIR=self.data), capture_output=True, text=True, cwd=ROOT)
        self.assertIn("official districts", r.stdout); self.assertEqual(r.returncode, 0, r.stdout[-1500:])

if __name__ == "__main__": unittest.main()
