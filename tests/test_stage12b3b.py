"""Stage 12b-3b: NBA programs matched to website branches; accreditation table; packaging. Temp folders only."""
import csv, json, os, shutil, sys, tempfile, unittest
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from ingestion import nba_branch_match as B, build_accreditation as A, package_real as PR
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
SRC = os.path.join(ROOT, "data", "normalized")
NCOLS = ["tier", "institution_raw", "institution_name", "place", "program", "level", "status", "period_text", "valid_from", "valid_to", "validity_basis", "source_file", "source_sha256", "downloaded_on"]
ICOLS = ["nba_institution", "nba_place", "nba_rows", "college_code", "college_name", "status", "score", "second_best", "how"]
BCOLS = ["choice_code", "college_code", "branch_code", "branch_name", "branch_group", "valid_from_year", "valid_to_year", "source_doc_id", "retrieved_date", "validation_status", "is_synthetic"]
SHA = "a" * 64


def put(path, cols, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols); w.writeheader(); [w.writerow({**{k: "" for k in cols}, **r}) for r in rows]


def fixture(programs, branches, rules=()):
    tmp = tempfile.mkdtemp(); base = os.path.join(tmp, "n")
    put(os.path.join(base, "nba", "nba_programs.csv"), NCOLS, [dict(institution_name="Inst A", place="Pune", program=p, status=st, valid_to=vt, valid_from="", source_file="f.xlsx", source_sha256=SHA, downloaded_on="2026-11-18") for p, st, vt in programs])
    put(os.path.join(base, "nba_link", "nba_institution_match.csv"), ICOLS, [dict(nba_institution="Inst A", nba_place="Pune", college_code="06001", status="linked")])
    put(os.path.join(base, "tables", "branches.csv"), BCOLS, [dict(choice_code=cc, college_code="06001" if not cc.startswith("9") else "09999", branch_name=n) for cc, n in branches])
    rp = os.path.join(tmp, "rules.csv")
    with open(rp, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(["nba_program", "branch_name", "decision"]); w.writerows(rules)
    return tmp, base, rp


def match(programs, branches, rules=()):
    tmp, base, rp = fixture(programs, branches, rules)
    try:
        rep = B.build(base=base, rules_path=rp); rows = list(csv.DictReader(open(os.path.join(base, "nba_link", "nba_program_match.csv"), encoding="utf-8")))
        return rep, rows, tmp, base
    finally: pass


class Names(unittest.TestCase):
    def test_spelling_only_differences_are_ignored(self):
        self.assertEqual(B.canon("Electronics & Telecommunications Engg."), B.canon("ELECTRONICS AND TELECOMMUNICATION ENGINEERING"))
        self.assertEqual(B.canon("Fibres and Textiles Processing Technology"), B.canon("Fibres and Textile Processing Technology"))
        self.assertEqual(B.canon("Production Engineering (SW)"), B.canon("Production Engineering[Sandwich]"))

    def test_related_is_subset_but_not_equal_and_sandwich_is_separate(self):
        self.assertTrue(B.related(B.canon("Electronics Engineering"), B.canon("Electronics and Telecommunication Engineering")))
        self.assertFalse(B.related(B.canon("Mechanical Engineering"), B.canon("Mechanical Engineering (Sandwich)")))
        self.assertFalse(B.related(B.canon("Civil Engineering"), B.canon("Civil Engineering")))
        self.assertFalse(B.related(B.canon("Textile Engineering"), B.canon("Textile Technology")))


class Matching(unittest.TestCase):
    def tearDown(self):
        shutil.rmtree(getattr(self, "tmp", ""), ignore_errors=True)

    def run_m(self, *a, **k):
        rep, rows, self.tmp, self.base = match(*a, **k); return rep, rows

    def test_exact_unclear_and_no_branch(self):
        rep, rows = self.run_m([("CIVIL ENGINEERING", "accredited", "2028-06-30"), ("Electronics Engineering", "accredited", "2027-06-30"), ("Mining Engineering", "accredited", "2027-06-30")],
                               [("0600119110", "Civil Engg"), ("0600137210", "Electronics and Telecommunication Engineering")])
        d = {r["program"]: r for r in rows}
        self.assertEqual((d["CIVIL ENGINEERING"]["status"], d["CIVIL ENGINEERING"]["choice_codes"]), ("matched", "0600119110"))
        self.assertEqual(d["Electronics Engineering"]["status"], "unclear"); self.assertEqual(d["Electronics Engineering"]["choice_codes"], "")
        self.assertEqual(d["Mining Engineering"]["status"], "no_branch"); self.assertEqual(len(rep["pairs_waiting"]), 1)

    def test_owner_rule_yes_links_and_no_does_not(self):
        pc, bc = B.canon("Electronics Engineering"), B.canon("Electronics and Telecommunication Engineering")
        rep, rows = self.run_m([("Electronics Engineering", "accredited", "2027-06-30")], [("0600137210", "Electronics and Telecommunication Engineering")], rules=[(pc, bc, "yes")])
        self.assertEqual((rows[0]["status"], rows[0]["choice_codes"]), ("matched", "0600137210")); self.assertEqual(rep["pairs_waiting"], [])
        shutil.rmtree(self.tmp, ignore_errors=True)
        rep, rows = self.run_m([("Electronics Engineering", "accredited", "2027-06-30")], [("0600137210", "Electronics and Telecommunication Engineering")], rules=[(pc, bc, "no")])
        self.assertEqual(rows[0]["status"], "no_branch")

    def test_every_choice_code_of_the_branch_gets_the_programme(self):
        rep, rows = self.run_m([("Computer Engineering", "accredited", "2027-06-30")], [("0600124510", "Computer Engineering"), ("0600124530E", "Computer Engineering")])
        self.assertEqual(rows[0]["choice_codes"], "0600124510;0600124530E"); self.assertEqual(len(rep["multi_choice_code"]), 1)

    def test_sandwich_is_not_the_regular_branch(self):
        rep, rows = self.run_m([("MECHANICAL ENGINEERING", "accredited", "2027-06-30")], [("0600125110", "Mechanical Engineering (Sandwich)")])
        self.assertEqual(rows[0]["choice_codes"], "")


class Accreditation(unittest.TestCase):
    def setUp(self): self.tmp = None
    def tearDown(self): shutil.rmtree(self.tmp or "", ignore_errors=True)

    def build(self, programs, branches):
        rep, rows, self.tmp, base = match(programs, branches)
        out = os.path.join(self.tmp, "t"); os.makedirs(out); shutil.copy(os.path.join(base, "tables", "branches.csv"), out)
        r = A.build(base=base, outdir=out, today="2026-11-20")
        return r, list(csv.DictReader(open(os.path.join(out, "accreditation.csv"), encoding="utf-8"))), out

    def test_rows_shape_and_status(self):
        r, rows, out = self.build([("Civil Engineering", "accredited", "2028-06-30"), ("Civil Engineering", "accredited", "2025-06-30"), ("Computer Engineering", "accredited", ""), ("Mechanical Engineering", "unknown", "")],
                                  [("0600119110", "Civil Engineering"), ("0600124510", "Computer Engineering"), ("0600125110", "Mechanical Engineering")])
        self.assertTrue(r["ok"]); self.assertEqual(len(rows), 4); self.assertEqual(len({x["accreditation_id"] for x in rows}), 4)
        for x in rows: self.assertEqual((x["body"], x["scope"], x["grade"], x["validation_status"], x["is_synthetic"]), ("NBA", "program", "", "validated", "FALSE")); self.assertTrue(x["source_doc_id"].startswith("DOC-"))
        d = {(x["choice_code"], x["valid_to"]): x for x in rows}
        self.assertEqual(d[("0600124510", "")]["status"], "accredited"); self.assertEqual(r["no_end_date"], 1)          # printed accredited, no end date: the site says 'validity unknown'
        self.assertEqual(d[("0600125110", "")]["status"], "unknown"); self.assertEqual(r["expired_on_build_date"], 1)
        srcs = list(csv.DictReader(open(os.path.join(out, "accreditation_sources.csv"), encoding="utf-8")))
        self.assertEqual([s["sha256"] for s in srcs], [SHA])

    def test_unmatched_programme_writes_nothing(self):
        r, rows, out = self.build([("Mining Engineering", "accredited", "2027-06-30")], [("0600119110", "Civil Engineering")])
        self.assertEqual(rows, [])


class RealData(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not os.path.exists(os.path.join(SRC, "nba_link", "nba_institution_match.csv")): raise unittest.SkipTest("no NBA link data in this checkout")
        cls.tmp = tempfile.mkdtemp(); cls.link = os.path.join(cls.tmp, "nba_link")
        cls.rep = B.build(base=SRC, outdir=cls.link)
        cls.rows = list(csv.DictReader(open(os.path.join(cls.link, "nba_program_match.csv"), encoding="utf-8")))

    @classmethod
    def tearDownClass(cls): shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_owner_rules_resolve_every_pair(self):
        self.assertTrue(self.rep["ok"], self.rep["problems"]); self.assertEqual(self.rep["pairs_waiting"], []); self.assertEqual(self.rep["unused_rules"], [])
        self.assertEqual(sum(self.rep["counts"].values()), len(self.rows)); self.assertEqual(set(self.rep["counts"]), {"matched", "no_branch"})

    def test_matched_choice_codes_belong_to_the_same_college(self):
        br = {b["choice_code"]: b for b in csv.DictReader(open(os.path.join(SRC, "tables", "branches.csv"), encoding="utf-8"))}
        for r in self.rows:
            if r["status"] == "matched":
                self.assertTrue(r["choice_codes"]); [self.assertEqual(br[c]["college_code"], r["college_code"]) for c in r["choice_codes"].split(";")]
            else: self.assertEqual(r["choice_codes"], "")

    def test_committed_accreditation_table_is_consistent(self):
        path = os.path.join(SRC, "tables", "accreditation.csv")
        if not os.path.exists(path): self.skipTest("accreditation.csv not built yet")
        rows = list(csv.DictReader(open(path, encoding="utf-8"))); br = {b["choice_code"]: b for b in csv.DictReader(open(os.path.join(SRC, "tables", "branches.csv"), encoding="utf-8"))}
        docs = {s["source_doc_id"] for s in csv.DictReader(open(os.path.join(SRC, "tables", "accreditation_sources.csv"), encoding="utf-8"))}
        self.assertEqual(len({r["accreditation_id"] for r in rows}), len(rows)); self.assertGreater(len([r for r in rows if r["body"] == "NBA"]), 1000)
        for r in rows:
            if r["body"] == "NBA": self.assertEqual(br[r["choice_code"]]["college_code"], r["college_code"])
            self.assertIn(r["source_doc_id"], docs); self.assertIn(r["status"], ("accredited", "unknown"))
        with tempfile.TemporaryDirectory() as t:                                           # rebuilt from the committed match data it must equal the committed file
            A.build(base=SRC, outdir=t, today="2026-11-20")
            self.assertEqual(open(os.path.join(t, "accreditation.csv"), "rb").read(), open(path, "rb").read())

    def test_packaging_adds_rows_and_source_documents(self):
        path = os.path.join(SRC, "tables", "accreditation.csv")
        if not os.path.exists(path): self.skipTest("accreditation.csv not built yet")
        with tempfile.TemporaryDirectory() as t:
            for f in os.listdir(PR.TEMPLATES): shutil.copy(os.path.join(PR.TEMPLATES, f), os.path.join(t, f))
            for n in ("branches", "colleges", "source_documents"): shutil.copy(os.path.join(SRC, "tables", n + ".csv"), os.path.join(t, n + ".csv"))
            rep = PR.add_accreditation(t, os.path.join(SRC, "tables"))
            n = len(list(csv.DictReader(open(path, encoding="utf-8")))); self.assertEqual(rep["added"], n); self.assertEqual(rep["skipped_not_on_website"], 0)
            sd = [r for r in csv.DictReader(open(os.path.join(t, "source_documents.csv"), encoding="utf-8")) if r["doc_type"] == "accreditation_list"]
            self.assertEqual(len(sd), 3); self.assertTrue(all(len(r["sha256"]) == 64 for r in sd))               # two NBA files + the NAAC list


if __name__ == "__main__":
    unittest.main()
