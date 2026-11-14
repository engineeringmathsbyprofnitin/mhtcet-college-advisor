"""Stage 10c-2 tests: building the website tables from the real normalized data. Run: python -m unittest tests/test_stage10c2.py -v"""
import csv, gzip, json, os, sys, tempfile, unittest
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from ingestion import build_tables as B, eligibility as E
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
def row(**k):
    r = dict(year_label="2026-27", cap_round="IV", choice_code="0000111110", section=E.S_STATE, seat_code="GOPENS", home_university="", stage="I", merit_no="10", percentile="90.0000000", source_sha256="ab" * 32)
    r.update(k); return r
class Unit(unittest.TestCase):
    def test_hu_printed_wins(self): self.assertEqual(B.resolve_hu(row(section=E.S_HU_HU, home_university="Pune"), {}), ("Pune", "printed"))
    def test_hu_inferred_only_from_a_single_printed_value(self):
        self.assertEqual(B.resolve_hu(row(section=E.S_HU_HU), {"0000111110": {"Pune"}}), ("Pune", "inferred"))
        self.assertEqual(B.resolve_hu(row(section=E.S_HU_HU), {"0000111110": {"Pune", "Autonomous Institute"}}), ("", "unknown"))
        self.assertEqual(B.resolve_hu(row(section=E.S_HU_HU), {}), ("", "unknown"))
    def test_hu_not_needed_for_state_level(self): self.assertEqual(B.resolve_hu(row(), {})[1], "not_needed")
    def test_collapse_takes_lowest_percentile_and_never_makes_zero(self):
        c = B.collapse([row(stage="I", percentile="61.7000000", merit_no="5"), row(stage="VII", percentile="81.7000000", merit_no="9"), row(stage="II", percentile="")], {})
        self.assertEqual(len(c), 1); self.assertEqual((c[0]["cutoff_percentile"], c[0]["stage"], c[0]["merit_no"]), ("61.7000000", "I", "5"))
        self.assertEqual(B.collapse([row(percentile="")], {}), [])
    def test_printed_zero_percentile_is_excluded(self):
        self.assertEqual(B.collapse([row(percentile="0.0000000", merit_no="5776")], {}), [])
    def test_cutoff_ids_are_stable_and_distinct(self):
        a = B.collapse([row(seat_code="GOPENS"), row(seat_code="LOPENS")], {}); b = B.collapse([row(seat_code="LOPENS"), row(seat_code="GOPENS")], {})
        self.assertEqual({x["cutoff_id"] for x in a}, {x["cutoff_id"] for x in b}); self.assertEqual(len({x["cutoff_id"] for x in a}), 2)
class Real(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.d = tempfile.mkdtemp(); cls.rep = B.build(outdir=cls.d)
        cls.t = {}
        for n in ("current_cutoffs", "historical_cutoffs"):
            with gzip.open(os.path.join(cls.d, n + ".csv.gz"), "rt", newline="", encoding="utf-8") as f: cls.t[n] = list(csv.DictReader(f))
        for n in ("colleges", "branches", "seat_types", "source_documents"):
            with open(os.path.join(cls.d, n + ".csv"), newline="", encoding="utf-8") as f: cls.t[n] = list(csv.DictReader(f))
    def test_headers_match_schema(self):
        s = json.load(open(os.path.join(ROOT, "database", "schema.json")))["tables"]
        for n, rows in self.t.items(): self.assertEqual(list(rows[0]), [c["name"] for c in s[n]["columns"]], n)
    def test_plan_driven_rounds(self):
        self.assertEqual({r["admission_year"] for r in self.t["current_cutoffs"]}, {"2026-27"})
        self.assertEqual({r["cap_round"] for r in self.t["current_cutoffs"]}, {"I", "II", "III", "IV"})
        self.assertEqual({(r["admission_year"], r["cap_round"]) for r in self.t["historical_cutoffs"]}, {("2025-26", "IV"), ("2024-25", "III"), ("2023-24", "III")})
    def test_foreign_keys(self):
        br = {r["choice_code"]: r for r in self.t["branches"]}; col = {r["college_code"] for r in self.t["colleges"]}
        seats = {r["seat_type_code"] for r in self.t["seat_types"]}; docs = {r["doc_id"] for r in self.t["source_documents"]}
        for n in ("current_cutoffs", "historical_cutoffs"):
            for r in self.t[n]:
                self.assertIn(r["choice_code"], br); self.assertIn(r["seat_type_code"], seats); self.assertIn(r["source_doc_id"], docs)
        for b in br.values(): self.assertIn(b["college_code"], col)
    def test_unique_keys_and_no_blank_percentile(self):
        for n in ("current_cutoffs", "historical_cutoffs"):
            keys = [(r["choice_code"], r["admission_year"], r["cap_round"], r["seat_type_code"], r["section"], r["stage"]) for r in self.t[n]]
            self.assertEqual(len(keys), len(set(keys)), n); self.assertEqual(len({r["cutoff_id"] for r in self.t[n]}), len(keys))
            for r in self.t[n]: self.assertTrue(r["cutoff_percentile"]); self.assertGreater(float(r["cutoff_percentile"]), 0)
        self.assertEqual(self.rep["excluded_printed_zero_percentile_cells"], 16)
    def test_nothing_invented(self):
        # a district is either "Not available" or exactly what the college's official Institute Summary page prints (never guessed)
        ip = os.path.join(ROOT, "data", "normalized", "institutes", "institutes.csv")
        printed = {r["institute_code"]: r["district"] for r in csv.DictReader(open(ip, newline="", encoding="utf-8"))} if os.path.exists(ip) else {}
        for r in self.t["colleges"]: self.assertEqual(r["district"], printed.get(r["college_code"]) or "Not available", r["college_code"])
        self.assertTrue(all(r["is_synthetic"] == "FALSE" for rows in self.t.values() for r in rows if "is_synthetic" in r))
    def test_unknown_home_university_rows_exist_and_are_flagged(self):
        b = self.rep["home_university_basis"]; self.assertGreater(b["unknown"], 0)
        for n in ("current_cutoffs", "historical_cutoffs"):
            for r in self.t[n]:
                if r["home_university_basis"] == "unknown": self.assertEqual(r["home_university"], "")
if __name__ == "__main__": unittest.main()
