"""Stage 10c-3a: real data packaged for the website, run through the browser loader + engine (Node), and cross-checked against the
independent Python eligibility rules (ingestion/eligibility.py). Skipped automatically when Node is not installed.
Run: python -m unittest tests/test_stage10c3a.py -v"""
import csv, gzip, json, os, shutil, subprocess, sys, tempfile, unittest
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from ingestion import package_real as PR, eligibility as E
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
NODE = shutil.which("node")

@unittest.skipUnless(NODE, "node not installed")
class T(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.d = tempfile.mkdtemp(); cls.ver, cls.m = PR.main(cls.d)
    @classmethod
    def tearDownClass(cls): shutil.rmtree(cls.d)
    def test_package_is_valid_small_and_real(self):
        self.assertTrue(self.m["is_synthetic"] is False); self.assertTrue(self.ver.startswith("REAL-2026-27-RIV-"))
        self.assertGreater(len(self.m["cutoffs"]), 90)
        self.assertLess(self.m["base"]["bytes"] + sum(c["bytes"] for c in self.m["cutoffs"].values()), 9_000_000)
        self.assertEqual(self.m["row_counts"]["current_cutoffs"] + self.m["row_counts"]["historical_cutoffs"], 104225 + 42602)
    def test_dictionary_encoding_roundtrips(self):
        f = next(iter(self.m["cutoffs"].values()))["file"]; t = json.load(open(os.path.join(self.d, f)))["current_cutoffs"]
        self.assertIn("dict", t); self.assertIn("section", t["dict"])
        cols = t["columns"]; r = t["rows"][0]; self.assertIsInstance(r[cols.index("section")], int)
    def test_browser_loader_and_engine_on_real_data(self):
        r = subprocess.run([NODE, "--test", os.path.join(ROOT, "tests", "real_data.test.js")], env=dict(os.environ, REAL_DATA_DIR=self.d), capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout[-1500:] + r.stderr[-500:]); self.assertIn("# pass 10", r.stdout); self.assertIn("# skipped 0", r.stdout)
    def test_engine_agrees_with_python_rules_for_two_students(self):
        out = os.path.join(self.d, "dump.json")
        r = subprocess.run([NODE, os.path.join(ROOT, "tests", "helpers", "dump_real.js")], env=dict(os.environ, REAL_DATA_DIR=self.d, DUMP_OUT=out), capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr[-800:])
        dump = json.load(open(out)); sc = E.load_seat_codes(os.path.join(ROOT, "data", "normalized", "master", "seat_codes.csv"))
        by = {}
        with gzip.open(os.path.join(ROOT, "data", "normalized", "tables", "current_cutoffs.csv.gz"), "rt", newline="", encoding="utf-8") as f:
            for x in csv.DictReader(f): by.setdefault((x["choice_code"], x["cap_round"]), []).append(x)
        HU4 = {E.S_HU_HU, E.S_HU_OHU, E.S_OHU_HU, E.S_OHU_OHU}; compared = exact = 0
        for v in dump.values():
            p = {"home_university": v["student"]["homeUniversity"], "gender": v["student"]["gender"].lower(), "category": v["student"]["category"]}
            for x in v["res"]:
                for rd in ("I", "II", "III", "IV"):
                    vals, unk = [], False
                    for c in by.get((x["cc"], rd), []):
                        if c["home_university_basis"] == "unknown" and c["section"] in HU4: unk = True; continue
                        if E.applicable({"section": c["section"], "home_university": c["home_university"], "seat_code": c["seat_type_code"]}, p, sc)[0] is True: vals.append(float(c["cutoff_percentile"]))
                    if unk: continue
                    expected = min(vals) if vals else None; got = x["rounds"][rd]; compared += 1
                    if got is None or expected is None: self.assertEqual((got is None), (expected is None), (x["cc"], rd))
                    else: self.assertAlmostEqual(got["value"], expected, places=6); exact += 1
        self.assertGreater(exact, 1000)
if __name__ == "__main__": unittest.main()
