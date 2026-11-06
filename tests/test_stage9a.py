"""Stage 9a tests: the Maharashtra State cutoff-list reader, using SYNTHETIC pages built from word positions
(each trap found in the real 2023-2026 files has its own test). Run: python -m unittest tests/test_stage9a.py -v"""
import gzip, hashlib, io, csv, json, os, sys, tempfile, unittest
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from ingestion import parse_mh as P, codes as C
from ingestion.pdf_words import Word
from ingestion.archive import empty_manifest, save_manifest
REAL_PARSE = P.parse_pdf

def L(y, text, x0=40.0):
    out, x = [], x0
    for t in text.split(): out.append(Word(x, y, x + 5.0 * len(t), y + 8, t)); x += 5.0 * len(t) + 4
    return out
def R(y, cells): return [Word(x, y, x + 5.0 * len(t), y + 8, t) for t, x in cells]
TITLE = lambda y=20, year="A.Y. 2026-27", rnd="IV": L(y, "Cut Off List for Maharashtra & Minority Seats of CAP Round - %s for the Admission to the First Year %s" % (rnd, year))

def table(y0, header, rows, title="State Level"):
    """header = [(code, x)], rows = [(label, [(num, pct, x)])]"""
    w = L(y0, title, 29) + R(y0 + 25, [("Stage", 40)] + header)
    y = y0 + 45
    for label, cells in rows:
        w += R(y, [(label, 47)] + [(n, x) for n, p, x in cells]); y += 9
        w += R(y, [(p, x) for n, p, x in cells]); y += 14
    return w

def run(pages, meta=None):
    orig = P.iter_pages
    P.iter_pages = lambda path, first=None, last=None: ((i + 1, 1740.0, 842.0, w) for i, w in enumerate(pages))
    try: return REAL_PARSE("x.pdf", meta=meta)
    finally: P.iter_pages = orig

def basic(inst="01002 - Government College of Engineering, Amravati", course="0100219110 - Civil Engineering", status="Status: Government Autonomous Home University : Autonomous Institute", year="A.Y. 2026-27"):
    return TITLE(year=year) + L(60, inst, 18) + L(80, course, 18) + L(95, status, 20) + table(115, [("GOPENS", 83), ("GSCS", 139)], [("I", [("32404", "(92.3369677)", 73), ("40301", "(90.4500000)", 129)])])

class Reading(unittest.TestCase):
    def test_a_normal_page(self):
        r = run([basic()], {"year_label": "2026-27", "cap_round": "IV"}); self.assertEqual(r["problems"], []); self.assertEqual(r["stats"]["cells"], 2); self.assertEqual(r["stats"]["printed_percentiles"], 2)
        a, b = r["records"]; self.assertEqual((a["institute_code"], a["choice_code"], a["course_name"], a["seat_code"], a["merit_no"], a["percentile"], a["stage"]), ("01002", "0100219110", "Civil Engineering", "GOPENS", 32404, "92.3369677", "I"))
        self.assertEqual((b["seat_code"], b["merit_no"], b["percentile"]), ("GSCS", 40301, "90.4500000")); self.assertEqual(a["status"], "Government Autonomous"); self.assertEqual(a["home_university"], "Autonomous Institute")
        self.assertEqual((a["seat_pool"], a["allotted_to"], a["section"]), ("State Level", "", "State Level")); self.assertEqual(r["file_header"], {"year": "2026-27", "round": "IV"})
    def test_percentile_text_is_kept_exactly(self): self.assertEqual(run([basic()])["records"][1]["percentile"], "90.4500000")
    def test_both_title_wordings_are_understood(self):
        for y in ("A.Y. 2026-27", "for the Year 2026-27", "Academic Year 2026-2027"): self.assertEqual(run([basic(year=y)])["file_header"]["year"], "2026-27", y)
    def test_a_file_that_is_not_what_it_was_archived_as_is_reported(self):
        r = run([basic()], {"year_label": "2025-26", "cap_round": "III"}); t = " ".join(p["problem"] for p in r["problems"]); self.assertIn("archived as 2025-26", t); self.assertIn("archived as III", t)
    def test_an_unrecognised_title_block_is_reported_not_skipped_silently(self):
        r = run([L(20, "Something else entirely") + L(30, "more") + L(40, "more") + L(50, "more") + L(52, "more") + L(54, "more") + L(56, "more") + L(58, "more") + basic()[len(TITLE()):]])
        self.assertTrue(any("title block not recognised" in p["problem"] for p in r["problems"]))
    def test_2023_codes_that_lost_their_leading_zero_are_repaired_and_checked(self):
        r = run([basic(inst="1002 - Government College of Engineering, Amravati", course="100219110 - Civil Engineering")]); self.assertEqual(r["problems"], [])
        self.assertEqual((r["records"][0]["institute_code"], r["records"][0]["choice_code"]), ("01002", "0100219110"))
    def test_a_course_that_does_not_belong_to_its_institute_is_reported(self):
        r = run([basic(course="0200219110 - Civil Engineering")]); self.assertTrue(any("does not start with institute code" in p["problem"] for p in r["problems"]))
    def test_course_codes_with_one_or_two_letters(self):
        for code in ("0302524270U", "0303337293LK"):
            r = run([basic(inst="03025 - X College" if code.startswith("03025") else "03033 - Y University", course="%s - Electronics Engg" % code)]); self.assertEqual(r["problems"], [], code); self.assertEqual(r["records"][0]["choice_code"], code)
    def test_a_heading_that_looks_like_a_code_but_is_unknown_is_reported_never_absorbed(self):
        r = run([basic()[:len(TITLE()) + 5] + L(70, "12345678 - Mystery heading", 18) + basic()[len(TITLE()) + 5:]]); self.assertTrue(any("looks like an institute or course code" in p["problem"] for p in r["problems"]))
    def test_long_course_names_that_wrap_are_joined(self):
        w = TITLE() + L(60, "01002 - College", 18) + L(80, "0100219110 - Master of Engineering and Technology", 18) + L(88, "(Integrated 5 Years)", 18) + L(103, "Status: Government", 20) + table(125, [("GOPENS", 83)], [("I", [("5", "(99.1000000)", 73)])])
        self.assertEqual(run([w])["records"][0]["course_name"], "Master of Engineering and Technology (Integrated 5 Years)")
    def test_home_university_sections_are_split_into_pool_and_candidates(self):
        self.assertEqual(P.section_parts("Other Than Home University Seats Allotted to Home University Candidates"), {"seat_pool": "Other Than Home University", "allotted_to": "Home University"})
        self.assertEqual(P.section_parts("Maharashtra State Seats Allotted to All India Candidature Candidates"), {"seat_pool": "Maharashtra State", "allotted_to": "All India Candidature"})
        self.assertEqual(P.section_parts("State Level"), {"seat_pool": "State Level", "allotted_to": ""})
    def test_several_sections_and_courses_on_one_page(self):
        w = basic() + table(200, [("GOPENH", 83)], [("I", [("100", "(98.0000000)", 73)])], title="Home University Seats Allotted to Home University Candidates") + L(260, "0100219120 - Mechanical Engineering", 18) + L(275, "Status: Government", 20) + table(295, [("GOPENS", 83)], [("I", [("7", "(99.5000000)", 73)])])
        r = run([w]); self.assertEqual(r["problems"], []); self.assertEqual([(x["choice_code"], x["seat_pool"], x["seat_code"]) for x in r["records"]],
            [("0100219110", "State Level", "GOPENS"), ("0100219110", "State Level", "GSCS"), ("0100219110", "Home University", "GOPENH"), ("0100219120", "State Level", "GOPENS")])

class TrapsFromTheRealFiles(unittest.TestCase):
    def test_stage_labels_of_any_kind_are_read(self):
        for label in ("I", "VII", "MH", "II"):
            w = TITLE() + L(60, "01002 - College", 18) + L(80, "0100219110 - Civil Engineering", 18) + L(95, "Status: Government", 20) + table(115, [("GOPENS", 83)], [(label, [("9", "(97.0000000)", 73)])])
            r = run([w]); self.assertEqual((r["problems"], r["records"][0]["stage"]), ([], label))
    def test_two_line_stage_labels_are_joined(self):
        w = TITLE() + L(60, "01002 - College", 18) + L(80, "0100219110 - Civil Engineering", 18) + L(95, "Status: Government", 20) + L(115, "State Level", 29) + R(140, [("Stage", 40), ("PWDOBCH", 83)])
        w += R(160, [("I-Non", 44), ("129017", 73)]) + R(169, [("PWD", 44), ("(66.5496835)", 73)])
        r = run([w]); self.assertEqual((r["problems"], r["records"][0]["stage"], r["records"][0]["seat_code"]), ([], "I-Non PWD", "PWDOBCH"))
    def test_a_long_seat_code_wrapped_onto_a_second_heading_line_is_joined(self):
        w = TITLE() + L(60, "01002 - College", 18) + L(80, "0100219110 - Civil Engineering", 18) + L(95, "Status: Government", 20) + L(115, "State Level", 29)
        w += R(140, [("Stage", 40), ("GOPENS", 83), ("PWDROBC", 139)]) + R(147, [("S", 160)]) + R(168, [("I", 47), ("5", 73), ("6", 129)]) + R(177, [("(97.0000000)", 73), ("(95.0000000)", 129)])
        r = run([w]); self.assertEqual(r["problems"], []); self.assertEqual([x["seat_code"] for x in r["records"]], ["GOPENS", "PWDROBCS"])
    def test_overflow_page_columns_join_the_table_of_the_previous_page_by_height(self):
        p1 = basic(); hdr_y = 115 + 25; row_y = 115 + 45
        p2 = R(hdr_y - 1.5, [("ORPHANI", 83), ("EWS", 139)]) + R(row_y + 0.8, [("27213", 73), ("15000", 129)]) + R(row_y + 9.8, [("(81.1000000)", 73), ("(88.2000000)", 129)])
        r = run([p1, p2]); self.assertEqual(r["problems"], []); self.assertEqual(r["stats"]["overflow_pages"], 1); self.assertEqual(r["stats"]["cells"], 4)
        o = [x for x in r["records"] if x["seat_code"] in ("ORPHANI", "EWS")]; self.assertEqual({(x["seat_code"], x["stage"], x["choice_code"], x["page"]) for x in o}, {("ORPHANI", "I", "0100219110", 2), ("EWS", "I", "0100219110", 2)})
    def test_an_overflow_block_that_matches_no_table_is_reported(self):
        r = run([basic(), R(400, [("ORPHANI", 83)]) + R(420, [("5", 73)]) + R(429, [("(81.1000000)", 73)])]); self.assertTrue(any("match no table" in p["problem"] for p in r["problems"])); self.assertEqual(r["stats"]["cells"], 2)
    def test_an_overflow_row_that_matches_no_stage_row_is_reported(self):
        r = run([basic(), R(138.5, [("ORPHANI", 83)]) + R(300, [("5", 73)]) + R(309, [("(81.1000000)", 73)])]); self.assertTrue(any("matches no stage row" in p["problem"] for p in r["problems"]))

class NothingIsGuessed(unittest.TestCase):
    def test_a_number_without_its_percentile_is_reported(self):
        w = basic()[:-1] ; w = [x for x in basic() if not x.text.startswith("(90.45")]
        r = run([w]); self.assertTrue(any("GSCS" in p["problem"] and "not the percentile" in p["problem"] for p in r["problems"])); self.assertEqual(r["stats"]["cells"], 1)
    def test_a_percentile_without_its_number_is_reported(self):
        w = [x for x in basic() if x.text != "40301"]; r = run([w]); self.assertTrue(any("percentile but not the number" in p["problem"] for p in r["problems"])); self.assertEqual(r["stats"]["cells"], 1)
    def test_a_value_under_no_heading_is_reported(self):
        w = basic() + R(205, [("I", 47), ("77", 900)]) + R(214, [("(50.0000000)", 900)]); r = run([w]); self.assertTrue(any("sits under no column heading" in p["problem"] for p in r["problems"]))
    def test_blank_cells_stay_absent_never_zero(self):
        w = TITLE() + L(60, "01002 - College", 18) + L(80, "0100219110 - Civil Engineering", 18) + L(95, "Status: Government", 20) + table(115, [("GOPENS", 83), ("GSCS", 139), ("GVJS", 195)], [("I", [("5", "(99.0000000)", 73), ("9", "(97.0000000)", 185)])])
        self.assertEqual([x["seat_code"] for x in run([w])["records"]], ["GOPENS", "GVJS"])
    def test_a_row_with_numbers_but_no_percentile_line_is_reported(self):
        w = TITLE() + L(60, "01002 - College", 18) + L(80, "0100219110 - Civil Engineering", 18) + L(95, "Status: Government", 20) + L(115, "State Level", 29) + R(140, [("Stage", 40), ("GOPENS", 83)]) + R(160, [("I", 47), ("5", 73)])
        self.assertTrue(any("numbers but no percentile line" in p["problem"] for p in run([w])["problems"]))
    def test_percentile_out_of_range_is_rejected(self):
        w = [Word(x.x0, x.y0, x.x1, x.y1, "(192.3369677)") if x.text == "(92.3369677)" else x for x in basic()]; r = run([w]); self.assertTrue(any("out of range" in p["problem"] for p in r["problems"])); self.assertEqual(r["stats"]["cells"], 1)

class Codes(unittest.TestCase):
    def test_padding_and_checking(self):
        self.assertEqual(C.norm_institute_code("1002"), "01002"); self.assertEqual(C.norm_institute_code("01002"), "01002"); self.assertIsNone(C.norm_institute_code("123"))
        for raw, want in (("100219110", "0100219110"), ("0100219110", "0100219110"), ("302524270U", "0302524270U"), ("0303337293LK", "0303337293LK")): self.assertEqual(C.norm_choice_code(raw), want)
        self.assertIsNone(C.norm_choice_code("12345")); self.assertIsNone(C.norm_choice_code("0100219110ABCD")); self.assertTrue(C.choice_matches_institute("0100219110", "01002")); self.assertFalse(C.choice_matches_institute("0100219110", "01003"))

class CommandLine(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp(); self.files = os.path.join(self.d, "files"); os.makedirs(self.files); body = b"%PDF-1.7 fake %%EOF"; self.sha = hashlib.sha256(body).hexdigest(); self.asset = self.sha[:16] + "__x.pdf"
        open(os.path.join(self.files, self.asset), "wb").write(body)
        m = empty_manifest(); m["documents"]["d1"] = {"doc_type": "cutoff", "scope": "MH", "year_label": "2026-27", "cap_round": "IV", "current_sha256": self.sha}
        m["documents"]["d2"] = {"doc_type": "cutoff", "scope": "AI", "year_label": "2026-27", "cap_round": "IV", "current_sha256": self.sha}      # not an MH file: ignored
        m["files"][self.sha] = {"sha256": self.sha, "asset_name": self.asset, "size_bytes": len(body)}; self.mp = os.path.join(self.d, "m.json"); save_manifest(self.mp, m)
        self.orig = P.parse_pdf; P.parse_pdf = lambda path, first=None, last=None, meta=None: run([basic()], meta)
    def tearDown(self): P.parse_pdf = self.orig
    def test_writes_a_normalized_file_and_a_verified_report(self):
        out = os.path.join(self.d, "out"); rep = P.run_cli(self.mp, self.files, out, "2026-10-29T00:00:00Z"); e = rep["files"][0]
        self.assertTrue(rep["all_ok"]); self.assertEqual(len(rep["files"]), 1); self.assertEqual((e["cells"], e["printed_percentiles"], e["complete"], e["problem_count"]), (2, 2, True, 0))
        rows = list(csv.DictReader(io.StringIO(gzip.open(os.path.join(out, e["output"])).read().decode("utf-8")))); self.assertEqual(len(rows), 2); self.assertEqual(rows[0]["source_sha256"], self.sha)
        self.assertEqual((rows[0]["year_label"], rows[0]["cap_round"], rows[0]["choice_code"], rows[0]["merit_no"], rows[0]["percentile"]), ("2026-27", "IV", "0100219110", "32404", "92.3369677"))
        self.assertEqual(list(rows[0]), P.COLUMNS)
    def test_output_is_byte_for_byte_repeatable(self):
        a, b = os.path.join(self.d, "a"), os.path.join(self.d, "b"); P.run_cli(self.mp, self.files, a); P.run_cli(self.mp, self.files, b); f = "2026-27_round-IV_MH.csv.gz"; self.assertEqual(open(os.path.join(a, f), "rb").read(), open(os.path.join(b, f), "rb").read())
    def test_a_file_that_is_not_the_archived_one_is_refused(self):
        open(os.path.join(self.files, self.asset), "ab").write(b"tampered"); rep = P.run_cli(self.mp, self.files, os.path.join(self.d, "o")); self.assertFalse(rep["all_ok"]); self.assertIn("fingerprint mismatch", rep["files"][0]["error"])
    def test_a_missing_file_is_reported(self):
        os.remove(os.path.join(self.files, self.asset)); rep = P.run_cli(self.mp, self.files, os.path.join(self.d, "o")); self.assertFalse(rep["all_ok"]); self.assertIn("not present", rep["files"][0]["error"])
    def test_exit_code_is_zero_only_when_everything_is_complete(self):
        self.assertEqual(P.main(["--manifest", self.mp, "--files", self.files, "--out", os.path.join(self.d, "o1")]), 0)
        P.parse_pdf = lambda path, first=None, last=None, meta=None: dict(run([basic()], meta), stats=dict(run([basic()])["stats"], printed_percentiles=99)); self.assertEqual(P.main(["--manifest", self.mp, "--files", self.files, "--out", os.path.join(self.d, "o2")]), 4)
    def test_merit_number_conflicts_are_counted_not_hidden(self):
        recs = [dict(seat_pool="State Level", allotted_to="", merit_no=5, percentile="90.0"), dict(seat_pool="State Level", allotted_to="", merit_no=5, percentile="91.0"), dict(seat_pool="Home University", allotted_to="X", merit_no=5, percentile="50.0")]
        self.assertEqual(P.merit_conflicts(recs), 1)
if __name__ == "__main__": unittest.main()
