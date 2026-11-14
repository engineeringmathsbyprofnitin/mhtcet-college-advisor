"""Stage 10c-3b: the form and results page on real data. The page tests need Node and jsdom (npm install jsdom); without jsdom they are skipped.
Run: python -m unittest tests/test_stage10c3b.py -v"""
import csv, json, os, re, shutil, subprocess, sys, tempfile, unittest
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import realpkg
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
NODE = shutil.which("node")
def has_jsdom():
    return bool(NODE) and subprocess.run([NODE, "-e", "require('jsdom')"], capture_output=True, cwd=ROOT, env=os.environ).returncode == 0

class Css(unittest.TestCase):
    def test_hidden_result_rows_stay_hidden_on_phones(self):
        """Phone layout makes `table.results tbody` a block; the hidden rows (results 6-20) need a rule at least as specific, or all 20 show at once."""
        css = open(os.path.join(ROOT, "frontend", "styles.css"), encoding="utf-8").read()
        self.assertIn("table.results,table.results tbody{display:block", css)
        self.assertIn("table.results tbody[hidden]{display:none}", css)
        self.assertNotRegex(css, r"(?m)^\s*tbody\[hidden\]\{display:none\}")

@unittest.skipUnless(NODE, "node not installed")
class Config(unittest.TestCase):
    def test_home_university_list_equals_the_data(self):
        js = "const w={};new Function('window',require('fs').readFileSync('frontend/config.js','utf8'))(w);console.log(JSON.stringify(w.APP_CONFIG.homeUniversities))"
        cfg = json.loads(subprocess.run([NODE, "-e", js], capture_output=True, text=True, cwd=ROOT, check=True).stdout)
        with open(os.path.join(ROOT, "data", "normalized", "master", "home_universities.csv"), newline="", encoding="utf-8") as f:
            data = [r["home_university"] for r in csv.DictReader(f)]
        self.assertEqual(sorted(cfg), sorted(x for x in data if x not in ("Autonomous Institute", "Deemed to be University")))

@unittest.skipUnless(has_jsdom(), "jsdom not installed (npm install jsdom)")
class Page(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.d = tempfile.mkdtemp(); realpkg.package(cls.d)
    @classmethod
    def tearDownClass(cls): shutil.rmtree(cls.d)
    def test_real_data_page(self):
        r = subprocess.run([NODE, "--test", os.path.join(ROOT, "tests", "ui_real.test.js")], env=dict(os.environ, REAL_DATA_DIR=self.d), capture_output=True, text=True, cwd=ROOT)
        self.assertEqual(r.returncode, 0, r.stdout[-1500:]); self.assertIn("# fail 0", r.stdout); self.assertIn("# skipped 0", r.stdout); self.assertGreaterEqual(int(re.search(r"# pass (\d+)", r.stdout).group(1)), 6)
    def test_synthetic_page_unchanged(self):
        r = subprocess.run([NODE, "--test", os.path.join(ROOT, "tests", "ui_stage6.test.js")], capture_output=True, text=True, cwd=ROOT)
        self.assertEqual(r.returncode, 0, r.stdout[-1500:]); self.assertIn("# pass 21", r.stdout)
if __name__ == "__main__": unittest.main()
