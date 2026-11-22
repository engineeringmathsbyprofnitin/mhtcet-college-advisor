"""Stage 12c-2: NAAC list reader (owner-downloaded Excel). Temp folders only."""
import csv, json, os, shutil, sys, tempfile, unittest, zipfile
from xml.sax.saxutils import escape
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from ingestion import naac_import as I
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
HEAD = ["Sl No", "HEI Name", "Track-Id", "Aishe-Id", "Affiliating University", "Address", "Current Cycle Number", "Current CGPA", "Current Grade", "Date Of Declaration"]


def write_xlsx(path, sheets):
    """A minimal valid .xlsx with several named sheets, built with the standard library (GitHub's test runner has no openpyxl). Numbers are numeric cells, text is inline text."""
    ns = 'xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"'; rel = 'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"'
    def col(i): return "ABCDEFGHIJKLMNOP"[i]
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("[Content_Types].xml", '<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"/>')
        z.writestr("xl/workbook.xml", '<?xml version="1.0"?><workbook %s %s><sheets>%s</sheets></workbook>' % (ns, rel, "".join('<sheet name="%s" sheetId="%d" r:id="rId%d"/>' % (escape(n), i, i) for i, (n, _r) in enumerate(sheets, 1))))
        z.writestr("xl/_rels/workbook.xml.rels", '<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">%s</Relationships>' % "".join('<Relationship Id="rId%d" Target="worksheets/sheet%d.xml"/>' % (i, i) for i in range(1, len(sheets) + 1)))
        for i, (n, rows) in enumerate(sheets, 1):
            body = []
            for r, row in enumerate(rows, 1):
                cs = []
                for c, v in enumerate(row):
                    if v is None: continue
                    cs.append('<c r="%s%d"><v>%s</v></c>' % (col(c), r, v) if isinstance(v, (int, float)) else '<c r="%s%d" t="inlineStr"><is><t xml:space="preserve">%s</t></is></c>' % (col(c), r, escape(str(v))))
                body.append('<row r="%d">%s</row>' % (r, "".join(cs)))
            z.writestr("xl/worksheets/sheet%d.xml" % i, '<?xml version="1.0"?><worksheet %s><sheetData>%s</sheetData></worksheet>' % (ns, "".join(body)))


def mk(rows, name="Institutions_accredited_by_NAAC_having_valid_accreditation-as_on_14082025_1.xlsx", sheet="Colleges", head=HEAD):
    tmp = tempfile.mkdtemp(); src = os.path.join(tmp, "src"); os.makedirs(src)
    write_xlsx(os.path.join(src, name), [(sheet, [head] + rows), ("Transition Autonomous Colleges", [["Sl. No.", "HEI Name", "State", "Extended validity upto"]])]); return tmp, src


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


class Reader(unittest.TestCase):
    def test_reads_the_named_sheet_not_the_first_one(self):
        tmp = tempfile.mkdtemp(); p = os.path.join(tmp, "x.xlsx"); write_xlsx(p, [("Other", [["a", "b"], [1, 2]]), ("Colleges", [["h1", "h2"], ["x", 3.5], [None, 4]])])
        try:
            self.assertEqual(I.read_sheet(p, "Colleges"), [["h1", "h2"], ["x", "3.5"], ["", "4"]]); self.assertEqual(I.sheet_names(p), ["Other", "Colleges"]); self.assertRaises(KeyError, I.read_sheet, p, "Nope")
        finally: shutil.rmtree(tmp, ignore_errors=True)

    def test_not_an_excel_file_is_a_problem_not_a_crash(self):
        tmp = tempfile.mkdtemp(); src = os.path.join(tmp, "s"); os.makedirs(src); open(os.path.join(src, "x_as_on_14082025.xlsx"), "wb").write(b"this is not a zip")
        try: rep = I.build(src=src, out=os.path.join(tmp, "o")); self.assertFalse(rep["ok"]); self.assertTrue(any("cannot be read" in p for p in rep["problems"]))
        finally: shutil.rmtree(tmp, ignore_errors=True)

    def test_agrees_with_openpyxl_on_the_real_file_when_it_is_installed(self):
        try: import openpyxl
        except ImportError: self.skipTest("openpyxl not installed")
        f = os.path.join(ROOT, "data", "manual", "naac", "Institutions_accredited_by_NAAC_having_valid_accreditation-as_on_14082025_1.xlsx")
        if not os.path.exists(f): self.skipTest("no NAAC list in this checkout")
        theirs = [[("" if c is None else str(c)) for c in r] for r in openpyxl.load_workbook(f, read_only=True)["Colleges"].iter_rows(values_only=True)]
        mine = I.read_sheet(f, "Colleges"); self.assertEqual(len(mine), len(theirs)); self.assertEqual(mine[0][:9], theirs[0][:9]); self.assertEqual([r[1] for r in mine[1:50]], [r[1] for r in theirs[1:50]])


class GitHubRunner(unittest.TestCase):
    def test_no_module_needs_an_extra_package_at_import(self):
        """GitHub's self-test step installs only PyYAML: a top-level 'import openpyxl' (or pandas / numpy) in a test or ingestion module would fail the whole step."""
        bad = []
        for d in ("tests", "ingestion"):
            for f in sorted(os.listdir(os.path.join(ROOT, d))):
                if f.endswith(".py"):
                    for i, line in enumerate(open(os.path.join(ROOT, d, f), encoding="utf-8"), 1):
                        if line.startswith(("import openpyxl", "from openpyxl", "import pandas", "from pandas", "import numpy", "from numpy")): bad.append("%s/%s:%d" % (d, f, i))
        self.assertEqual(bad, [])


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
