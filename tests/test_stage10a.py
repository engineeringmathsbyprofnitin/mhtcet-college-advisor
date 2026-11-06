"""Stage 10a tests: which cutoff cells apply to which Maharashtra-candidature student. Uses the real seat-code table (master) and
hand-made rows. Run: python -m unittest tests/test_stage10a.py -v"""
import csv, gzip, os, sys, unittest
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from ingestion import eligibility as E
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
SC = E.load_seat_codes(os.path.join(ROOT, "data", "normalized", "master", "seat_codes.csv"))
PUNE = "Savitribai Phule Pune University"; MUM = "Mumbai University"

def row(seat, section=E.S_STATE, uni=PUNE, stage="I", pct="90.0", merit="100"):
    return {"year_label": "2026-27", "cap_round": "IV", "choice_code": "0100219110", "section": section, "home_university": uni, "seat_code": seat, "stage": stage, "percentile": pct, "merit_no": merit}
def stu(**k):
    d = {"home_university": PUNE, "gender": "male", "category": "OPEN"}; d.update(k); return d
def ok(r, p): return E.applicable(r, p, SC)[0]

class T(unittest.TestCase):
    def test_every_real_seat_code_is_classified(self):
        for code, info in SC.items():
            self.assertIn(info["family"], ("regular", "ews", "tfws", "pwd", "defence", "phc", "orphan", "minority", "all_india_seat"), code)
    def test_ladies_need_female(self):
        self.assertTrue(ok(row("LOPENS"), stu(gender="female")))
        self.assertFalse(ok(row("LOPENS"), stu(gender="male")))
        self.assertTrue(ok(row("GOPENS"), stu(gender="female")))
    def test_category_matching(self):
        self.assertTrue(ok(row("GOBCS"), stu(category="OBC")))
        self.assertFalse(ok(row("GOBCS"), stu(category="SC")))
        self.assertTrue(ok(row("GOPENS"), stu(category="SC")))   # open seats are open to everyone (assumption flagged in docs)
    def test_home_university_sections(self):
        hu = row("GOPENH", E.S_HU_HU); self.assertTrue(ok(hu, stu())); self.assertFalse(ok(hu, stu(home_university=MUM)))
        ho = row("GOPENH", E.S_HU_OHU); self.assertFalse(ok(ho, stu())); self.assertTrue(ok(ho, stu(home_university=MUM)))
        oo = row("GOPENO", E.S_OHU_OHU); self.assertFalse(ok(oo, stu())); self.assertTrue(ok(oo, stu(home_university=MUM)))
        oh = row("GOPENO", E.S_OHU_HU); self.assertTrue(ok(oh, stu())); self.assertFalse(ok(oh, stu(home_university=MUM)))
    def test_autonomous_has_only_state_level(self):
        self.assertTrue(ok(row("GOPENS", uni=E.AUTONOMOUS), stu()))
        self.assertFalse(ok(row("GOPENH", E.S_HU_HU, uni=E.AUTONOMOUS), stu(home_university=E.AUTONOMOUS)))
    def test_all_india_section_not_for_maharashtra_candidates(self):
        self.assertFalse(ok(row("GOPENS", E.S_AI), stu()))
    def test_special_families_need_flags(self):
        self.assertFalse(ok(row("EWS"), stu())); self.assertTrue(ok(row("EWS"), stu(ews=True)))
        self.assertFalse(ok(row("TFWS"), stu())); self.assertTrue(ok(row("TFWS"), stu(tfws=True)))
        self.assertFalse(ok(row("DEFOPENS"), stu())); self.assertTrue(ok(row("DEFOPENS"), stu(defence=True)))
        self.assertFalse(ok(row("PWDOBCS"), stu(pwd=True, category="SC"))); self.assertTrue(ok(row("PWDOBCS"), stu(pwd=True, category="OBC")))
    def test_undefined_variants_and_minority_are_unknown_not_guessed(self):
        self.assertIsNone(ok(row("DEFROBCS"), stu(defence=True, category="OBC")))
        self.assertIsNone(ok(row("ORPHANI"), stu(orphan=True)))
        self.assertIsNone(ok(row("MI", E.S_MINORITY, stage="MH"), stu()))
    def test_unrecognised_inputs_are_unknown(self):
        self.assertIsNone(ok(row("ZZZ"), stu())); self.assertIsNone(ok(row("GOPENS", "Some new section"), stu()))
    def test_closing_cells_lowest_percentile_and_keeps_all_stages(self):
        c = E.closing_cells([row("GOPENS", stage="I", pct="61.7"), row("GOPENS", stage="VII", pct="81.7"), row("GOPENS", pct="", stage="II")])
        self.assertEqual(len(c), 1); self.assertEqual(c[0]["closing_percentile"], "61.7"); self.assertEqual(c[0]["closing_stage"], "I")
        self.assertEqual(c[0]["all_stages"], {"I": "61.7", "VII": "81.7"})
    def test_real_data_every_section_known_and_every_seat_code_known(self):
        base = os.path.join(ROOT, "data", "normalized", "cutoffs_mh")
        secs, codes = set(), set()
        for fn in os.listdir(base):
            if fn.endswith(".csv.gz"):
                with gzip.open(os.path.join(base, fn), "rt", newline="", encoding="utf-8") as f:
                    for r in csv.DictReader(f): secs.add(r["section"]); codes.add(r["seat_code"])
        self.assertEqual(secs - set(E.KNOWN_SECTIONS), set()); self.assertEqual(codes - set(SC), set())
    def test_real_data_key_is_unique_per_stage(self):
        seen = set(); base = os.path.join(ROOT, "data", "normalized", "cutoffs_mh")
        for fn in os.listdir(base):
            if fn.endswith(".csv.gz"):
                with gzip.open(os.path.join(base, fn), "rt", newline="", encoding="utf-8") as f:
                    for r in csv.DictReader(f):
                        k = (r["year_label"], r["cap_round"], r["choice_code"], r["section"], r["seat_code"], r["stage"])
                        self.assertNotIn(k, seen); seen.add(k)
if __name__ == "__main__": unittest.main()
