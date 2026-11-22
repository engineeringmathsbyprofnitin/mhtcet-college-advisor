"""Stage 12c-4: NAAC rows in the accreditation table and in the website data. Temp folders only."""
import csv, json, os, shutil, sys, tempfile, unittest
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from ingestion import build_accreditation as A, package_real as PR
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
SRC = os.path.join(ROOT, "data", "normalized")
SHA = "b" * 64


def put(path, cols, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols); w.writeheader(); [w.writerow({**{k: "" for k in cols}, **r}) for r in rows]


def fixture(status="linked"):
    tmp = tempfile.mkdtemp(); base = os.path.join(tmp, "n")
    put(os.path.join(base, "tables", "colleges.csv"), ["college_code", "college_name", "district"], [dict(college_code="06001", college_name="A College", district="Pune"), dict(college_code="06002", college_name="B College", district="Pune")])
    put(os.path.join(base, "tables", "branches.csv"), ["choice_code", "college_code", "branch_code", "branch_name"], [dict(choice_code="0600119110", college_code="06001", branch_code="19110", branch_name="Civil Engineering")])
    put(os.path.join(base, "nba_link", "nba_program_match.csv"), ["nba_institution", "nba_place", "college_code", "program", "status", "choice_codes", "how", "valid_from", "valid_to", "validity_basis", "nba_status", "source_file", "source_sha256", "downloaded_on"], [])
    put(os.path.join(base, "naac", "naac_institutions.csv"), ["aishe_id", "name", "grade", "cgpa", "declared_on", "list_as_on", "source_file", "source_sha256"],
        [dict(aishe_id="C-1", name="A COLLEGE", grade="B++", cgpa="2.85", declared_on="2024-07-19", list_as_on="2025-08-14", source_file="naac.xlsx", source_sha256=SHA)])
    put(os.path.join(base, "naac_link", "naac_college_match.csv"), ["college_code", "college_name", "district", "aishe_id", "naac_name", "naac_grade", "naac_cgpa", "declared_on", "status"],
        [dict(college_code="06001", aishe_id="C-1", status=status), dict(college_code="06002", status="no_record")])
    return tmp, base


class Build(unittest.TestCase):
    def test_naac_row_is_exactly_what_naac_printed_with_no_end_date(self):
        tmp, base = fixture(); out = os.path.join(tmp, "t"); os.makedirs(out); shutil.copy(os.path.join(base, "tables", "branches.csv"), out)
        try:
            rep = A.build(base=base, outdir=out, today="2026-11-21"); rows = list(csv.DictReader(open(os.path.join(out, "accreditation.csv"), encoding="utf-8")))
            self.assertTrue(rep["ok"], rep["problems"]); self.assertEqual((rep["naac_rows"], rep["nba_rows"]), (1, 0)); x = rows[0]
            self.assertEqual((x["accreditation_id"], x["college_code"], x["choice_code"], x["body"], x["scope"], x["status"]), ("NAAC-06001-1", "06001", "", "NAAC", "institution", "accredited"))
            self.assertEqual((x["grade"], x["cgpa"], x["valid_from"], x["valid_to"], x["listed_as_on"]), ("B++", "2.85", "2024-07-19", "", "2025-08-14"))     # no end date invented
            srcs = list(csv.DictReader(open(os.path.join(out, "accreditation_sources.csv"), encoding="utf-8")))
            self.assertEqual((srcs[0]["body"], srcs[0]["published_date"], srcs[0]["source_url"]), ("NAAC", "2025-08-14", "https://www.naac.gov.in/")); self.assertEqual(srcs[0]["source_doc_id"], "DOC-" + SHA[:16])
        finally: shutil.rmtree(tmp, ignore_errors=True)

    def test_only_linked_colleges_get_a_row_and_a_missing_naac_link_folder_is_fine(self):
        tmp, base = fixture(status="doubtful"); out = os.path.join(tmp, "t"); os.makedirs(out); shutil.copy(os.path.join(base, "tables", "branches.csv"), out)
        try:
            self.assertEqual(A.build(base=base, outdir=out)["naac_rows"], 0); shutil.rmtree(os.path.join(base, "naac_link")); rep = A.build(base=base, outdir=out); self.assertTrue(rep["ok"]); self.assertEqual(rep["rows"], 0)
        finally: shutil.rmtree(tmp, ignore_errors=True)

    def test_a_record_missing_from_the_naac_file_is_a_problem(self):
        tmp, base = fixture(); put(os.path.join(base, "naac", "naac_institutions.csv"), ["aishe_id", "name", "grade", "cgpa", "declared_on", "list_as_on", "source_file", "source_sha256"], []); out = os.path.join(tmp, "t"); os.makedirs(out)
        try: rep = A.build(base=base, outdir=out); self.assertFalse(rep["ok"]); self.assertTrue(any("C-1" in p for p in rep["problems"]))
        finally: shutil.rmtree(tmp, ignore_errors=True)


class TransitionRows(unittest.TestCase):
    def test_transition_row_has_a_date_and_no_grade(self):
        tmp, base = fixture(status="no_record")
        put(os.path.join(base, "naac", "naac_transition.csv"), ["source_row", "sl_no", "name", "text", "state", "extended_until", "list_as_on", "source_file", "source_sha256"],
            [dict(source_row="5", name="B COLLEGE", extended_until="2026-12-31", list_as_on="2025-08-14", source_file="naac.xlsx", source_sha256=SHA)])
        put(os.path.join(base, "naac_link", "naac_transition_match.csv"), ["college_code", "source_row", "status"], [dict(college_code="06002", source_row="5", status="linked"), dict(college_code="06001", status="no_record")])
        out = os.path.join(tmp, "t"); os.makedirs(out); shutil.copy(os.path.join(base, "tables", "branches.csv"), out)
        try:
            rep = A.build(base=base, outdir=out); rows = list(csv.DictReader(open(os.path.join(out, "accreditation.csv"), encoding="utf-8")))
            self.assertTrue(rep["ok"], rep["problems"]); self.assertEqual((rep["naac_rows"], rep["naac_transition_rows"]), (0, 1)); x = rows[0]
            self.assertEqual((x["college_code"], x["body"], x["scope"], x["grade"], x["cgpa"], x["valid_from"], x["valid_to"], x["listed_as_on"]), ("06002", "NAAC", "institution", "", "", "", "2026-12-31", "2025-08-14"))
        finally: shutil.rmtree(tmp, ignore_errors=True)

    def test_a_college_cannot_have_a_graded_and_a_transition_row(self):
        tmp, base = fixture()
        put(os.path.join(base, "naac", "naac_transition.csv"), ["source_row", "sl_no", "name", "text", "state", "extended_until", "list_as_on", "source_file", "source_sha256"],
            [dict(source_row="5", name="A COLLEGE", extended_until="2026-12-31", list_as_on="2025-08-14", source_file="naac.xlsx", source_sha256=SHA)])
        put(os.path.join(base, "naac_link", "naac_transition_match.csv"), ["college_code", "source_row", "status"], [dict(college_code="06001", source_row="5", status="linked")])
        out = os.path.join(tmp, "t"); os.makedirs(out)
        try: rep = A.build(base=base, outdir=out); self.assertFalse(rep["ok"]); self.assertTrue(any("graded NAAC record and a transition row" in p for p in rep["problems"]))
        finally: shutil.rmtree(tmp, ignore_errors=True)


class Real(unittest.TestCase):
    def setUp(self):
        if not os.path.exists(os.path.join(SRC, "naac_link", "naac_college_match.csv")): self.skipTest("no NAAC link data")
        self.rows = list(csv.DictReader(open(os.path.join(SRC, "tables", "accreditation.csv"), encoding="utf-8")))

    def test_committed_table_has_one_naac_row_per_linked_college(self):
        naac = [r for r in self.rows if r["body"] == "NAAC" and r["grade"]]; linked = [r for r in csv.DictReader(open(os.path.join(SRC, "naac_link", "naac_college_match.csv"), encoding="utf-8")) if r["status"] == "linked"]
        self.assertEqual(len(naac), len(linked)); self.assertEqual({r["college_code"] for r in naac}, {r["college_code"] for r in linked})
        for r in naac: self.assertEqual((r["scope"], r["choice_code"], r["valid_to"], r["listed_as_on"], r["status"]), ("institution", "", "", "2025-08-14", "accredited")); self.assertRegex(r["valid_from"], r"^\d{4}-\d{2}-\d{2}$"); self.assertIn(r["grade"], ("A++", "A+", "A", "B++", "B+", "B", "C"))
        self.assertTrue(all(r["cgpa"] == "" for r in self.rows if r["body"] == "NBA")); self.assertEqual(len({r["accreditation_id"] for r in self.rows}), len(self.rows))

    def test_transition_rows_are_dated_without_a_grade_and_never_double_a_graded_college(self):
        tr = [r for r in self.rows if r["body"] == "NAAC" and not r["grade"]]; graded = {r["college_code"] for r in self.rows if r["body"] == "NAAC" and r["grade"]}
        self.assertGreaterEqual(len(tr), 10)
        for r in tr: self.assertEqual((r["cgpa"], r["valid_from"], r["listed_as_on"], r["choice_code"], r["scope"]), ("", "", "2025-08-14", "", "institution")); self.assertRegex(r["valid_to"], r"^\d{4}-\d{2}-\d{2}$"); self.assertNotIn(r["college_code"], graded)
        self.assertIn("03209", {r["college_code"] for r in tr})                                                  # K J Somaiya Institute of Technology

    def test_packaging_carries_naac_rows_and_a_naac_source_document(self):
        with tempfile.TemporaryDirectory() as t:
            for f in os.listdir(PR.TEMPLATES): shutil.copy(os.path.join(PR.TEMPLATES, f), os.path.join(t, f))
            for n in ("branches", "colleges", "source_documents"): shutil.copy(os.path.join(SRC, "tables", n + ".csv"), os.path.join(t, n + ".csv"))
            rep = PR.add_accreditation(t, os.path.join(SRC, "tables")); self.assertEqual(rep["added"], len(self.rows)); self.assertEqual(rep["naac"], len([r for r in self.rows if r["body"] == "NAAC"])); self.assertEqual(rep["skipped_not_on_website"], 0)
            sd = [r for r in csv.DictReader(open(os.path.join(t, "source_documents.csv"), encoding="utf-8")) if "naac" in r["source_url"]]
            self.assertEqual(len(sd), 1); self.assertEqual(sd[0]["published_date"], "2025-08-14"); self.assertEqual(sd[0]["doc_type"], "accreditation_list")
            hdr = next(csv.reader(open(os.path.join(t, "accreditation.csv"), encoding="utf-8"))); self.assertIn("cgpa", hdr); self.assertIn("listed_as_on", hdr)


if __name__ == "__main__":
    unittest.main()
