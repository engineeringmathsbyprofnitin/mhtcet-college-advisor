"""Stage 7 tests: admission-year logic (SYNTHETIC evidence; no network). Run from repo root: python -m unittest tests/test_stage7_year.py -v"""
import sys, os, unittest
from datetime import date
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from ingestion import admission_year as A

def cut(y, rounds, scope="MH", **kw): return [dict(year=y, doc_type="cutoff", cap_round=r, scope=scope, **kw) for r in rounds]
def vac(y, rounds, **kw): return [dict(year=y, doc_type="vacancy_position", cap_round=r, scope=None, **kw) for r in rounds]

def evidence(years=None, menu=None, extra=()):
    years = years or {2026: ["I", "II", "III", "IV"], 2025: ["I", "II", "III", "IV"], 2024: ["I", "II", "III"], 2023: ["I", "II", "III"]}
    docs = []
    for y, rs in years.items(): docs += cut(y, rs)
    docs += list(extra)
    return {"menu_years": menu or list(years), "docs": docs}

class T(unittest.TestCase):
    def test_labels(self):
        self.assertEqual(A.label(2026), "2026-27"); self.assertEqual(A.label(2099), "2099-00"); self.assertEqual(A.label(1999), "1999-00")
    def test_parse(self):
        for s, y in [("2026-27", 2026), ("2026-2027", 2026), ("A.Y. 2026 \u2013 27", 2026), ("CAP 2025/26", 2025), ("Admission Process A.Y. 2026-2027", 2026), ("2099-00", 2099)]:
            self.assertEqual(A.parse_year_label(s), y, s)
        for s in ["2026-28", "2026", "hello", "", None, "12026-27", "2026-270"]: self.assertIsNone(A.parse_year_label(s), s)
    def test_previous_years_exclude_current(self):
        self.assertEqual(A.previous_years(2027), [2026, 2025, 2024]); self.assertEqual(A.previous_years(2026, 2), [2025, 2024])
    def test_current_cycle_confirmed(self):
        r = A.decide(evidence(extra=vac(2026, ["II", "III", "IV"])), date(2026, 10, 26))
        self.assertEqual(r["current_label"], "2026-27"); self.assertEqual(r["status"], "confirmed"); self.assertEqual(r["latest_cutoff_round"], "IV"); self.assertEqual(r["vacancy_round"], "IV")
        self.assertEqual([p["label"] for p in r["previous"]], ["2025-26", "2024-25", "2023-24"])      # the current year is never one of the three
        self.assertEqual(r["previous"][1]["cutoff_rounds"], ["I", "II", "III"])
    def test_year_follows_evidence_not_calendar_in_every_month(self):
        for m in range(1, 13):
            r = A.decide(evidence(), date(2026, m, 15))
            self.assertEqual(r["current_label"], "2026-27", m)       # no January or July boundary is assumed
    def test_between_cycles_keeps_previous_year_and_flags_it(self):
        for d in (date(2027, 1, 5), date(2027, 3, 1), date(2027, 5, 30)):
            r = A.decide(evidence(), d); self.assertEqual(r["current_label"], "2026-27"); self.assertEqual(r["status"], "previous_cycle_latest")
            self.assertTrue(any("2027-28" in w and "have been published yet" in w for w in r["warnings"]))
    def test_new_cycle_announced_without_documents_is_not_adopted(self):
        r = A.decide(evidence(menu=[2027, 2026, 2025, 2024, 2023]), date(2027, 2, 1))
        self.assertEqual(r["current_label"], "2026-27"); self.assertEqual(r["status"], "new_cycle_announced"); self.assertTrue(any("lists 2027-28" in w for w in r["warnings"]))
    def test_new_cycle_adopted_once_cutoffs_exist(self):
        ev = evidence(years={2027: ["I"], 2026: ["I", "II", "III", "IV"], 2025: ["I", "II", "III", "IV"], 2024: ["I", "II", "III"]}); r = A.decide(ev, date(2027, 7, 20))
        self.assertEqual(r["current_label"], "2027-28"); self.assertEqual(r["status"], "confirmed"); self.assertEqual(r["latest_cutoff_round"], "I")
        self.assertEqual([p["label"] for p in r["previous"]], ["2026-27", "2025-26", "2024-25"])
    def test_partial_current_round_uses_latest_available(self):
        r = A.decide(evidence(years={2026: ["I", "II"], 2025: ["I", "II", "III", "IV"], 2024: ["I"], 2023: ["I"]}), date(2026, 8, 1)); self.assertEqual(r["latest_cutoff_round"], "II")
    def test_no_evidence_means_unknown(self):
        r = A.decide({"menu_years": [2026], "docs": []}, date(2026, 10, 1)); self.assertIsNone(r["current_start_year"]); self.assertEqual(r["status"], "unknown")
        self.assertTrue(any("Keep the last validated data" in w for w in r["warnings"]))
    def test_unreachable_documents_are_not_evidence(self):
        docs = cut(2026, ["IV"], reachable=False) + cut(2025, ["III"], reachable=True)
        r = A.decide({"menu_years": [2026, 2025], "docs": docs}, date(2026, 10, 1)); self.assertEqual(r["current_label"], "2025-26")
        docs2 = cut(2026, ["IV"], reachable=None) ; self.assertEqual(A.decide({"menu_years": [2026], "docs": docs2}, date(2026, 10, 1))["current_label"], "2026-27")   # unknown is not 'unreachable'
    def test_found_but_unopenable_newer_year_is_reported_as_such(self):
        docs = cut(2026, ["IV"], reachable=False) + cut(2025, ["IV"], reachable=True)
        r = A.decide({"menu_years": [2026, 2025], "docs": docs}, date(2026, 10, 1))
        self.assertEqual(r["status"], "newer_documents_unreachable"); self.assertEqual(r["current_label"], "2025-26"); self.assertTrue(any("could not be opened" in w for w in r["warnings"]))
    def test_vacancy_round_rule_iv_then_iii_only(self):
        for found, want in [(["II", "III", "IV"], "IV"), (["II", "III"], "III"), (["I", "II"], None), ([], None)]:
            r = A.decide(evidence(extra=vac(2026, found)), date(2026, 10, 1)); self.assertEqual(r["vacancy_round"], want, found)
    def test_supplementary_and_other_vacancy_lists_do_not_count(self):
        extra = vac(2026, ["IV"], supplementary=True) + [dict(year=2026, doc_type="vacancy_after_cap", cap_round="IV", scope=None), dict(year=2026, doc_type="seat_matrix", cap_round=None)]
        self.assertIsNone(A.decide(evidence(extra=extra), date(2026, 10, 1))["vacancy_round"])
    def test_missing_previous_year_is_reported(self):
        r = A.decide(evidence(years={2026: ["IV"], 2025: ["IV"], 2023: ["III"]}), date(2026, 10, 1))
        self.assertFalse(r["previous"][1]["has_cutoffs"]); self.assertTrue(any("2024-25" in w for w in r["warnings"]))
    def test_portal_ahead_of_clock_is_flagged(self):
        r = A.decide(evidence(), date(2025, 6, 1)); self.assertTrue(any("ahead" in w for w in r["warnings"]))
    def test_result_is_json_friendly(self):
        import json; json.dumps(A.decide(evidence(), date(2026, 10, 1)))
if __name__ == "__main__": unittest.main()
