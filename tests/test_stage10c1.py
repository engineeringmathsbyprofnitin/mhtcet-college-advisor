"""Stage 10c-1 tests: the automatic data plan. Run: python -m unittest tests/test_stage10c1.py -v"""
import json, os, sys, unittest
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from ingestion import plan as P
def dec(cur_rounds, prev=None, status="confirmed", label="2026-27"):
    return {"current_label": label, "status": status, "current_cutoff_rounds": cur_rounds,
            "previous": prev if prev is not None else [{"label": "2025-26", "cutoff_rounds": ["I", "II", "III", "IV"]}, {"label": "2024-25", "cutoff_rounds": ["I", "II", "III"]}, {"label": "2023-24", "cutoff_rounds": ["I", "II", "III"]}]}
class T(unittest.TestCase):
    def test_real_decision(self):
        p = P.make_plan(json.load(open(P.DISCOVERY))["admission_year"])
        self.assertTrue(p["ok"]); self.assertEqual((p["current_year"], p["latest_round"], p["next_round_expected"]), ("2026-27", "IV", None))
        self.assertEqual([(x["year"], x["round"]) for x in p["required_lists"]], [("2026-27", "I"), ("2026-27", "II"), ("2026-27", "III"), ("2026-27", "IV"), ("2025-26", "IV"), ("2024-25", "III"), ("2023-24", "III")])
    def test_mid_cycle_next_round(self):
        p = P.make_plan(dec(["I", "II"])); self.assertEqual((p["latest_round"], p["next_round_expected"]), ("II", "III"))
        self.assertEqual([x["round"] for x in p["required_lists"] if x["role"] == "current"], ["I", "II"])
    def test_new_year_changes_everything_automatically(self):
        p = P.make_plan(dec(["I"], prev=[{"label": "2026-27", "cutoff_rounds": ["I", "II", "III", "IV"]}, {"label": "2025-26", "cutoff_rounds": ["I", "II", "III", "IV"]}, {"label": "2024-25", "cutoff_rounds": ["III"]}], label="2027-28"))
        self.assertEqual(p["current_year"], "2027-28"); self.assertEqual([x["year"] for x in p["required_lists"] if x["role"] == "history"], ["2026-27", "2025-26", "2024-25"])
        self.assertEqual(p["next_round_expected"], "II")
    def test_history_year_without_cutoffs_is_reported_not_invented(self):
        p = P.make_plan(dec(["I"], prev=[{"label": "2025-26", "cutoff_rounds": []}, {"label": "2024-25", "cutoff_rounds": ["III"]}, {"label": "2023-24", "cutoff_rounds": ["III"]}]))
        self.assertEqual(p["history_years_without_cutoffs"], ["2025-26"]); self.assertNotIn("2025-26", [x["year"] for x in p["required_lists"]])
    def test_year_not_established_keeps_last_data(self):
        for d in ({"current_label": None, "status": "unknown"}, dec([])):
            p = P.make_plan(d); self.assertFalse(p["ok"]); self.assertEqual(p["required_lists"], [])
    def test_previous_cycle_status_passes_through(self):
        self.assertEqual(P.make_plan(dec(["I", "II", "III", "IV"], status="previous_cycle_latest"))["year_status"], "previous_cycle_latest")
if __name__ == "__main__": unittest.main()
