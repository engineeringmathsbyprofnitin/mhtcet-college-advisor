"""Stage 12c-3: website colleges matched to NAAC records (strict; doubtful pairs wait for the owner). Temp folders only."""
import csv, json, os, shutil, sys, tempfile, unittest
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from ingestion import naac_match as X
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
SRC = os.path.join(ROOT, "data", "normalized")
NC = ["source_row", "track_id", "aishe_id", "name", "affiliating_university", "address", "locality_hint", "district_hint", "state", "pin", "cycle", "cgpa", "grade", "declared_on", "list_as_on", "source_file", "source_sha256"]
CC = ["college_code", "college_name", "district", "city"]


def put(path, cols, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols); w.writeheader(); [w.writerow({**{k: "" for k in cols}, **r}) for r in rows]


def run(naac, colleges, confirm=()):
    tmp = tempfile.mkdtemp(); base = os.path.join(tmp, "n")
    put(os.path.join(base, "naac", "naac_institutions.csv"), NC, [dict(source_row=i, aishe_id=a, name=n, address=ad, district_hint=dh, grade=g, cgpa="3.0", declared_on="2024-01-01") for i, (a, n, ad, dh, g) in enumerate(naac, 2)])
    put(os.path.join(base, "tables", "colleges.csv"), CC, [dict(college_code=c, college_name=n, district=d) for c, n, d in colleges])
    man = os.path.join(tmp, "c.csv")
    with open(man, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(["college_code", "aishe_id", "decision"]); w.writerows(confirm)
    rep = X.build(base=base, manual=man, outdir=os.path.join(tmp, "o"))
    rows = {r["college_code"]: r for r in csv.DictReader(open(os.path.join(tmp, "o", "naac_college_match.csv"), encoding="utf-8"))}
    shutil.rmtree(tmp, ignore_errors=True); return rep, rows


NAAC = [("C-1", "GOVERNMENT COLLEGE OF ENGINEERING AURANGABAD", "x, Aurangabad, Aurangabad, Maharashtra, 431005", "Aurangabad", "B++"),
        ("C-2", "RIZVI COLLEGE OF EDUCATION", "x, Mumbai, Mumbai, Maharashtra, 400050", "Mumbai", "B+"),
        ("C-3", "RIZVI COLLEGE OF ENGINEERING", "x, Mumbai, Mumbai, Maharashtra, 400050", "Mumbai", "B+"),
        ("C-4", "ABC COLLEGE OF ENGINEERING PUNE", "x, Pune, Pune, Maharashtra, 411001", "Pune", "A")]
COLS = [("02008", "Government College of Engineering, Chhatrapati Sambhajinagar", "Chhatrapati Sambhajinagar"), ("03201", "Rizvi College of Engineering", "Mumbai Suburban"),
        ("06999", "Zed Institute of Technology", "Pune")]


class Helpers(unittest.TestCase):
    def test_old_and_new_place_names_are_the_same_word(self):
        self.assertEqual(X.fix("Government College of Engineering Aurangabad"), "Government College of Engineering chhatrapati sambhajinagar"); self.assertIn("dharashiv", X.fix("Osmanabad"))

    def test_an_engineering_college_is_not_an_education_or_pharmacy_college(self):
        idf = lambda t: 2.0
        self.assertLess(X.name_score("RIZVI COLLEGE OF EDUCATION", "Rizvi College of Engineering", idf), X.name_score("RIZVI COLLEGE OF ENGINEERING", "Rizvi College of Engineering", idf))
        self.assertLess(X.name_score("ABC COLLEGE OF PHARMACY", "ABC College of Engineering", idf), 0.6)

    def test_place_vs_address(self):
        col = dict(district="Pune"); n = dict(address="x, Hinjewadi, Pune, Maharashtra", name="ABC", district_hint="Pune")
        self.assertEqual(X.place_vs_address(col, n), "ok"); self.assertEqual(X.place_vs_address(col, dict(address="x, Nagpur, Nagpur, Maharashtra", name="ABC", district_hint="Nagpur")), "conflict")
        mum = dict(address="x, Andheri, Mumbai, Maharashtra, 400058", name="ABC", district_hint="Mumbai")
        for d in ("Mumbai Suburban", "Mumbai City", "Mumbai"): self.assertEqual(X.place_vs_address(dict(district=d), mum), "ok", d)                 # one place for addresses
        self.assertEqual(X.place_vs_address(dict(district="Thane"), mum), "conflict")
        self.assertEqual(X.place_vs_address(col, dict(address="x, Daund, Maharashtra", name="ABC", district_hint="Daund")), "unknown"); self.assertEqual(X.place_vs_address(dict(district="Not available"), n), "unknown")


class Matching(unittest.TestCase):
    def test_link_no_record_and_the_wrong_kind_of_college(self):
        rep, rows = run(NAAC, COLS)
        self.assertEqual((rows["02008"]["status"], rows["02008"]["aishe_id"]), ("linked", "C-1"))                    # old name Aurangabad = Chhatrapati Sambhajinagar
        self.assertEqual(rows["03201"]["aishe_id"], "C-3")                                                           # engineering, not the education college of the same trust
        self.assertEqual(rows["06999"]["status"], "no_record"); self.assertEqual(rows["06999"]["aishe_id"], "")
        self.assertEqual(rep["counts"], {"linked": 2, "doubtful": 0, "no_record": 1})

    def test_two_colleges_claiming_one_record_are_both_left_to_the_owner(self):
        rep, rows = run([("C-9", "SHREE ABC COLLEGE OF ENGINEERING PUNE", "x, Pune, Pune, Maharashtra", "Pune", "A")], [("06001", "Shree ABC College of Engineering, Pune", "Pune"), ("06002", "Shree ABC College of Engineering, Pune", "Pune")])
        self.assertEqual(rep["counts"]["linked"], 0); self.assertEqual({rows["06001"]["status"], rows["06002"]["status"]}, {"doubtful"}); self.assertTrue(rep["naac_used_twice"]); self.assertTrue(all(r["aishe_id"] == "" for r in rows.values()))

    def test_owner_yes_and_no(self):
        rep, rows = run(NAAC, COLS, confirm=[("06999", "C-4", "yes"), ("02008", "", "no")])
        self.assertEqual((rows["06999"]["status"], rows["06999"]["aishe_id"], rows["06999"]["how"]), ("linked", "C-4", "owner confirmed")); self.assertEqual(rows["02008"]["status"], "no_record")

    def test_confirmation_with_an_unknown_record_is_a_problem_and_unused_ones_are_listed(self):
        rep, rows = run(NAAC, COLS, confirm=[("06999", "C-404", "yes"), ("99999", "", "no")])
        self.assertFalse(rep["ok"] and rows["06999"]["status"] == "linked"); self.assertEqual(rows["06999"]["aishe_id"], ""); self.assertEqual(rep["unused_confirmations"], ["99999"])

    def test_missing_grade_is_never_invented(self):
        rep, rows = run(NAAC, COLS); self.assertEqual(rows["06999"]["naac_grade"], ""); self.assertEqual(rows["02008"]["naac_grade"], "B++")


class RealData(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not os.path.exists(os.path.join(SRC, "naac", "naac_institutions.csv")): raise unittest.SkipTest("no NAAC data in this checkout")
        cls.tmp = tempfile.mkdtemp(); cls.rep = X.build(base=SRC, outdir=cls.tmp)
        cls.rows = {r["college_code"]: r for r in csv.DictReader(open(os.path.join(cls.tmp, "naac_college_match.csv"), encoding="utf-8"))}
        cls.naac = {r["aishe_id"]: r for r in csv.DictReader(open(os.path.join(SRC, "naac", "naac_institutions.csv"), encoding="utf-8"))}

    @classmethod
    def tearDownClass(cls): shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_every_college_is_resolved_and_no_record_is_used_twice(self):
        self.assertTrue(self.rep["ok"], self.rep["problems"]); self.assertEqual(self.rep["counts"]["doubtful"], 0); self.assertEqual(self.rep["unused_confirmations"], [])
        self.assertEqual(len(self.rows), self.rep["colleges"]); ids = [r["aishe_id"] for r in self.rows.values() if r["status"] == "linked"]; self.assertEqual(len(ids), len(set(ids)))

    def test_linked_rows_carry_the_grade_NAAC_printed(self):
        for r in self.rows.values():
            if r["status"] == "linked": n = self.naac[r["aishe_id"]]; self.assertEqual((r["naac_grade"], r["naac_cgpa"], r["declared_on"]), (n["grade"], n["cgpa"], n["declared_on"]))
            else: self.assertEqual((r["aishe_id"], r["naac_grade"]), ("", ""))

    def test_known_traps(self):
        g = lambda c: self.rows[c]["aishe_id"]
        self.assertEqual(g("04116"), "C-18817"); self.assertEqual(g("04142"), "")                                  # two Raisoni Nagpur colleges, one NAAC record
        self.assertEqual(g("06822"), "C-49660"); self.assertEqual(g("06175"), ""); self.assertEqual(g("16354"), "")   # NAAC says "...AND RESEARCH" = Ravet
        self.assertEqual(g("06298"), "C-41988"); self.assertEqual(g("16361"), "")
        self.assertEqual(g("05322"), "C-50940"); self.assertEqual(g("05239"), ""); self.assertEqual(g("06144"), "C-41744"); self.assertEqual(g("06138"), "")
        self.assertEqual(g("03201"), "C-34027"); self.assertEqual(g("02113"), "")                                  # Rizvi engineering (not education); Marathwada IT is another institute
        self.assertEqual(g("01005"), ""); self.assertEqual(g("03033"), "")                                         # universities are not in this college list


if __name__ == "__main__":
    unittest.main()
