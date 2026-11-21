"""Stage 12c-2: NAAC list reader (owner-downloaded Excel). Temp folders only."""
import csv, json, os, shutil, sys, tempfile, unittest
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from openpyxl import Workbook
from ingestion import naac_import as I
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
HEAD = ["Sl No", "HEI Name", "Track-Id", "Aishe-Id", "Affiliating University", "Address", "Current Cycle Number", "Current CGPA", "Current Grade", "Date Of Declaration"]


def mk(rows, name="Institutions_accredited_by_NAAC_having_valid_accreditation-as_on_14082025_1.xlsx", sheet="Colleges", head=HEAD):
    tmp = tempfile.mkdtemp(); src = os.path.join(tmp, "src"); os.makedirs(src)
    wb = Workbook(); ws = wb.active; ws.title = sheet; ws.append(head)
    for r in rows: ws.append(r)
    wb.create_sheet("Transition Autonomous Colleges").append(["Sl. No.", "HEI Name", "State", "Extended validity upto"])
    wb.save(os.path.join(src, name)); return tmp, src


def run(rows, **k):
    tmp, src = mk(rows, **k); out = os.path.join(tmp, "out")
    rep = I.build(src=src, out=out); data = list(csv.DictReader(open(os.path.join(out, "naac_institutions.csv"), encoding="utf-8")))
    shutil.rmtree(tmp, ignore_errors=True); return rep, data


def row(i=1, name="A COLLEGE OF ENGINEERING", aishe="C-1", univ="Savitribai Phule Pune University", addr="Plot 1,\n Road,Hinjewadi,Pune,Maharashtra,411057", cyc=2, cgpa=3.05, grade="A", dec="19-07-2024"):
    return [i, name, "MHCOGN%d" % i, aishe, univ, addr, cyc, cgpa, grade, dec]


class Helpers(unittest.TestCase):
    def test_state_is_found_by_scanning_not_by_position(self):
        self.assertEqual(I.split_address("Plot 1, Road,Hinjewadi,Pune,Maharashtra,411057"), dict(locality_hint="Hinjewadi", district_hint="Pune", state="Maharashtra", pin="411057"))
        self.assertEqual(I.split_address("MAIN ROAD, MAHAGAON,Maharashtra,416503")["state"], "Maharashtra")           # no district printed
        self.assertEqual(I.split_address("x,y,Pune,Maharashtra")["pin"], "")                                           # no PIN printed
        self.assertEqual(I.split_address("Eluru road, \n Gudivada,Krishna,Andhra Pradesh,521301")["state"], "Andhra Pradesh")
        self.assertEqual(I.split_address("nowhere in particular")["state"], "")

    def test_doubled_text_and_date_from_file_name(self):
        self.assertEqual(I.undouble("Andhra UniversityAndhra University"), "Andhra University"); self.assertEqual(I.undouble("Shivaji   University"), "Shivaji University")
        self.assertEqual(I.list_date("x_as_on_14082025_1.xlsx"), "2025-08-14"); self.assertEqual(I.list_date("no date.xlsx"), "")


class Import(unittest.TestCase):
    def test_keeps_only_maharashtra_and_normalises(self):
        rep, data = run([row(1), row(2, name="Other State College", aishe="C-2", addr="Road,Kochi,Ernakulam,Kerala,682001"), row(3, name="  SPACED   NAME ", aishe="C-3", grade="B++", cgpa=2.80, dec="01-02-2023")])
        self.assertTrue(rep["ok"], rep["problems"]); self.assertEqual(rep["rows_read"], 3); self.assertEqual(rep["rows_maharashtra"], 2)
        d = {x["aishe_id"]: x for x in data}; self.assertEqual(d["C-3"]["name"], "SPACED NAME"); self.assertEqual((d["C-3"]["grade"], d["C-3"]["cgpa"], d["C-3"]["declared_on"], d["C-3"]["list_as_on"]), ("B++", "2.80", "2023-02-01", "2025-08-14"))
        self.assertEqual(len(d["C-1"]["source_sha256"]), 64); self.assertNotIn("valid_to", data[0])                       # no end date is invented

    def test_problems_are_reported_not_guessed(self):
        for bad, what in [(row(1, grade="A+++"), "unknown grade"), (row(1, dec="2024/07/19"), "not dd-mm-yyyy"), (row(1, cgpa="n/a"), "not a number"), (row(1, dec="01-01-2030"), "after the list date"),
                          (row(1, addr="no state here"), "state not readable"), (row(1, cyc="x"), "cycle")]:
            rep, data = run([bad]); self.assertFalse(rep["ok"], what); self.assertTrue(any(what in p for p in rep["problems"]), (what, rep["problems"])); self.assertEqual(data, [])

    def test_duplicate_aishe_is_a_problem_but_duplicate_track_id_is_only_a_warning(self):
        rep, data = run([row(1, aishe="C-9"), row(2, aishe="C-9")]); self.assertFalse(rep["ok"]); self.assertTrue(any("AISHE id C-9" in p for p in rep["problems"]))
        a, b = row(1, aishe="C-1"), row(2, aishe="C-2"); b[2] = a[2]
        rep, data = run([a, b]); self.assertTrue(rep["ok"]); self.assertEqual(len(data), 2); self.assertTrue(any("Track-Id" in w for w in rep["warnings"]))

    def test_cgpa_that_does_not_fit_the_grade_is_a_warning(self):
        rep, data = run([row(1, cgpa=3.40, grade="A")]); self.assertTrue(rep["ok"]); self.assertTrue(any("does not fit grade A" in w for w in rep["warnings"])); self.assertEqual(data[0]["cgpa"], "3.40")

    def test_wrong_file_shapes(self):
        rep, data = run([row(1)], sheet="Sheet1"); self.assertFalse(rep["ok"]); self.assertTrue(any("sheet 'Colleges' is missing" in p for p in rep["problems"]))
        rep, data = run([row(1)], head=HEAD[:-1] + ["Declared"]); self.assertFalse(rep["ok"]); self.assertTrue(any("Date Of Declaration" in p for p in rep["problems"]))
        rep, data = run([row(1)], name="list_without_date.xlsx"); self.assertFalse(rep["ok"]); self.assertTrue(any("list date" in p for p in rep["problems"]))
        with tempfile.TemporaryDirectory() as t:
            rep = I.build(src=t, out=os.path.join(t, "o")); self.assertFalse(rep["ok"]); self.assertTrue(any("no .xlsx" in p for p in rep["problems"]))


class RealFile(unittest.TestCase):
    def test_owner_file_in_repo(self):
        src = os.path.join(ROOT, "data", "manual", "naac")
        if not (os.path.isdir(src) and any(f.endswith(".xlsx") for f in os.listdir(src))): self.skipTest("no NAAC list in this checkout")
        with tempfile.TemporaryDirectory() as t:
            rep = I.build(src=src, out=t); self.assertTrue(rep["ok"], rep["problems"][:5]); self.assertEqual(rep["rows_read"], 7566); self.assertEqual(rep["rows_maharashtra"], 2324)
            self.assertEqual(rep["files"][0]["list_as_on"], "2025-08-14"); self.assertEqual(sum(rep["grades"].values()), 2324); self.assertEqual(rep["grades"]["A++"], 37)
            data = list(csv.DictReader(open(os.path.join(t, "naac_institutions.csv"), encoding="utf-8")))
            kdk = [x for x in data if "K. D. K. COLLEGE OF ENGINEERING" in x["name"]]; self.assertEqual(len(kdk), 1); self.assertEqual((kdk[0]["grade"], kdk[0]["declared_on"]), ("B++", "2024-07-19"))
            self.assertTrue(all(x["state"] == "Maharashtra" and x["declared_on"] <= "2025-08-14" for x in data)); self.assertEqual(len({x["aishe_id"] for x in data}), len(data))


if __name__ == "__main__":
    unittest.main()
