import csv, datetime, os, re, shutil, sys, tempfile, unittest, zipfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from xml.sax.saxutils import escape
from ingestion import nba_import as N
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
REAL = os.path.join(N.MANUAL, "NBA_UG_TierI_WA_2026-11-18.xlsx")
HEAD = N.EXPECTED


def write_xlsx(path, rows, inline=False):
    """A minimal valid .xlsx (first sheet only) built with the standard library."""
    sst, cells = [], []
    def col(i): return "ABCDEFGHIJ"[i]
    for r, row in enumerate(rows, 1):
        cs = []
        for c, v in enumerate(row):
            if v is None: continue
            if inline: cs.append('<c r="%s%d" t="inlineStr"><is><t>%s</t></is></c>' % (col(c), r, escape(str(v))))
            else:
                if v not in sst: sst.append(v)
                cs.append('<c r="%s%d" t="s"><v>%d</v></c>' % (col(c), r, sst.index(v)))
        cells.append('<row r="%d">%s</row>' % (r, "".join(cs)))
    ns = 'xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"'
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("[Content_Types].xml", '<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"/>')
        z.writestr("xl/sharedStrings.xml", '<?xml version="1.0"?><sst %s>%s</sst>' % (ns, "".join("<si><t>%s</t></si>" % escape(str(s)) for s in sst)))
        z.writestr("xl/worksheets/sheet1.xml", '<?xml version="1.0"?><worksheet %s><sheetData>%s</sheetData></worksheet>' % (ns, "".join(cells)))


def good(inst="Walchand College of Engineering (Sangli)", prog="Civil Engineering", period="Academic Year 2024-25, 2025-26 and 2026-27, i.e., upto 30/06/2027", level="Under Graduate", status="ACCREDITED"):
    return [inst, prog, level, status, period]


def setup(rows, tier="UG Tier I (WA)", inline=False, header=HEAD, sources=True, name="a.xlsx"):
    d = tempfile.mkdtemp(); write_xlsx(os.path.join(d, name), [header] + rows, inline)
    if sources:
        with open(os.path.join(d, "sources.csv"), "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f); w.writerow(["file", "tier", "downloaded_on", "note"]); w.writerow([name, tier, "2026-11-18", "owner"])
    return d


def run(rows, **kw):
    d = setup(rows, **kw); o = tempfile.mkdtemp(); rep = N.build(manual=d, out_dir=o)
    p = os.path.join(o, "nba_programs.csv"); return rep, (list(csv.DictReader(open(p, encoding="utf-8"))) if os.path.exists(p) else None)


class Period(unittest.TestCase):
    def p(self, t): return N.parse_period(t)[:3]
    def test_upto_date(self): self.assertEqual(self.p("Academic Year 2024-25, 2025-26 and 2026-27, i.e., upto 30/06/2027"), ("", "2027-06-30", "printed 'upto' date"))
    def test_upto_with_dashes_and_space_variants(self):
        self.assertEqual(self.p("Academic Years 2022-23, 2023-24 and 2024-25, i.e. up to 30-06-2025")[1], "2025-06-30")
        self.assertEqual(self.p("Academic year 2023-24,2024-25 and 2025-26 i.e. upto 30/06/2026")[1], "2026-06-30")
    def test_further_accredited_takes_the_latest(self):
        self.assertEqual(self.p("Academic Year 2022-23, 2023-24 and 2024-25, i.e., upto 30/06/2025; Further Accredited for Academic Year 2025-26, 2026-27 and 2027-28, i.e., upto 30/06/2028")[1], "2028-06-30")
    def test_older_period_alone(self): self.assertEqual(self.p("Academic Year 2017-18, 2018-19, 2019-20, 2020-21 and 2021-22, i.e., upto 30-06-2022")[1], "2022-06-30")
    def test_long_date_range(self): self.assertEqual(self.p("1st January 2026 to 31st December 2028"), ("2026-01-01", "2028-12-31", "printed date range"))
    def test_two_part_range(self): self.assertEqual(self.p("1st July 2025 to 31st December 2025 and from 1st January 2026 to 31st December 2028")[:2], ("2025-07-01", "2028-12-31"))
    def test_accredited_for_prefix_range(self): self.assertEqual(self.p("Accredited for Academic Year 1st July 2025 to 31st December 2025 and from 1st January 2026 to 31st December 2028")[1], "2028-12-31")
    def test_upto_then_further_range(self):
        self.assertEqual(self.p("Academic Year 2022-23, 2023-24 and 2024-25, i.e., upto 30/06/2025. Further Accredited from 1st July 2025 to 31st December 2025 and from 1st January 2026 to 31st December 2028")[1], "2028-12-31")
    def test_wef_computes_end_and_says_so(self): self.assertEqual(self.p("3 YEARS W.E.F. 01-07-2018"), ("2018-07-01", "2021-06-30", "computed: 3 years from the printed w.e.f. date (end date not printed)"))
    def test_wef_spellings(self):
        for t, vf, vt in (("3 YRS.W.E.F.04-05-2007", "2007-05-04", "2010-05-03"), ("3 YEARSW.E.F.19-07-2008", "2008-07-19", "2011-07-18"), ("3 years w.e.f 12.12.2003", "2003-12-12", "2006-12-11"),
                          ("3 YEARS (GRADE C)W.E.F.24-04-2002", "2002-04-24", "2005-04-23"), ("3 YEAR W.E.F 15-2-2005", "2005-02-15", "2008-02-14"), ("5 years w.e.f 10.02.2009", "2009-02-10", "2014-02-09"),
                          ("5 YEARS.W.E.F.19-07-2008", "2008-07-19", "2013-07-18"), ("3 YEARS GRADE B W.E.F. 01-07-2012", "2012-07-01", "2015-06-30")):
            self.assertEqual(self.p(t)[:2], (vf, vt), t)
    def test_wef_leap_day(self): self.assertEqual(self.p("3 YEARS W.E.F. 29-02-2020")[:2], ("2020-02-29", "2023-02-27"))
    def test_wef_typo_year_is_not_guessed(self):
        r = N.parse_period("3 years w.e.f. 16-08-2202"); self.assertEqual(r[:3], ("", "", "unparsed")); self.assertIn("implausible start year", r[3])
    def test_ie_date_without_upto(self): self.assertEqual(self.p("Academic year 2023-24,2024-25 and 2025-26 i.e. 30-06-2026")[1], "2026-06-30")
    def test_no_date_is_unparsed_not_guessed(self): self.assertEqual(self.p("Academic Year 2024-25")[1:], ("", "unparsed"))
    def test_impossible_date_is_a_problem(self): self.assertIn("impossible", N.parse_period("upto 31/02/2027")[3])
    def test_end_year_out_of_range(self): self.assertIn("out of range", N.parse_period("upto 30/06/2099")[3])


class Names(unittest.TestCase):
    def test_split(self):
        self.assertEqual(N.split_name("Walchand College of Engineering (Sangli)"), ("Walchand College of Engineering", "Sangli"))
        self.assertEqual(N.split_name("Thakur College of Engineering & Technology (--Select--)"), ("Thakur College of Engineering & Technology", ""))
        self.assertEqual(N.split_name("MAEER's MIT ACADEMY OF ENGINEERING, ALANDI (DEVACHI) (Pune)"), ("MAEER's MIT ACADEMY OF ENGINEERING, ALANDI (DEVACHI)", "Pune"))
        self.assertEqual(N.split_name("NAGAR YUWAK SHIKSHAN SANSTHA''''S COLLEGE (WANADONGRI)")[0], "NAGAR YUWAK SHIKSHAN SANSTHA'S COLLEGE")
        self.assertEqual(N.split_name("No brackets here"), ("No brackets here", ""))


class Build(unittest.TestCase):
    def test_reads_and_writes(self):
        rep, rows = run([good(), good("Sardar Patel College of Engineering (Mumbai-City)", "Computer Engineering", "1st January 2026 to 31st December 2028")])
        self.assertTrue(rep["ok"], rep["problems"]); self.assertEqual((rep["rows"], rep["institutions"], rep["no_end_date"]), (2, 2, 0))
        r = rows[0]; self.assertEqual((r["tier"], r["institution_name"], r["place"], r["program"], r["status"], r["valid_to"], r["downloaded_on"], r["source_file"]), ("UG Tier I (WA)", "Walchand College of Engineering", "Sangli", "Civil Engineering", "accredited", "2027-06-30", "2026-11-18", "a.xlsx"))
        self.assertEqual(len(r["source_sha256"]), 64); self.assertEqual(r["period_text"], good()[4])

    def test_inline_strings_also_read(self):
        rep, rows = run([good()], inline=True); self.assertTrue(rep["ok"]); self.assertEqual(rows[0]["program"], "Civil Engineering")

    def test_wef_row_gets_computed_end_labelled_as_computed(self):
        rep, rows = run([good(period="3 YEARS W.E.F. 01-07-2018")]); self.assertTrue(rep["ok"]); self.assertEqual((rows[0]["valid_from"], rows[0]["valid_to"]), ("2018-07-01", "2021-06-30")); self.assertTrue(rows[0]["validity_basis"].startswith("computed")); self.assertEqual(rep["no_end_date"], 0)

    def test_typo_year_row_kept_without_dates_with_warning(self):
        rep, rows = run([good(period="3 years w.e.f. 16-08-2202")]); self.assertTrue(rep["ok"]); self.assertEqual((rows[0]["valid_from"], rows[0]["valid_to"]), ("", "")); self.assertTrue(any("implausible" in w for w in rep["warnings"]))

    def test_unreadable_period_is_a_warning_and_kept(self):
        rep, rows = run([good(period="Academic Year 2024-25")]); self.assertTrue(rep["ok"]); self.assertEqual(rows[0]["valid_to"], ""); self.assertTrue(any("no date found" in w for w in rep["warnings"]))

    def test_impossible_date_fails_and_writes_nothing(self):
        rep, rows = run([good(period="upto 31/02/2027")]); self.assertFalse(rep["ok"]); self.assertIsNone(rows)

    def test_unknown_status_is_unknown_never_not_accredited(self):
        rep, rows = run([good(status="WITHDRAWN")]); self.assertEqual(rows[0]["status"], "unknown"); self.assertTrue(rep["warnings"])

    def test_old_and_new_entries_of_a_program_are_both_kept(self):
        rep, rows = run([good(period="Academic Year 2017-18, 2018-19 and 2019-20, i.e., upto 30-06-2020"), good()]); self.assertEqual(sorted(r["valid_to"] for r in rows), ["2020-06-30", "2027-06-30"])

    def test_identical_repeated_row_dropped_with_warning(self):
        rep, rows = run([good(), good()]); self.assertEqual(len(rows), 1); self.assertTrue(any("repeated" in w for w in rep["warnings"]))

    def test_wrong_header_fails(self):
        rep, rows = run([good()], header=["Institution", "Program", "Level", "Status", "Period"]); self.assertFalse(rep["ok"]); self.assertIsNone(rows)

    def test_missing_cell_fails(self):
        rep, rows = run([good(), [good()[0], "", "Under Graduate", "ACCREDITED", good()[4]]]); self.assertFalse(rep["ok"]); self.assertIsNone(rows)

    def test_unknown_level_fails(self):
        rep, _ = run([good(level="Diploma")]); self.assertFalse(rep["ok"])

    def test_listed_file_missing_fails(self):
        d = setup([good()]); os.remove(os.path.join(d, "a.xlsx")); rep = N.build(manual=d, out_dir=tempfile.mkdtemp()); self.assertFalse(rep["ok"])

    def test_no_sources_file_fails(self):
        d = setup([good()], sources=False); rep = N.build(manual=d, out_dir=tempfile.mkdtemp()); self.assertFalse(rep["ok"])

    def test_broken_xlsx_fails_cleanly(self):
        d = setup([good()]); open(os.path.join(d, "a.xlsx"), "wb").write(b"not a zip"); rep = N.build(manual=d, out_dir=tempfile.mkdtemp()); self.assertFalse(rep["ok"]); self.assertTrue(any("cannot be read" in p for p in rep["problems"]))

    def test_two_files_two_tiers(self):
        d = tempfile.mkdtemp(); write_xlsx(os.path.join(d, "t1.xlsx"), [HEAD, good()]); write_xlsx(os.path.join(d, "t2.xlsx"), [HEAD, good("Other College (Pune)", "Civil Engineering")])
        with open(os.path.join(d, "sources.csv"), "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f); w.writerow(["file", "tier", "downloaded_on", "note"]); w.writerow(["t1.xlsx", "UG Tier I (WA)", "2026-11-18", ""]); w.writerow(["t2.xlsx", "UG Tier II", "2026-11-19", ""])
        o = tempfile.mkdtemp(); rep = N.build(manual=d, out_dir=o); self.assertTrue(rep["ok"]); self.assertEqual({r["tier"] for r in csv.DictReader(open(os.path.join(o, "nba_programs.csv"), encoding="utf-8"))}, {"UG Tier I (WA)", "UG Tier II"})

    def test_bad_sources_line_fails(self):
        d = setup([good()], tier=""); rep = N.build(manual=d, out_dir=tempfile.mkdtemp()); self.assertFalse(rep["ok"])


REAL2 = os.path.join(N.MANUAL, "NBA_UG_TierII_2026-11-18.xlsx")


@unittest.skipUnless(os.path.exists(REAL) and os.path.exists(REAL2), "owner's NBA files not in the repository")
class RealFile(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.o = tempfile.mkdtemp(); cls.rep = N.build(out_dir=cls.o)
        cls.rows = list(csv.DictReader(open(os.path.join(cls.o, "nba_programs.csv"), encoding="utf-8"))) if cls.rep["ok"] else []

    def test_real_numbers(self):
        r = self.rep; self.assertTrue(r["ok"], r["problems"])
        self.assertEqual([(f["tier"], f["rows"]) for f in r["files"]], [("UG Tier I (WA)", 258), ("UG Tier II", 1253)])
        self.assertEqual((r["rows"], r["institutions"], r["no_end_date"]), (1511, 217, 3)); self.assertEqual(len(r["warnings"]), 4)

    def test_every_row_is_accounted_for(self):
        self.assertEqual(sum(1 for x in self.rows if not x["valid_to"]), 3)
        self.assertEqual(sorted({(x["tier"], x["status"]) for x in self.rows}), [("UG Tier I (WA)", "accredited"), ("UG Tier II", "accredited"), ("UG Tier II", "unknown")])
        self.assertTrue(all(x["level"] == "Under Graduate" for x in self.rows))
        self.assertTrue(all(x["valid_to"] >= x["valid_from"] for x in self.rows if x["valid_to"] and x["valid_from"]))

    def test_computed_ends_are_labelled(self):
        c = [x for x in self.rows if x["validity_basis"].startswith("computed")]; self.assertEqual(len(c), 701)
        for x in c: self.assertTrue(x["valid_from"] and x["valid_to"] and re.search(r"\d+\s*(years?|yrs?)", x["period_text"], re.I), x["period_text"])

    def test_reader_agrees_with_openpyxl(self):
        try: import openpyxl
        except ImportError: self.skipTest("openpyxl not installed")
        for f in (REAL, REAL2):
            theirs = [[("" if c is None else str(c)) for c in r] for r in openpyxl.load_workbook(f).active.iter_rows(values_only=True)]
            self.assertEqual(N.read_xlsx(f), theirs)


if __name__ == "__main__":
    unittest.main()
