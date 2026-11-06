"""Stage 9b tests: the All India cutoff-list reader, with SYNTHETIC pages built from word positions.
Run: python -m unittest tests/test_stage9b.py -v"""
import csv, gzip, hashlib, io, os, sys, tempfile, unittest
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from ingestion import parse_ai as A
from ingestion.pdf_words import Word
from ingestion.archive import empty_manifest, save_manifest
REAL = A.parse_pdf

def W(t, x, y): return Word(x, y, x + 4.5 * len(t), y + 8, t)
def words(y, items): return [W(t, x, y) for t, x in items]

def header(style="2026"):
    """Heading geometry of the 2026 files, or of 2023-24 (shifted columns, 'Exam(JEE/ MHT-CET)')."""
    if style == "2026":
        return words(96.7, [("Sr.", 51), ("All", 105), ("India", 122), ("Choice", 175), ("Code", 195), ("Merit", 624), ("Exam", 647)]) + words(100.5, [("Institute", 318), ("Name", 350), ("Course", 537), ("Name", 560), ("Type", 717), ("Seat", 770), ("Type", 785)]) + words(111, [("No.", 53), ("Merit", 117)])
    return words(96.7, [("Sr.", 51), ("All", 112), ("India", 128), ("Choice", 178), ("Code", 198), ("Exam(JEE/", 628)]) + words(100.5, [("Institute", 318), ("Name", 350), ("Course", 544), ("Name", 567), ("Type", 698), ("Seat", 750), ("Type", 765)]) + words(121, [("MHT-CET)", 628)])

def row(y, sr, merit, score, code, inst, course_lines, exam, typ, seat, off=0.0, ec=672, tx=716, sx=784):
    w = [W(sr, 55, y)]
    if merit: w += [W(merit, 93, y), W(score, 115, y)]
    if code: w.append(W(code, 177, y + 1.8 + off))
    w += words(y, [("%s" % inst[0], 235), ("-", 257)]) + [W(t, 262 + 40 * i, y) for i, t in enumerate(inst[1].split())]
    for k, line in enumerate(course_lines): w += [W(t, 525 + 45 * j, y + 11 * k) for j, t in enumerate(line.split())]
    toks = exam.split(); total = sum(4.5 * len(t) + 4 for t in toks); x = ec - total / 2
    for t in toks: w.append(W(t, x, y + 3)); x += 4.5 * len(t) + 4
    w += [W(t, tx + 12 * i, y + 3) for i, t in enumerate(typ.split())] + [W(seat, sx, y)]
    return w

FOOT = words(560, [("Cut", 40), ("Off", 55), ("Indicates", 70), ("All", 120), ("India", 135), ("Merit", 160), ("No.;", 185)]) + words(570, [("AI", 40), ("to", 52), ("AI", 62), ("-", 72), ("All", 80)])
def page(rows, style="2026", foot=True): return header(style) + [w for r in rows for w in r] + (FOOT if foot else [])
def R1(y=131.8, sr="1", **kw):
    a = dict(merit="32404", score="(84.6827154)", code="0110124210", inst=("01101", "Government College of Engineering"), course_lines=["Information Technology"], exam="JEE", typ="AI to AI", seat="AI", ec=672, tx=716, sx=784); a.update(kw)
    return row(y, sr, a["merit"], a["score"], a["code"], a["inst"], a["course_lines"], a["exam"], a["typ"], a["seat"], ec=a["ec"], tx=a["tx"], sx=a["sx"])

def run(pages, first=None):
    orig = A.iter_pages; A.iter_pages = lambda path, first=None, last=None: ((i + 1, 841.0, 595.0, w) for i, w in enumerate(pages))
    try: return REAL("x.pdf", first=first)
    finally: A.iter_pages = orig

class Reading(unittest.TestCase):
    def test_a_normal_row(self):
        r = run([page([R1()])]); self.assertEqual(r["problems"], []); x = r["records"][0]; self.assertEqual(r["stats"]["rows"], 1)
        self.assertEqual((x["sr_no"], x["merit_no"], x["score"], x["choice_code"], x["institute_code"], x["institute_name"], x["course_name"], x["merit_exam"], x["merit_exam_kind"], x["ai_type"], x["seat_type"]),
                         (1, 32404, "84.6827154", "0110124210", "01101", "Government College of Engineering", "Information Technology", "JEE", "JEE", "AI to AI", "AI"))
    def test_two_pages_and_contiguous_serial_numbers(self):
        r = run([page([R1(131.8, "1"), R1(157.3, "2")]), page([R1(131.8, "3")])]); self.assertEqual(r["problems"], []); self.assertEqual([x["sr_no"] for x in r["records"]], [1, 2, 3]); self.assertEqual(r["stats"]["pages"], 2)
    def test_serial_numbers_from_1000_are_printed_with_a_comma(self):
        r = run([page([R1(131.8, "999"), R1(157.3, "1,000"), R1(182.8, "1,001")])], first=2); self.assertEqual(r["problems"], []); self.assertEqual([x["sr_no"] for x in r["records"]], [999, 1000, 1001])
    def test_the_first_row_of_a_whole_list_must_be_number_1(self):
        self.assertTrue(any("serial number 5 where 1 was expected" in p["problem"] for p in run([page([R1(131.8, "5")])])["problems"]))
    def test_a_gap_in_serial_numbers_is_reported(self):
        self.assertTrue(any("serial number 3 where 2 was expected" in p["problem"] for p in run([page([R1(131.8, "1"), R1(157.3, "3")])])["problems"]))
    def test_the_choice_code_printed_a_little_lower_than_the_name_is_still_read(self):
        r = run([page([R1(code="0110124210")])]); self.assertEqual(r["records"][0]["choice_code"], "0110124210")
    def test_course_names_wrapping_over_lines_are_joined(self):
        r = run([page([R1(course_lines=["Electronics and", "Telecommunication Engg"])])]); self.assertEqual(r["records"][0]["course_name"], "Electronics and Telecommunication Engg")
    def test_a_blank_cutoff_is_recorded_as_blank_never_as_zero(self):
        r = run([page([R1(merit="", score="", exam="MHT-CET", typ="MI to AI", seat="MI")])]); self.assertEqual(r["problems"], []); x = r["records"][0]
        self.assertEqual((x["merit_no"], x["score"], x["choice_code"], x["note"]), ("", "", "0110124210", "no cutoff printed in the source")); self.assertEqual((r["stats"]["rows"], r["stats"]["blank_rows"]), (1, 1))
    def test_a_row_missing_only_the_choice_code_is_reported(self):
        self.assertTrue(run([page([R1(code="")])])["problems"])
    def test_exam_names_of_every_kind(self):
        for exam, kind in (("JEE", "JEE"), ("JEE(Main)", "JEE"), ("JEE(Main)-2026", "JEE"), ("MHT-CET", "MHT-CET"), ("MHT-CET-PCB 2026", "MHT-CET"), ("NEET-2025", "NEET"), ("NEET 2026", "NEET")):
            r = run([page([R1(exam=exam)])]); self.assertEqual((r["problems"], r["records"][0]["merit_exam"], r["records"][0]["merit_exam_kind"]), ([], exam, kind), exam)
    def test_maharashtra_seats_for_all_india_candidates_have_a_state_seat_code(self):
        r = run([page([R1(typ="MH to AI", seat="GNT1H", exam="MHT-CET")])]); self.assertEqual((r["problems"], r["records"][0]["ai_type"], r["records"][0]["seat_type"]), ([], "MH to AI", "GNT1H"))
    def test_the_other_year_layout_with_shifted_columns(self):
        r = run([page([R1(exam="JEE(Main)", ec=655, tx=700, sx=765)], style="2023")]); self.assertEqual(r["problems"], []); self.assertEqual((r["records"][0]["merit_exam"], r["records"][0]["ai_type"], r["records"][0]["seat_type"]), ("JEE(Main)", "AI to AI", "AI"))
    def test_the_footer_legend_is_never_read_as_part_of_the_last_row(self):
        r = run([page([R1()])]); self.assertEqual(r["records"][0]["seat_type"], "AI"); self.assertEqual(r["records"][0]["course_name"], "Information Technology")
    def test_score_is_kept_as_printed_text(self): self.assertEqual(run([page([R1(score="(92.0000000)")])])["records"][0]["score"], "92.0000000")

class NothingIsGuessed(unittest.TestCase):
    def test_a_course_code_that_does_not_start_with_its_institute_code_is_reported(self):
        self.assertTrue(any("does not start with institute code" in p["problem"] for p in run([page([R1(code="0220124210")])])["problems"]))
    def test_an_unknown_type_is_reported(self):
        self.assertTrue(any("unknown type" in p["problem"] for p in run([page([R1(typ="XX to AI")])])["problems"]))
    def test_a_missing_page_heading_is_reported_not_skipped(self):
        r = run([header() [3:] + R1()]); self.assertTrue(r["problems"]); self.assertEqual(r["records"], [])
    def test_a_word_straddling_a_column_boundary_is_reported(self):
        bad = R1() + [Word(500, 140, 560, 148, "Wide-Token")]; r = run([page([bad])]); self.assertTrue(any("straddles a column boundary" in p["problem"] for p in r["problems"]))
    def test_an_empty_course_is_reported(self):
        self.assertTrue(any("course is empty" in p["problem"] for p in run([page([R1(course_lines=[])])])["problems"]))
    def test_a_merit_without_a_score_is_reported(self):
        self.assertTrue(any("merit cell" in p["problem"] for p in run([page([R1(score="")])])["problems"]))

class CrossCheck(unittest.TestCase):
    def test_classifies_differences(self):
        recs = [dict(choice_code="0110124210", institute_name="Govt College", course_name="Computer Science and Engineering(Artificial"), dict(choice_code="0110124220", institute_name="Other Name", course_name="Civil"), dict(choice_code="0110124230", institute_name="Govt College", course_name="Mechanical"), dict(choice_code="9999999999", institute_name="x", course_name="y"), dict(choice_code="", institute_name="x", course_name="y")]
        names = {"0110124210": ("Govt College", "Computer Science and Engineering(Artificial Intelligence and Machine Learning)"), "0110124220": ("Govt College", "Civil"), "0110124230": ("Govt College", "Electrical")}
        c = A.cross_check(recs, names); self.assertEqual((c["course_name_truncated_in_ai_list"], c["institute_name_differs"], c["course_name_differs"], c["not_in_state_list"]), (1, 1, 1, 1))
    def test_nothing_to_compare_with(self): self.assertIsNone(A.cross_check([], {}))

class CommandLine(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp(); self.files = os.path.join(self.d, "f"); os.makedirs(self.files); body = b"%PDF-1.7 x %%EOF"; self.sha = hashlib.sha256(body).hexdigest(); self.asset = self.sha[:16] + "__ai.pdf"
        open(os.path.join(self.files, self.asset), "wb").write(body)
        m = empty_manifest(); m["documents"]["a"] = {"doc_type": "cutoff", "scope": "AI", "year_label": "2026-27", "cap_round": "IV", "current_sha256": self.sha}; m["documents"]["b"] = {"doc_type": "cutoff", "scope": "MH", "year_label": "2026-27", "cap_round": "IV", "current_sha256": self.sha}
        m["files"][self.sha] = {"sha256": self.sha, "asset_name": self.asset, "size_bytes": len(body)}; self.mp = os.path.join(self.d, "m.json"); save_manifest(self.mp, m)
        self.orig = A.parse_pdf; A.parse_pdf = lambda path, first=None, last=None, meta=None: run([page([R1(131.8, "1"), R1(157.3, "2", merit="", score="", exam="MHT-CET", typ="MI to AI", seat="MI")])])
    def tearDown(self): A.parse_pdf = self.orig
    def test_writes_rows_including_blank_ones_and_a_report(self):
        out = os.path.join(self.d, "o"); rep = A.run_cli(self.mp, self.files, out); e = rep["files"][0]
        self.assertTrue(rep["all_ok"]); self.assertEqual(len(rep["files"]), 1); self.assertEqual((e["rows"], e["blank_rows"], e["complete"], e["problem_count"]), (2, 1, True, 0))
        rows = list(csv.DictReader(io.StringIO(gzip.open(os.path.join(out, e["output"])).read().decode("utf-8")))); self.assertEqual(list(rows[0]), A.COLUMNS); self.assertEqual(rows[1]["merit_no"], ""); self.assertEqual(rows[0]["source_sha256"], self.sha)
    def test_repeatable_byte_for_byte(self):
        a, b = os.path.join(self.d, "a"), os.path.join(self.d, "b"); A.run_cli(self.mp, self.files, a); A.run_cli(self.mp, self.files, b); f = "2026-27_round-IV_AI.csv.gz"; self.assertEqual(open(os.path.join(a, f), "rb").read(), open(os.path.join(b, f), "rb").read())
    def test_a_file_that_is_not_the_archived_one_is_refused(self):
        open(os.path.join(self.files, self.asset), "ab").write(b"x"); rep = A.run_cli(self.mp, self.files, os.path.join(self.d, "o")); self.assertFalse(rep["all_ok"]); self.assertIn("fingerprint mismatch", rep["files"][0]["error"])
    def test_exit_code(self): self.assertEqual(A.main(["--manifest", self.mp, "--files", self.files, "--out", os.path.join(self.d, "o"), "--mh-dir", self.d]), 0)
if __name__ == "__main__": unittest.main()
