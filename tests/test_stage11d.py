"""Stage 11d: vacancy packaged into the website data and shown by the browser loader + engine (Node). Node tests skip when Node is missing."""
import csv, json, os, shutil, subprocess, sys, tempfile, unittest
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import realpkg
from ingestion import package_real as PR, build_vacancy as BV
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
NODE = shutil.which("node")
MAN = json.load(open(os.path.join(ROOT, "data", "raw", "manifest.json")))["files"]
SHA = next(k for k, v in MAN.items() if v["asset_name"].endswith("FE2026_Vacancy_For_CAP4.pdf"))
DOC = "DOC-" + SHA[:16]
HEAD = ["vacancy_id", "choice_code", "admission_year", "cap_round", "seat_type_code", "vacancy_count", "published_date", "source_doc_id", "retrieved_date", "validation_status", "is_synthetic"]
SHEAD = ["doc_id", "source_name", "source_url", "filename", "sha256", "admission_year", "doc_type", "cap_round", "published_date", "retrieved_date", "validation_status", "is_synthetic"]


def vrow(cc, vac="3", rnd="IV", year="2026-27", doc=DOC):
    return dict(choice_code=cc, admission_year=year, vacancy_round=rnd, vacant_cap_seats=vac, source_doc_id=doc, source_url="https://example.org/v.pdf")


def folder(branch_codes):
    d = tempfile.mkdtemp()
    for n, h in (("vacancies", HEAD), ("source_documents", SHEAD)):
        with open(os.path.join(d, n + ".csv"), "w", newline="", encoding="utf-8") as f: csv.writer(f, lineterminator="\r\n").writerow(h)
    with open(os.path.join(d, "branches.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(["choice_code"]); [w.writerow([c]) for c in branch_codes]
    return d


def tables(rows):
    t = tempfile.mkdtemp()
    if rows is not None:
        with open(os.path.join(t, "vacancy.csv"), "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    return t


def read(d, n):
    with open(os.path.join(d, n + ".csv"), newline="", encoding="utf-8") as f: return list(csv.DictReader(f))


class AddVacancy(unittest.TestCase):
    def test_rows_and_source_document(self):
        d = folder(["0100219110", "0100224210"]); rep = PR.add_vacancy(d, tables([vrow("0100219110", "3"), vrow("0100224210", "0")]))
        self.assertEqual((rep["added"], rep["round"], rep["year"]), (2, "IV", "2026-27"))
        v = read(d, "vacancies"); self.assertEqual([(r["seat_type_code"], r["vacancy_count"], r["cap_round"]) for r in v], [("ALL", "3", "IV"), ("ALL", "0", "IV")])
        s = read(d, "source_documents"); self.assertEqual(len(s), 1); self.assertEqual((s[0]["doc_id"], s[0]["doc_type"], s[0]["cap_round"], s[0]["sha256"]), (DOC, "vacancy_position", "IV", SHA))

    def test_course_not_on_website_is_counted_not_packaged(self):
        d = folder(["0100219110"]); rep = PR.add_vacancy(d, tables([vrow("0100219110"), vrow("0476699510")]))
        self.assertEqual((rep["added"], rep["skipped_not_on_website"]), (1, 1)); self.assertEqual([r["choice_code"] for r in read(d, "vacancies")], ["0100219110"])

    def test_no_vacancy_file_adds_nothing(self):
        d = folder(["0100219110"]); rep = PR.add_vacancy(d, tables(None))
        self.assertEqual(rep["added"], 0); self.assertEqual(read(d, "vacancies"), []); self.assertEqual(read(d, "source_documents"), [])

    def test_mixed_rounds_refused(self):
        with self.assertRaises(SystemExit): PR.add_vacancy(folder(["0100219110", "0100224210"]), tables([vrow("0100219110"), vrow("0100224210", rnd="III")]))

    def test_unknown_source_refused(self):
        with self.assertRaises(SystemExit): PR.add_vacancy(folder(["0100219110"]), tables([vrow("0100219110", doc="DOC-0000000000000000")]))

    def test_zero_is_kept_as_zero_and_values_are_not_changed(self):
        d = folder(["0100219110"]); PR.add_vacancy(d, tables([vrow("0100219110", "0")]))
        self.assertEqual(read(d, "vacancies")[0]["vacancy_count"], "0")


@unittest.skipUnless(NODE, "node not installed")
class RealPipeline(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not os.path.isdir(os.path.join(BV.N, "vacancy")): raise unittest.SkipTest("no committed vacancy tables")
        cls.t = realpkg.fresh_tables(); cls.rep = BV.build(outdir=cls.t)
        if not cls.rep["ok"] or not os.path.exists(os.path.join(cls.t, "vacancy.csv")): raise unittest.SkipTest("no vacancy for the current year: " + cls.rep["status"])
        cls.d = tempfile.mkdtemp(); cls.ver, cls.m = PR.main(cls.d, tables=cls.t)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(getattr(cls, "d", ""), ignore_errors=True); shutil.rmtree(getattr(cls, "t", ""), ignore_errors=True)

    def test_package_has_vacancy_rows(self):
        self.assertGreater(self.m["row_counts"]["vacancies"], 2000)

    def test_browser_loader_and_engine_show_the_table_figures(self):
        env = dict(os.environ, REAL_DATA_DIR=self.d, VACANCY_CSV=os.path.join(self.t, "vacancy.csv"))
        r = subprocess.run([NODE, "--test", os.path.join(ROOT, "tests", "real_vacancy.test.js")], env=env, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout[-1500:] + r.stderr[-500:]); self.assertIn("# pass 2", r.stdout); self.assertIn("# skipped 0", r.stdout)

    def test_older_tests_still_pass_with_vacancy_present(self):
        r = subprocess.run([NODE, "--test", os.path.join(ROOT, "tests", "real_data.test.js")], env=dict(os.environ, REAL_DATA_DIR=self.d), capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout[-1500:] + r.stderr[-500:])

    def test_version_changes_when_vacancy_changes(self):
        t2 = realpkg.fresh_tables()
        try:
            self.assertNotEqual(PR.main(tempfile.mkdtemp(), tables=t2)[0], self.ver)      # no vacancy.csv in t2 -> different data version
        finally: shutil.rmtree(t2, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
