"""Stage 8 tests: which documents are selected for download (simulated site, no network)."""
import sys, os, unittest, copy
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stage8_helpers import *
from ingestion.policy import select_documents

class T(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.report = make_report(Docs()); cls.sel, cls.dfr = select_documents(cls.report)
    def test_exactly_the_seventeen_needed_files(self):
        self.assertEqual(len(self.sel), 17); self.assertEqual(len(self.dfr), 24); self.assertEqual(len({d["id"] for d in self.sel}), 17)
    def test_current_year_cutoffs_all_rounds_both_groups(self):
        got = sorted((d["cap_round"], d["scope"]) for d in self.sel if d["year"] == 2026 and d["doc_type"] == "cutoff")
        self.assertEqual(got, sorted((r, s) for r in ("I", "II", "III", "IV") for s in ("MH", "AI")))
    def test_vacancy_only_round_iv_and_iii(self):
        self.assertEqual(sorted(d["cap_round"] for d in self.sel if d["doc_type"] == "vacancy_position"), ["III", "IV"])
    def test_look_alike_and_special_lists_are_not_selected(self):
        urls = " ".join(d["url"] for d in self.sel)
        for bad in ("ACAP", "CourtOder", "NewInstitute", "Diploma", "Vacancy_For_CAP2"): self.assertNotIn(bad, urls)
        self.assertFalse([d for d in self.sel if d["doc_type"] in ("vacancy_after_cap",) or d["supplementary"] or d["scope"] == "DIPLOMA"])
    def test_previous_years_get_only_the_final_round_per_group(self):
        prev = sorted((d["year_label"], d["scope"], d["cap_round"]) for d in self.sel if d["year"] < 2026)
        self.assertEqual(prev, [("2023-24", "AI", "III"), ("2023-24", "MH", "III"), ("2024-25", "AI", "III"), ("2024-25", "MH", "III"), ("2025-26", "AI", "IV"), ("2025-26", "MH", "IV")])
    def test_only_the_current_seat_matrix(self):
        sm = [d for d in self.sel if d["doc_type"] == "seat_matrix"]; self.assertEqual([d["year"] for d in sm], [2026])
    def test_every_choice_states_its_reason(self):
        self.assertTrue(all(d["why"] for d in self.sel)); self.assertTrue(all(d["why"] == "not needed yet" for d in self.dfr))
    def test_order_is_stable(self):
        again, _ = select_documents(self.report); self.assertEqual([d["id"] for d in again], [d["id"] for d in self.sel])
    def test_no_current_year_selects_nothing(self):
        r = copy.deepcopy(self.report); r["admission_year"]["current_start_year"] = None; self.assertEqual(select_documents(r), ([], []))
    def test_unreachable_documents_are_never_selected(self):
        r = copy.deepcopy(self.report)
        for d in r["documents"]:
            if d["year"] == 2026 and d["doc_type"] == "cutoff" and d["cap_round"] == "IV": d["verification"]["reachable"] = False
        sel, _ = select_documents(r); self.assertFalse([d for d in sel if d["year"] == 2026 and d["cap_round"] == "IV" and d["doc_type"] == "cutoff"])
    def test_vacancy_falls_back_to_round_iii_then_nothing_never_to_round_ii(self):
        r = copy.deepcopy(self.report)
        r["documents"] = [d for d in r["documents"] if not (d["doc_type"] == "vacancy_position" and d["cap_round"] == "IV")]
        self.assertEqual([d["cap_round"] for d in select_documents(r)[0] if d["doc_type"] == "vacancy_position"], ["III"])
        r["documents"] = [d for d in r["documents"] if not (d["doc_type"] == "vacancy_position" and d["cap_round"] == "III")]
        self.assertEqual([d for d in select_documents(r)[0] if d["doc_type"] == "vacancy_position"], [])
    def test_final_round_is_worked_out_separately_per_group(self):
        r = copy.deepcopy(self.report)
        r["documents"] = [d for d in r["documents"] if not (d["year_label"] == "2025-26" and d["scope"] == "AI" and d["cap_round"] == "IV")]
        got = {(d["scope"], d["cap_round"]) for d in select_documents(r)[0] if d["year"] == 2025 and d["doc_type"] == "cutoff"}; self.assertEqual(got, {("MH", "IV"), ("AI", "III")})
if __name__ == "__main__": unittest.main()
