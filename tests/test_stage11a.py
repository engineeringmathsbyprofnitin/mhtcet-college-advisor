import os, re, sys, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from ingestion import parse_vacancy as P

FIX = os.path.join(os.path.dirname(__file__), "fixtures", "vacancy_cap4_pages1-2.txt")
RAW = open(FIX, encoding="utf-8").read()
# The fixture is pages 1-2 of the real file. It is cut after page 2, so (a) the page total is changed from 1013 to 2 and
# (b) the header of the next, cut-off block at the very end of page 2 is removed. Nothing else is edited.
SAMPLE = RAW.replace("of 1013", "of 2")
SAMPLE = "\n".join(l for l in SAMPLE.split("\n") if "Vacant CAP Seats:2" not in l or "Government" not in l and "Un-Aided" not in l and "Autonomous" not in l)


def block(code="0100219110", name="Civil Engineering", si=60, ms=1, mino=0, ai=0, inst=0, oi=0, on=0, vac=None,
          state=(0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0), pwd=(0,) * 9, dfn=(0,) * 9, ews="Seats: 0",
          head="Government Autonomous", instline=" 01002 - Government College of Engineering, Amravati", name_above=None):
    vac = ms + ai + mino if vac is None else vac
    g = "     State Level   " + "  ".join(map(str, state)) + "  " + str(sum(state)) + "\n"
    codeline = "     %s        %s        %d   %d   %d   %d   %d   %d   %d\n" % (code, name if not name_above else "", si, ms, mino, ai, inst, oi, on)
    return (instline + "\n\n " + head + "      Vacant CAP Seats:%d\n   MS\n Choice Code   Course Name   SI  Minority Seats  All India  Institute Seats OrphanI OrphanN\n   Seats\n" % vac
            + (("   " + name_above + "\n") if name_above else "") + codeline
            + "      Category   OPEN   SC   ST   VJ/DT   NTB   NTC   NTD   OBC   SEBC   Total\n\n  General / Ladies   G  L\n\n" + g
            + "        PWD   " + "  ".join(map(str, pwd)) + "  " + str(sum(pwd)) + "\n   PWD Common Reserved Seats : 0\n"
            + "        DEF   " + "  ".join(map(str, dfn)) + "  " + str(sum(dfn)) + "\n   DEF Common Reserved Seats : 0\n"
            + " Economically Weaker Section (EWS) Seats: 0     Tution Fee Waiver Scheme Choice Code: " + ews.replace("Seats", "Seats") + "\n\n")


def page(body, n=1, total=1):
    return body + "STATE CET CELL , Mumbai          Page %d of %d\n\f" % (n, total)


class RealSample(unittest.TestCase):
    def test_real_pages_clean(self):
        r = P.parse_text(SAMPLE)
        self.assertEqual(r["problems"], [])
        self.assertEqual(r["unrecognised"], [])
        self.assertGreaterEqual(len(r["blocks"]), 2)

    def test_first_real_block(self):
        b = P.parse_text(SAMPLE)["blocks"][0]
        self.assertEqual((b["inst_code"], b["code"], b["course"], b["si"], b["vacant"]), ("01002", "0100219110", "Civil Engineering", 60, 1))
        self.assertEqual(b["kind"], "Government Autonomous")
        self.assertEqual((b["tfws_code"], b["tfws"]), ("0100219111T", 1))

    def test_wrapped_course_name_and_page_break(self):
        bl = P.parse_text(SAMPLE)["blocks"]
        self.assertEqual(bl[1]["course"], "Computer Science and Engineering")
        self.assertEqual(bl[1]["def_common"], 0)  # row printed after the page break still belongs to this block


class Rules(unittest.TestCase):
    def test_arithmetic_holds_on_synthetic(self):
        r = P.parse_text(page(block(ms=2, mino=1, ai=1, oi=0, state=(1, 1) + (0,) * 16)))
        self.assertEqual(r["problems"], [])
        self.assertEqual(r["blocks"][0]["vacant"], 4)

    def test_intake_is_separate_from_vacancy(self):
        b = P.parse_text(page(block(si=120, ms=3, state=(0, 0, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0))))["blocks"][0]
        self.assertEqual((b["si"], b["vacant"]), (120, 3))

    def test_institute_seats_not_in_vacancy(self):
        r = P.parse_text(page(block(ms=1, inst=18)))
        self.assertEqual(r["problems"], [])

    def test_wrong_vacant_reported_not_corrected(self):
        r = P.parse_text(page(block(ms=1, vac=5)))
        self.assertTrue(any("Vacant 5" in p for p in r["problems"]))
        self.assertEqual(r["blocks"][0]["vacant"], 5)

    def test_wrong_ms_reported(self):
        r = P.parse_text(page(block(ms=3)))
        self.assertTrue(any("MS Seats" in p for p in r["problems"]))

    def test_two_letter_choice_code(self):
        b = P.parse_text(page(block(code="0303337293LK", name="")))["blocks"][0]
        self.assertEqual(b["code"], "0303337293LK")

    def test_letter_suffix_code(self):
        b = P.parse_text(page(block(code="0430424550F")))["blocks"][0]
        self.assertEqual(b["code"], "0430424550F")

    def test_empty_tfws_code_with_zero_seats(self):
        r = P.parse_text(page(block(ews="Seats: 0").replace("Choice Code: Seats: 0", "Choice Code: Seats: 0")))
        b = r["blocks"][0]
        self.assertEqual((b["tfws_code"], b["tfws"]), ("", 0))
        self.assertEqual(r["problems"], [])

    def test_empty_tfws_code_with_seats_reported(self):
        r = P.parse_text(page(block(ews="Seats: 2")))
        self.assertTrue(any("TFWS seats 2" in p for p in r["problems"]))

    def test_wrapped_institute_name(self):
        t = block(instline=" 06182 - Sinhgad Technical Education Society, Narhe\n (Ambegaon)")
        self.assertEqual(P.parse_text(page(t))["blocks"][0]["inst_name"], "Sinhgad Technical Education Society, Narhe (Ambegaon)")

    def test_unknown_line_reported(self):
        r = P.parse_text(page("Something never seen before\n" + block()))
        self.assertTrue(any("Something never seen" in u[1] for u in r["unrecognised"]))

    def test_missing_page_reported(self):
        r = P.parse_text(page(block(), n=1, total=3))
        self.assertTrue(any("pages seen 1 of declared 3" in p for p in r["problems"]))

    def test_ghost_header_at_page_end(self):
        ghost = " Un-Aided Autonomous      Vacant CAP Seats:1\n\n"
        r = P.parse_text(page(block(ms=1)) + ghost + "STATE CET CELL , Mumbai   Page 2 of 3\n\f" + page(block(code="0100224210", ms=1), 3, 3))
        self.assertEqual(r["ghosts"], 1)
        self.assertEqual(len(r["blocks"]), 2)

    def test_lonely_header_reported(self):
        r = P.parse_text(page(" Un-Aided      Vacant CAP Seats:4\n"))
        self.assertTrue(any("without a course block" in p for p in r["problems"]))

    def test_duplicate_choice_code_reported(self):
        r = P.parse_text(page(block() + block()))
        self.assertTrue(any("duplicate choice codes" in p for p in r["problems"]))


class RealFiles(unittest.TestCase):
    """Run on the full archived PDFs if they are present (the GitHub workflow supplies them)."""
    def _run(self, env, blocks, pages):
        path = os.environ.get(env)
        if not path or not os.path.exists(path):
            self.skipTest(env + " not set")
        r = P.parse_text(P.pdf_to_text(path))
        self.assertEqual((len(r["blocks"]), r["pages"]), (blocks, pages))
        self.assertEqual(r["problems"], [])
        self.assertEqual(r["unrecognised"], [])

    def test_cap4_real(self): self._run("VACANCY_CAP4_PDF", 2335, (1013, 1013))
    def test_cap3_real(self): self._run("VACANCY_CAP3_PDF", 2330, (946, 946))


if __name__ == "__main__":
    unittest.main()
