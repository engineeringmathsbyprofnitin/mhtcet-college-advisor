"""Stage 10c-3e: "Download PDF" - a real PDF made in the browser (frontend/pdfexport.js), checked with poppler's pdfinfo/pdftotext and by reading the
PDF's own structure. Skipped when node or poppler is missing. Run: python -m unittest tests/test_stage10c3e.py -v"""
import json, os, re, shutil, subprocess, sys, tempfile, unittest
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
NODE, PDFINFO, PDFTOTEXT = shutil.which("node"), shutil.which("pdfinfo"), shutil.which("pdftotext")

def node(js):
    return subprocess.run([NODE, "-e", js], capture_output=True, text=True, cwd=ROOT, check=True).stdout

class LastUpdate(unittest.TestCase):
    def test_header_never_says_unknown_when_the_data_version_has_a_time(self):
        """Owner saw 'last updated unknown': a package without a refresh-status row. The exporter now falls back to the data version's creation time."""
        from ingestion import package_real as PR
        import realpkg
        sys.path.insert(0, os.path.join(ROOT, "database")); import export_static as X
        d = tempfile.mkdtemp(); t = realpkg.fresh_tables()
        try:
            PR.assemble(d, tables=t)
            hdr = open(os.path.join(d, "refresh_status.csv"), encoding="utf-8").readline(); open(os.path.join(d, "refresh_status.csv"), "w", encoding="utf-8").write(hdr)
            m = X.publish(d, os.path.join(d, "out"), now="1970-01-01T00:00:00Z")
            self.assertRegex(m["last_successful_update"], r"^20\d\d-\d\d-\d\dT")
        finally: shutil.rmtree(d); shutil.rmtree(t, ignore_errors=True)

@unittest.skipUnless(NODE, "node not installed")
class Text(unittest.TestCase):
    def test_clean_and_wrap(self):
        out = json.loads(node("const P=require('./frontend/pdfexport.js');console.log(JSON.stringify({a:P.clean('Pune \\u2013 \\u20B9 5 \\u2019 caf\\u00E9 \\u0928\\u092E'),b:P.wrap('word '.repeat(60),8,false,200).length,c:P.wrap('x'.repeat(300),8,false,100).length}))"))
        self.assertEqual(out["a"], "Pune - Rs  5 ' caf\u00E9 ??")                     # non-Latin text becomes '?', never disappears silently
        self.assertGreater(out["b"], 3); self.assertGreater(out["c"], 2)                # long text and long words wrap
    def test_pdf_special_characters_are_escaped(self):
        pdf = node("const P=require('./frontend/pdfexport.js');const b=P.buildPdf({meta:{},results:[{rank:1,collegeName:'A (B) \\\\ C',collegeCode:'1',branchName:'X',branchCode:'2',suitability:'s',score:1,explanation:[]}]});console.log(Buffer.from(b).toString('latin1'))")
        self.assertIn("A \\(B\\) \\\\ C", pdf)

@unittest.skipUnless(NODE and PDFINFO and PDFTOTEXT, "node or poppler not installed")
class RealPdf(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import realpkg
        cls.d = tempfile.mkdtemp(); realpkg.package(os.path.join(cls.d, "data")); cls.out = os.path.join(cls.d, "out"); os.makedirs(cls.out)
        subprocess.run([NODE, os.path.join(ROOT, "tests", "helpers", "make_pdf.js")], env=dict(os.environ, REAL_DATA_DIR=os.path.join(cls.d, "data"), OUT_DIR=cls.out), check=True, capture_output=True)
        cls.pdf = os.path.join(cls.out, "real.pdf"); cls.meta = json.load(open(os.path.join(cls.out, "real.json")))
    @classmethod
    def tearDownClass(cls): shutil.rmtree(cls.d)
    def test_it_is_a_valid_pdf(self):
        info = subprocess.run([PDFINFO, self.pdf], capture_output=True, text=True); self.assertEqual(info.returncode, 0, info.stderr)
        self.assertRegex(info.stdout, r"Pages:\s+[2-9]"); self.assertIn("A4", info.stdout); self.assertEqual(info.stderr.strip(), "")
        raw = open(self.pdf, "rb").read().decode("latin-1")
        start = int(re.search(r"startxref\n(\d+)\n%%EOF", raw).group(1)); self.assertTrue(raw[start:].startswith("xref"))
        for m in re.finditer(r"(\d{10}) 00000 n", raw): self.assertRegex(raw[int(m.group(1)):], r"^\d+ 0 obj")     # every xref offset points to an object
    def test_text_content(self):
        txt = subprocess.run([PDFTOTEXT, "-layout", self.pdf, "-"], capture_output=True, text=True).stdout
        for must in ("MHT-CET College Advisor", "Data version REAL-2026-27-RIV-", "not a prediction or a guarantee", "Vacancy data unavailable", "Past cutoffs", "Page 1 of"):
            self.assertIn(must, txt)
        self.assertRegex(txt, r"last successful data update: 20\d\d-\d\d-\d\d")
        self.assertEqual(len(re.findall(r"(?:^|\f)#\d+ ", txt, re.M)), self.meta["n"])                    # every result is in the PDF
    def test_no_text_runs_off_the_page(self):
        bbox = subprocess.run([PDFTOTEXT, "-bbox", self.pdf, "-"], capture_output=True, text=True).stdout
        for m in re.finditer(r'xMax="([\d.]+)"', bbox): self.assertLessEqual(float(m.group(1)), 595.28 - 30)
if __name__ == "__main__": unittest.main()
