"""Stage 7 tests: document classifier and HTML link reader (fixtures modelled on the real portal pages)."""
import sys, os, unittest
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ingestion.classify import classify
from ingestion.html_extract import extract_links
from stage7_helpers import fixture
B = "https://cappublicdocs2026.blob.core.windows.net/documents/"

class Classify(unittest.TestCase):
    def c(self, text, name, ctx=None, py=2026): return classify(text, name if name.startswith("http") else B + name, ctx, py)
    def test_round_iv_vacancy_position_is_a_vacancy_position(self):
        r = self.c("Provisional Vacancy Position for CAP Round-IV", "FE2026_Vacancy_For_CAP4.pdf")
        self.assertEqual((r["doc_type"], r["cap_round"], r["year"]), ("vacancy_position", "IV", 2026)); self.assertIn("provisional", r["qualifiers"]); self.assertFalse(r["supplementary"])
    def test_acap_list_is_NOT_a_round_iv_vacancy_position(self):
        r = self.c("Vacant Seats after CAP IV (ACAP)", "FE2026_Vacancy_For_ACAP.pdf")
        self.assertEqual(r["doc_type"], "vacancy_after_cap"); self.assertIn("acap", r["qualifiers"])
        self.assertEqual(self.c("click here", "FE2026_Vacancy_For_ACAP.pdf")["doc_type"], "vacancy_after_cap")     # even if only the file name says so
    def test_court_order_new_institute_vacancy_is_supplementary(self):
        r = self.c("Provisional Vacancy Position for New Institute as per Court Order in CAP Round-III", "FE2026_Vacancy_For_CAP3_NewInstitute_CourtOder.pdf")
        self.assertEqual((r["doc_type"], r["cap_round"]), ("vacancy_position", "III")); self.assertTrue(r["supplementary"])
    def test_seat_matrix_is_never_a_vacancy(self):
        for t, n in [("Institute-wise Category-wise Seats (Seat Matrix) for CAP Round-I", "2026_fe_seatmatrix_V1.pdf"), ("View", "2024SeatMatrix.pdf")]:
            r = self.c(t, n, {"row_label": "2024-25", "col_headers": ["Seat Matrix"]}); self.assertEqual(r["doc_type"], "seat_matrix"); self.assertIsNone(r["cap_round"])
    def test_cutoffs_all_rounds_and_groups(self):
        cases = [("CAP Round I MH CutOff", "2026ENGG_CAP1_MH_CutOff_V1.pdf", "I", "MH"), ("CAP Round I AI Cutoff", "2026ENGG_CAP1_AI_CutOff.pdf", "I", "AI"),
                 ("CAP Round II MH Cut Off", "2026ENGG_CAP2_MH_CutOff.pdf", "II", "MH"), ("CAP Round III AI Cut Off", "2026ENGG_CAP3_AI_CutOff.pdf", "III", "AI"),
                 ("CAP Round IV MH Cut Off", "2026ENGG_CAP4_MH_CutOff.pdf", "IV", "MH"), ("Diploma Cut off CAP Round IV", "2026ENGG_CAP4_Diploma_CutOff.pdf", "IV", "DIPLOMA")]
        for t, n, rnd, sc in cases:
            r = self.c(t, n); self.assertEqual((r["doc_type"], r["cap_round"], r["scope"], r["year"]), ("cutoff", rnd, sc, 2026), t)
    def test_version_suffix_is_noted_not_confused_with_round(self):
        r = self.c("CAP Round I MH CutOff", "2026ENGG_CAP1_MH_CutOff_V1.pdf"); self.assertIn("version_1", r["qualifiers"]); self.assertEqual(r["cap_round"], "I")
    def test_round_numbers_are_not_confused_with_each_other(self):
        for word, want in [("Round-I", "I"), ("Round-II", "II"), ("Round-III", "III"), ("Round-IV", "IV"), ("Round 2", "II"), ("CAP-3", "III")]:
            self.assertEqual(classify("x CAP %s Cut Off" % word if "CAP" not in word else "x %s Cut Off" % word, "https://fe2026.mahacet.org/a.pdf")["cap_round"], want, word)
    def test_view_links_take_meaning_from_table_headings(self):
        ctx = {"row_label": "2025-26", "col_headers": ["CAP Round-IV Cut Off", "AI"]}
        r = classify("View", "https://fe2026.mahacet.org/2025/2025ENGG_CAP4_AI_CutOff.pdf", ctx, 2026)
        self.assertEqual((r["doc_type"], r["cap_round"], r["scope"], r["year"]), ("cutoff", "IV", "AI", 2025))
    def test_old_file_name_without_group_takes_group_from_table(self):
        r = classify("View", "https://fe2026.mahacet.org/2025/2025ENGG_CAP1_CutOff.pdf", {"row_label": "2025-26", "col_headers": ["CAP Round-I Cut Off", "MH"]}, 2026)
        self.assertEqual(r["scope"], "MH")
        r2 = classify("click", "https://fe2026.mahacet.org/2025/2025ENGG_CAP1_CutOff.pdf", None, 2026); self.assertIsNone(r2["scope"])      # not guessed
    def test_year_comes_from_the_row_not_from_the_page(self):
        r = classify("View", "https://fe2026.mahacet.org/2023/2023ENGG_CAP1_CutOff.pdf", {"row_label": "2023-24", "col_headers": ["CAP Round-I Cut Off", "MH"]}, 2026); self.assertEqual(r["year_label"], "2023-24")
    def test_year_conflict_is_flagged(self):
        r = classify("View", "https://fe2026.mahacet.org/2024/2024ENGG_CAP1_CutOff.pdf", {"row_label": "2023-24", "col_headers": ["CAP Round-I Cut Off"]}, 2026)
        self.assertIn("year_conflict", r["qualifiers"])
    def test_unrelated_links_stay_other(self):
        for t, u in [("Registration Manual (Eng)", "https://x.mahacet.org/44.pdf"), ("UM-Option Form Video", "https://youtu.be/abc"), ("Scrutiny Center List", "https://fe2026.mahacet.org/a.aspx")]:
            self.assertEqual(classify(t, u)["doc_type"], "other")
    def test_other_document_kinds(self):
        self.assertEqual(classify("Final Merit List", "https://x.mahacet.org/FE2026_PCMMH_MeritList_Final.pdf")["doc_type"], "merit_list")
        self.assertEqual(classify("Check Provisional Allotment Status (CAP Round-IV)", "https://fe2026.mahacet.org/a.aspx")["doc_type"], "allotment")
        self.assertEqual(classify("Information Brochure for Academic Year 2026-27", B + "Information_Brochure.pdf")["doc_type"], "brochure")
    def test_every_decision_has_reasons(self):
        self.assertTrue(self.c("CAP Round IV MH Cut Off", "2026ENGG_CAP4_MH_CutOff.pdf")["reasons"])

class Extract(unittest.TestCase):
    def test_cap_menu_is_told_apart_from_cet_menu(self):
        links = extract_links(fixture("cetcell_home.html"), "https://cetcell.mahacet.org/")
        cap = [l for l in links if l["menu_path"] and l["menu_path"][-1] == "CAP"]; cet = [l for l in links if l["menu_path"] and l["menu_path"][-1] == "CETs"]
        self.assertEqual([l["text"] for l in cap], ["2026-2027", "2025-2026", "2024-2025", "2023-2024", "2022-2023"]); self.assertEqual(len(cet), 3)
    def test_table_context_with_colspan_and_rowspan(self):
        links = extract_links(fixture("fe2026_home.html"), "https://fe2026.mahacet.org/StaticPages/HomePage")
        t = {l["href"]: l["table"] for l in links if l["table"]}
        u = "https://fe2026.mahacet.org/2025/2025ENGG_CAP4_AI_CutOff.pdf"; self.assertEqual(t[u]["row_label"], "2025-26"); self.assertEqual(t[u]["col_headers"], ["CAP Round-IV Cut Off", "AI"])
        u = "https://fe2026.mahacet.org/2023/2023ENGG_CAP3_CutOff_Diploma.pdf"; self.assertEqual(t[u]["col_headers"], ["CAP Round-III Cut Off", "Diploma"])
        u = "https://fe2026.mahacet.org/2024/2024SeatMatrix.pdf"; self.assertEqual(t[u]["col_headers"], ["Seat Matrix"])
    def test_placeholder_links_are_dropped(self):
        links = extract_links(fixture("fe2026_home.html"), "https://fe2026.mahacet.org/StaticPages/HomePage"); self.assertFalse([l for l in links if l["text"] == "-"])
    def test_relative_links_and_images_and_scripts(self):
        h = '<script>var a="<a href=/x>no</a>"</script><a href="/p/q.pdf"><img alt="NEW"></a><a href="mailto:a@b.c">m</a><a href="javascript:void(0)">j</a><a title="T" href="r.pdf"></a>'
        l = extract_links(h, "https://fe2026.mahacet.org/StaticPages/HomePage"); self.assertEqual([(x["href"], x["text"]) for x in l], [("https://fe2026.mahacet.org/p/q.pdf", "NEW"), ("https://fe2026.mahacet.org/StaticPages/r.pdf", "T")])
    def test_broken_html_does_not_crash(self):
        for h in ["<table><tr><td><a href='http://a.mahacet.org/x.pdf'>x", "<<>><li><li><a href=a>", "", None, "<table><table><tr><td>1<tr><td><a href='http://a.mahacet.org/y.pdf'>y</a></table>"]:
            extract_links(h, "https://cetcell.mahacet.org/")
    def test_real_menu_text_with_image_inside_link(self):
        l = extract_links('<li><a href="https://cetcell.mahacet.org/cap-_2026-27/">Admission Process A.Y. 2026-2027 <img src="n.gif"></a></li>', "https://cetcell.mahacet.org/"); self.assertEqual(l[0]["text"], "Admission Process A.Y. 2026-2027")
if __name__ == "__main__": unittest.main()
