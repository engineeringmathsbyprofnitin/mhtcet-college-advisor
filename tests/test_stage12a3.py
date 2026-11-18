"""Stage 12a-3: FRA fees linked to website colleges, packaged and shown (Node tests skip when Node is missing)."""
import csv, json, os, shutil, subprocess, sys, tempfile, unittest
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import realpkg
from ingestion import build_fees as B, package_real as PR, fra_fees as FF
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
NODE = shutil.which("node")
PLAN = dict(ok=True, current_year="2026-27")
FCOLS = FF.OUT_COLS


def frow(iid="EN3139", name="VIDYALANKAR INSTITUTE OF TECHNOLOGY, WADALA, MUMBAI.", status="Approved", t="176521", d="26479", tot="203000", eq=None):
    code = iid[2:].zfill(5) if iid.startswith("EN") else ""
    if eq is None: eq = "" if "" in (t, d, tot) else ("TRUE" if int(t) + int(d) == int(tot) else "FALSE")
    return dict(inst_id=iid, cet_institute_code=code, inst_name=name, district="Mumbai-City", stream="ENGG", status=status, meeting_date="2026-06-15", tuition_fee=t, development_fee=d,
                total_fee=tot, total_equals_parts=eq, source_url="u", retrieved_date="2026-11-17")


def setup(rows, colleges=(("03139", "Vidyalankar Institute of Technology, Wadala, Mumbai"),), confirm=()):
    tmp = tempfile.mkdtemp(); base = os.path.join(tmp, "n"); os.makedirs(os.path.join(base, "fees")); os.makedirs(os.path.join(base, "tables"))
    if rows is not None:
        with open(os.path.join(base, "fees", "fra_fees_2026-27_engg.csv"), "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=FCOLS); w.writeheader(); w.writerows(rows)
    with open(os.path.join(base, "tables", "colleges.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(["college_code", "college_name"]); w.writerows(colleges)
    man = os.path.join(tmp, "manual.csv")
    with open(man, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(["inst_id", "cet_institute_code", "confirmed_note"]); w.writerows(confirm)
    return base, man


def go(rows, **kw):
    base, man = setup(rows, **kw); rep = B.build(base=base, plan=PLAN, manual=man)
    p = os.path.join(base, "tables", "fees.csv"); return rep, (list(csv.DictReader(open(p, encoding="utf-8"))) if os.path.exists(p) else None)


class Match(unittest.TestCase):
    def test_verified_college_gets_tuition_and_total(self):
        rep, rows = go([frow()]); self.assertTrue(rep["ok"], rep["problems"])
        self.assertEqual([(r["college_code"], r["fee_type"], r["annual_fee_inr"], r["academic_year"], r["validation_status"]) for r in rows], [("03139", "tuition", "176521", "2026-27", "validated"), ("03139", "total", "203000", "2026-27", "validated")])
        self.assertEqual(rows[0]["source_doc_id"], "DOC-FRA-2026-27-ENGG"); self.assertEqual(rows[0]["choice_code"], "")

    def test_same_code_different_name_is_not_published(self):
        rep, rows = go([frow("EN3139", "COMPLETELY DIFFERENT UNIVERSITY OF ARTS")])
        self.assertFalse(rep["ok"]); self.assertIsNone(rows); self.assertIn("name_unverified", " ".join(rep["tiers"]))

    def test_owner_confirmation_publishes_it(self):
        rep, rows = go([frow("EN3139", "COMPLETELY DIFFERENT UNIVERSITY OF ARTS")], confirm=[("EN3139", "03139", "same college, renamed")])
        self.assertTrue(rep["ok"]); self.assertEqual(len(rows), 2); self.assertIn("published (owner-confirmed name)", rep["tiers"])

    def test_confirmation_for_other_code_does_not_apply(self):
        rep, _ = go([frow("EN3139", "COMPLETELY DIFFERENT UNIVERSITY OF ARTS")], confirm=[("EN3139", "09999", "x")]); self.assertFalse(rep["ok"])

    def test_non_en_code_not_linked(self):
        rep, rows = go([frow(), frow("AR3439", "SOME ARCHITECTURE COLLEGE")]); self.assertEqual(len(rows), 2); self.assertEqual(rep["tiers"]["no_cet_code (not an EN code)"], 1)

    def test_college_not_on_website(self):
        rep, rows = go([frow(), frow("EN9999", "OTHER COLLEGE")]); self.assertEqual(rep["tiers"]["college_not_on_website"], 1); self.assertEqual({r["college_code"] for r in rows}, {"03139"})

    def test_interim_order_withheld(self):
        rep, rows = go([frow(), frow("EN3139", status="Interim Order of High Court")]); self.assertFalse(rep["ok"]) if rows is None else None
        rep2, rows2 = go([frow(status="Interim Order of High Court")]); self.assertFalse(rep2["ok"]); self.assertIn("interim_order (fee not final)", rep2["tiers"])

    def test_zero_tuition_with_total_publishes_total_only(self):
        rep, rows = go([frow(t="0", d="0", tot="136000")]); self.assertEqual([(r["fee_type"], r["annual_fee_inr"]) for r in rows], [("total", "136000")]); self.assertTrue(any("tuition not published" in n for n in rep["notes"]))

    def test_total_different_from_parts_keeps_total_drops_tuition(self):
        rep, rows = go([frow(t="100000", d="20000", tot="150000")]); self.assertEqual([r["fee_type"] for r in rows], ["total"])

    def test_blank_numbers_never_become_zero(self):
        rep, rows = go([frow(t="", d="", tot="203000")]); self.assertEqual([(r["fee_type"], r["annual_fee_inr"]) for r in rows], [("total", "203000")])
        rep2, rows2 = go([frow(t="", d="", tot="")]); self.assertFalse(rep2["ok"]); self.assertIsNone(rows2)

    def test_no_fee_file_means_unavailable_and_old_file_removed(self):
        base, man = setup(None); open(os.path.join(base, "tables", "fees.csv"), "w").write("old")
        rep = B.build(base=base, plan=PLAN, manual=man); self.assertTrue(rep["ok"]); self.assertIn("unavailable", rep["status"]); self.assertFalse(os.path.exists(os.path.join(base, "tables", "fees.csv")))

    def test_name_score(self):
        self.assertGreaterEqual(B.name_score("TRIMURTI INSTITUTE OF TECHNOLOGY", "Trimurti Shikshan Prasarak Mandal, Trimurti Institute Of Technology, Jalna"), 0.5)
        self.assertLess(B.name_score("ABC COLLEGE OF ENGINEERING", "Xyz Institute Of Pharmacy"), 0.5)


class Real(unittest.TestCase):
    def test_real_table_is_consistent(self):
        n = B.N
        if not os.path.exists(os.path.join(n, "fees", "fra_fees_2026-27_engg.csv")) or not os.path.exists(os.path.join(n, "data_plan.json")): self.skipTest("no committed fee data")
        t = realpkg.fresh_tables(); rep = B.build(outdir=t)
        try:
            self.assertTrue(rep["ok"], rep["problems"]); self.assertGreater(rep["published_colleges"], 250)
            rows = list(csv.DictReader(open(os.path.join(t, "fees.csv"), encoding="utf-8")))
            self.assertTrue(all(int(r["annual_fee_inr"]) > 0 for r in rows)); self.assertEqual({r["fee_type"] for r in rows}, {"tuition", "total"})
            by = {}; [by.setdefault(r["college_code"], {}).__setitem__(r["fee_type"], int(r["annual_fee_inr"])) for r in rows]
            self.assertTrue(all(v["total"] >= v.get("tuition", 0) for v in by.values()))
        finally: shutil.rmtree(t, ignore_errors=True)


class Confirmations(unittest.TestCase):
    def test_committed_confirmation_file_is_well_formed(self):
        rows = B.load(B.MANUAL); seen = set()
        for r in rows:
            self.assertRegex(r["inst_id"], r"^EN\d{4,5}$"); self.assertEqual(r["cet_institute_code"], r["inst_id"][2:].zfill(5))
            self.assertTrue(r["confirmed_note"].strip()); self.assertNotIn(r["inst_id"], seen); seen.add(r["inst_id"])


class AddFees(unittest.TestCase):
    def test_package_adds_rows_and_source_document(self):
        d = tempfile.mkdtemp(); t = tempfile.mkdtemp()
        for n, h in (("fees", ["fee_id", "college_code", "choice_code", "academic_year", "fee_type", "annual_fee_inr", "fee_scope", "source_doc_id", "retrieved_date", "validation_status", "is_synthetic"]),
                     ("source_documents", ["doc_id", "source_name", "source_url", "filename", "sha256", "admission_year", "doc_type", "cap_round", "published_date", "retrieved_date", "validation_status", "is_synthetic"])):
            open(os.path.join(d, n + ".csv"), "w", newline="").write(",".join(h) + "\r\n")
        open(os.path.join(d, "colleges.csv"), "w", newline="").write("college_code,college_name\r\n03139,X\r\n")
        base, man = setup([frow(), frow("EN9999", "OTHER")]); B.build(base=base, plan=PLAN, manual=man)
        rep = PR.add_fees(d, os.path.join(base, "tables"))
        self.assertEqual(rep["added"], 2)
        s = list(csv.DictReader(open(os.path.join(d, "source_documents.csv"), encoding="utf-8")))
        self.assertEqual((s[0]["doc_id"], s[0]["doc_type"], s[0]["source_url"]), ("DOC-FRA-2026-27-ENGG", "fee_notice", FF.FRA_SITES["2026-27"] + "outer.php?q=fee_search_report")); self.assertEqual(len(s[0]["sha256"]), 64)

    def test_no_fees_file_adds_nothing(self):
        self.assertEqual(PR.add_fees(tempfile.mkdtemp(), tempfile.mkdtemp())["added"], 0)


@unittest.skipUnless(NODE, "node not installed")
class RealPipeline(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        n = B.N
        if not os.path.exists(os.path.join(n, "fees", "fra_fees_2026-27_engg.csv")): raise unittest.SkipTest("no committed fee data")
        cls.t = realpkg.fresh_tables(); rep = B.build(outdir=cls.t)
        if not rep["ok"] or not os.path.exists(os.path.join(cls.t, "fees.csv")): raise unittest.SkipTest(rep["status"])
        cls.d = tempfile.mkdtemp(); cls.ver, cls.m = PR.main(cls.d, tables=cls.t)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(getattr(cls, "d", ""), ignore_errors=True); shutil.rmtree(getattr(cls, "t", ""), ignore_errors=True)

    def test_package_has_fee_rows(self): self.assertGreater(self.m["row_counts"]["fees"], 500)

    def test_browser_loader_and_engine_show_the_table_fees(self):
        env = dict(os.environ, REAL_DATA_DIR=self.d, FEES_CSV=os.path.join(self.t, "fees.csv"))
        r = subprocess.run([NODE, "--test", os.path.join(ROOT, "tests", "real_fees.test.js")], env=env, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout[-2000:] + r.stderr[-500:]); self.assertIn("# pass 4", r.stdout); self.assertIn("# skipped 0", r.stdout)

    def test_older_real_tests_still_pass(self):
        for f in ("real_data.test.js", "real_vacancy.test.js"):
            env = dict(os.environ, REAL_DATA_DIR=self.d, VACANCY_CSV=os.path.join(self.t, "vacancy.csv"))
            if f == "real_vacancy.test.js" and not os.path.exists(env["VACANCY_CSV"]): continue
            r = subprocess.run([NODE, "--test", os.path.join(ROOT, "tests", f)], env=env, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, f + r.stdout[-1500:])


if __name__ == "__main__":
    unittest.main()
