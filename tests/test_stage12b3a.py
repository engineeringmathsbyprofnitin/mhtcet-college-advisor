"""Stage 12b-3a: NBA institutions matched to website colleges (strict; doubtful pairs wait for the owner). Temp folders only - never the real data folders."""
import csv, json, os, shutil, sys, tempfile, unittest
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from ingestion import nba_match as M
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
NCOLS = ["tier", "institution_raw", "institution_name", "place", "program", "level", "status", "period_text", "valid_from", "valid_to", "validity_basis", "source_file", "source_sha256", "downloaded_on"]


def setup(nba_rows, colleges, confirm=()):
    tmp = tempfile.mkdtemp(); base = os.path.join(tmp, "n"); os.makedirs(os.path.join(base, "nba")); os.makedirs(os.path.join(base, "tables"))
    with open(os.path.join(base, "nba", "nba_programs.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=NCOLS); w.writeheader()
        for name, place in nba_rows: w.writerow({**{k: "" for k in NCOLS}, "institution_name": name, "place": place, "program": "Civil Engineering"})
    with open(os.path.join(base, "tables", "colleges.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(["college_code", "college_name", "district", "city"]); w.writerows([list(c) + [""] for c in colleges])
    man = os.path.join(tmp, "confirm.csv")
    with open(man, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(["nba_institution", "nba_place", "decision", "college_code"]); w.writerows(confirm)
    return tmp, base, man


def run(nba_rows, colleges, confirm=()):
    tmp, base, man = setup(nba_rows, colleges, confirm); out = os.path.join(tmp, "out")
    rep = M.build(base=base, manual=man, outdir=out)
    rows = list(csv.DictReader(open(os.path.join(out, "nba_institution_match.csv"), encoding="utf-8")))
    shutil.rmtree(tmp, ignore_errors=True)
    return rep, rows


COLS = [("04025", "Government College of Engineering, Nagpur", "Nagpur"), ("04147", "K.D.K. College of Engineering, Nagpur", "Nagpur"),
        ("06036", "Government College of Engineering, Kolhapur", "Kolhapur"), ("02641", "Dr. V.K. Patil College of Engineering & Technology", "Dharashiv"),
        ("06250", "D.Y. Patil College of Engineering and Technology, Kolhapur", "Kolhapur"), ("03014", "Sardar Patel College of Engineering, Andheri", "Mumbai Suburban"),
        ("06271", "Pune Institute of Computer Technology", "Pune"), ("05999", "Zed Institute of Technology", "Not available")]


class Names(unittest.TestCase):
    def test_initials_are_kept_together(self):
        self.assertEqual(M.norm("D.Y. Patil"), ["dy", "patil"]); self.assertEqual(M.norm("K.D.K. College"), ["kdk", "college"])
        self.assertEqual(M.norm("G H Raisoni"), ["gh", "raisoni"])

    def test_bracket_text_and_entities(self):
        self.assertNotIn("autonomous", M.norm("Government College (An Autonomous Institute of Govt)")); self.assertEqual(M.norm("BHARATI VIDYAPEETH&#39;S"), ["bharati", "vidyapeeth"])

    def test_government_is_a_real_word(self):
        self.assertIn("government", M.toks("Government College of Engineering"))

    def test_place_rules(self):
        col = dict(college_name="X College, Pune", district="Pune", city="")
        self.assertEqual(M.place_state("PUNE", col), "ok"); self.assertEqual(M.place_state("", col), "unknown")
        self.assertEqual(M.place_state("Nagpur", col), "conflict")                     # a known district that differs
        self.assertEqual(M.place_state("Islampur", dict(college_name="Y College", district="Sangli", city="")), "unknown")   # a town cannot be checked
        self.assertEqual(M.place_state("Aurangabad", dict(college_name="Z", district="Chhatrapati Sambhajinagar", city="")), "ok")   # old name


class Matching(unittest.TestCase):
    def test_clear_match_is_linked_and_wrong_college_is_not(self):
        rep, rows = run([("Government College of Engineering, Nagpur", "Nagpur"), ("K.D.K COLLEGE OF ENGINEERING", "Nagpur"), ("D.Y. Patil College of Engineering and Technology", "")], COLS)
        d = {r["nba_institution"]: r for r in rows}
        self.assertEqual(d["Government College of Engineering, Nagpur"]["college_code"], "04025")
        self.assertEqual(d["K.D.K COLLEGE OF ENGINEERING"]["college_code"], "04147")
        self.assertNotEqual(d["D.Y. Patil College of Engineering and Technology"]["college_code"], "02641")   # trap: 'Dr. V.K. Patil' is a different college

    def test_place_conflict_blocks_auto_link(self):
        rep, rows = run([("Government College of Engineering", "KOLHAPUR")], COLS)
        self.assertEqual(rows[0]["college_code"], "06036")                              # Kolhapur place picks the Kolhapur college
        rep, rows = run([("Government College of Engineering", "Nagpur")], [c for c in COLS if c[0] != "04025"])
        self.assertNotEqual(rows[0]["status"], "linked")                                # no Nagpur government college in this list: never fall back to another city

    def test_no_plausible_college(self):
        rep, rows = run([("Amity University Maharashtra", "Raigad")], COLS)
        self.assertEqual(rows[0]["status"], "no_college"); self.assertEqual(rows[0]["college_code"], "")

    def test_doubtful_has_no_college_code_and_is_listed(self):
        rep, rows = run([("Sardar Patel Institute of Engineering", "Mumbai")], COLS)
        for r in rows:
            if r["status"] == "doubtful": self.assertEqual(r["college_code"], "")
        self.assertEqual(rep["counts"].get("linked", 0) + rep["counts"].get("doubtful", 0) + rep["counts"].get("no_college", 0), 1)

    def test_owner_confirmation_yes_and_no(self):
        nba = [("Sardar Patel Institute of Engineering", "Mumbai"), ("Zed Technical Institute", "Pune")]
        rep, rows = run(nba, COLS, confirm=[("Sardar Patel Institute of Engineering", "Mumbai", "yes", "03014"), ("Zed Technical Institute", "Pune", "no", "")])
        d = {r["nba_institution"]: r for r in rows}
        self.assertEqual((d["Sardar Patel Institute of Engineering"]["status"], d["Sardar Patel Institute of Engineering"]["college_code"]), ("linked", "03014"))
        self.assertEqual(d["Zed Technical Institute"]["status"], "no_college")

    def test_confirmation_for_unknown_college_is_a_problem_not_a_link(self):
        rep, rows = run([("Sardar Patel Institute of Engineering", "Mumbai")], COLS, confirm=[("Sardar Patel Institute of Engineering", "Mumbai", "yes", "99999")])
        self.assertFalse(rep["ok"]); self.assertEqual(rows[0]["college_code"], "")

    def test_unused_confirmation_reported(self):
        rep, rows = run([("Pune Institute of Computer Technology", "Pune")], COLS, confirm=[("Gone Institute", "Pune", "no", "")])
        self.assertEqual(rep["unused_confirmations"], [["Gone Institute", "Pune"]])


class RealData(unittest.TestCase):
    """Runs the matcher on the committed real tables, writing only to a temp folder."""
    @classmethod
    def setUpClass(cls):
        cls.src = os.path.join(ROOT, "data", "normalized"); cls.tmp = tempfile.mkdtemp()
        if not os.path.exists(os.path.join(cls.src, "nba", "nba_programs.csv")): raise unittest.SkipTest("no NBA data in this checkout")
        cls.rep = M.build(base=cls.src, manual=os.path.join(cls.tmp, "none.csv"), outdir=cls.tmp)
        cls.rows = list(csv.DictReader(open(os.path.join(cls.tmp, "nba_institution_match.csv"), encoding="utf-8")))

    @classmethod
    def tearDownClass(cls): shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_every_institution_has_exactly_one_row_and_status(self):
        nba = list(csv.DictReader(open(os.path.join(self.src, "nba", "nba_programs.csv"), encoding="utf-8")))
        self.assertEqual(len(self.rows), len({(r["institution_name"], r["place"]) for r in nba}))
        self.assertEqual(sum(self.rep["counts"].values()), len(self.rows)); self.assertTrue(all(r["status"] in ("linked", "doubtful", "no_college") for r in self.rows))

    def test_linked_colleges_exist_and_doubtful_are_not_used(self):
        codes = {c["college_code"] for c in csv.DictReader(open(os.path.join(self.src, "tables", "colleges.csv"), encoding="utf-8"))}
        for r in self.rows:
            if r["status"] == "linked": self.assertIn(r["college_code"], codes)
            else: self.assertEqual(r["college_code"], "")

    def test_known_traps(self):
        def link(prefix):
            return {r["college_code"] for r in self.rows if r["nba_institution"].upper().startswith(prefix.upper()) and r["status"] == "linked"}
        self.assertNotIn("02641", link("D.Y. Patil College of Engineering and Technology"))        # Dr. V.K. Patil (Dharashiv) is a different college
        self.assertEqual(link("Government College of Engineering, Nagpur"), {"04025"})             # not the K.D.K. Nagpur college
        self.assertEqual(link("K.D.K COLLEGE"), {"04147"})
        self.assertEqual(link("Amity University"), set())                                           # a university that is not a CAP college

    def test_two_different_nba_institutions_of_same_name_in_different_places_do_not_share_by_accident(self):
        for r in self.rows:
            if r["status"] == "linked" and r["nba_place"].strip().lower() in M.KNOWN_PLACES:
                col = {c["college_code"]: c for c in csv.DictReader(open(os.path.join(self.src, "tables", "colleges.csv"), encoding="utf-8"))}[r["college_code"]]
                self.assertNotEqual(M.place_state(r["nba_place"], col), "conflict", r["nba_institution"])


class OwnerConfirmations(unittest.TestCase):
    """The committed owner answers must be well-formed: each pair once, yes needs a real college code, and no pair is left doubtful."""
    def test_file_is_valid_and_resolves_every_doubtful_pair(self):
        path = os.path.join(ROOT, "data", "manual", "nba_institution_confirmations.csv")
        if not os.path.exists(path): self.skipTest("no confirmations file yet")
        with open(path, newline="", encoding="utf-8") as f: conf = list(csv.DictReader(f))
        with open(os.path.join(ROOT, "data", "normalized", "tables", "colleges.csv"), newline="", encoding="utf-8") as f: codes = {c["college_code"] for c in csv.DictReader(f)}
        keys = [(r["nba_institution"], r["nba_place"]) for r in conf]
        self.assertEqual(len(keys), len(set(keys)))
        for r in conf:
            self.assertIn(r["decision"], ("yes", "no"))
            if r["decision"] == "yes": self.assertIn(r["college_code"], codes, r["nba_institution"])
            else: self.assertEqual(r["college_code"], "")
        tmp = tempfile.mkdtemp()
        try:
            rep = M.build(base=os.path.join(ROOT, "data", "normalized"), manual=path, outdir=tmp)
        finally: shutil.rmtree(tmp, ignore_errors=True)
        self.assertTrue(rep["ok"], rep["problems"]); self.assertEqual(rep["counts"].get("doubtful", 0), 0); self.assertEqual(rep["unused_confirmations"], [])


if __name__ == "__main__":
    unittest.main()
