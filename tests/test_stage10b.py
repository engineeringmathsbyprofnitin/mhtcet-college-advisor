"""Stage 10b tests: the cutoff validator finds the traps it is meant to find. Run: python -m unittest tests/test_stage10b.py -v"""
import csv, gzip, json, os, shutil, sys, tempfile, unittest
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from ingestion import validate_cutoffs as V, plan as P
DEC = {"current_label": "2026-27", "status": "confirmed", "current_cutoff_rounds": ["IV"],
       "previous": [{"label": "2025-26", "cutoff_rounds": ["I", "IV"]}, {"label": "2024-25", "cutoff_rounds": ["III"]}, {"label": "2023-24", "cutoff_rounds": ["III"]}]}
HDR = "year_label,cap_round,list_type,institute_code,institute_name,choice_code,course_name,status,home_university,section,seat_pool,allotted_to,stage,seat_code,merit_no,percentile,page,source_sha256".split(",")
AIH = "year_label,cap_round,list_type,sr_no,merit_no,score,choice_code,institute_code,institute_name,course_name,merit_exam,merit_exam_kind,ai_type,seat_type,page,note,source_sha256".split(",")
def mh(yr="2026-27", rd="IV", **k):
    r = dict(year_label=yr, cap_round=rd, list_type="MH", institute_code="00001", institute_name="X", choice_code="0000111110", course_name="C", status="Un-Aided",
             home_university="Pune", section="State Level", seat_pool="State Level", allotted_to="", stage="I", seat_code="GOPENS", merit_no="10", percentile="90.0000000", page="1", source_sha256="a")
    r.update(k); return r
def make(rows_by_file, ai=None):
    d = tempfile.mkdtemp()
    for sub in ("cutoffs_mh", "cutoffs_ai", "master"): os.makedirs(os.path.join(d, sub))
    def w(path, hdr, rows):
        with open(path, "w", newline="") as f: x = csv.DictWriter(f, fieldnames=hdr); x.writeheader(); x.writerows(rows)
    w(os.path.join(d, "master", "colleges.csv"), ["institute_code", "home_university_latest"], [dict(institute_code="00001", home_university_latest="Pune")])
    w(os.path.join(d, "master", "courses.csv"), ["choice_code"], [dict(choice_code="0000111110")])
    w(os.path.join(d, "master", "seat_codes.csv"), ["code"], [dict(code="GOPENS")])
    w(os.path.join(d, "master", "home_universities.csv"), ["home_university"], [dict(home_university="Pune")])
    for fn, rows in rows_by_file.items():
        with gzip.open(os.path.join(d, "cutoffs_mh", fn), "wt", newline="") as f: x = csv.DictWriter(f, fieldnames=HDR); x.writeheader(); x.writerows(rows)
    for fn, rows in (ai or {}).items():
        with gzip.open(os.path.join(d, "cutoffs_ai", fn), "wt", newline="") as f: x = csv.DictWriter(f, fieldnames=AIH); x.writeheader(); x.writerows(rows)
    return d
def good_years():
    return {"a.csv.gz": [mh("2026-27", "IV")], "b.csv.gz": [mh("2025-26", "IV")], "c.csv.gz": [mh("2024-25", "III")], "d.csv.gz": [mh("2023-24", "III")]}
def ai_row(yr, rd, score="99.0"):
    return dict(year_label=yr, cap_round=rd, list_type="AI", sr_no="1", merit_no="1", score=score, choice_code="0000111110", institute_code="00001", institute_name="X",
                course_name="C", merit_exam="MHT-CET", merit_exam_kind="MHT-CET", ai_type="MH to AI", seat_type="AI", page="1", note="", source_sha256="a")
def run(files, ai=None):
    base_ai = {"ai%d.csv.gz" % i: [ai_row(y, r)] for i, (y, r) in enumerate([("2026-27", "IV"), ("2025-26", "IV"), ("2024-25", "III"), ("2023-24", "III")])}
    base_ai.update(ai or {})
    d = make(files, base_ai)
    try: return V.validate(d, plan=P.make_plan(DEC))
    finally: shutil.rmtree(d)

class T(unittest.TestCase):
    def test_clean_data_passes(self): self.assertTrue(run(good_years())["ok"])
    def test_bad_percentile_and_blank(self):
        f = good_years(); f["a.csv.gz"] = [mh(percentile="123.0000000"), mh(percentile="", merit_no="11"), mh(percentile="9.5", merit_no="12")]
        e = run(f)["errors"]; self.assertEqual(e.get("PERCENTILE_OUT_OF_RANGE"), 1); self.assertEqual(e.get("BLANK_PERCENTILE"), 1); self.assertEqual(e.get("BAD_PERCENTILE_FORMAT"), 1)
    def test_code_consistency(self):
        f = good_years(); f["a.csv.gz"] = [mh(choice_code="9999911110"), mh(seat_code="ZZZ", merit_no="11"), mh(institute_code="77777", choice_code="7777711110", merit_no="12")]
        e = run(f)["errors"]
        self.assertEqual(e.get("CHOICE_CODE_INSTITUTE_MISMATCH"), 1); self.assertEqual(e.get("SEAT_CODE_NOT_IN_MASTER"), 1)
        self.assertEqual(e.get("INSTITUTE_NOT_IN_MASTER"), 1); self.assertGreaterEqual(e.get("COURSE_NOT_IN_MASTER", 0), 2)
    def test_conflicting_merit_numbers_are_counted_not_fixed(self):
        f = good_years(); f["a.csv.gz"] = [mh(percentile="90.0000000"), mh(seat_code="GOPENS", stage="II", percentile="91.0000000")]
        r = run(f); self.assertTrue(r["ok"]); self.assertEqual(r["warnings"]["CONFLICTING_MERIT_PERCENTILE"], 1)
    def test_percentile_rising_with_merit_number_is_reported(self):
        f = good_years(); f["a.csv.gz"] = [mh(merit_no="10", percentile="90.0000000"), mh(merit_no="20", percentile="91.0000000")]
        w = run(f)["warnings"]; self.assertEqual(w["PERCENTILE_RISES_WITH_MERIT_NO"], 1); self.assertEqual(w["PERCENTILE_RISES_OVER_HALF_POINT"], 1)
    def test_blank_home_university_classified(self):
        f = good_years(); f["a.csv.gz"] = [mh(home_university="")]            # course prints "Pune" in the other lists
        w = run(f)["warnings"]; self.assertEqual(w["BLANK_HOME_UNIVERSITY_ROWS_COURSE_PRINTS_ONE_VALUE_ELSEWHERE"], 1)
    def test_year_rules_follow_the_plan(self):
        f = good_years(); del f["d.csv.gz"]; self.assertIn("PLANNED_LIST_NOT_PARSED", run(f)["errors"])
        f = good_years(); f["a.csv.gz"] = [mh("2026-27", "III")]; self.assertIn("PLANNED_LIST_NOT_PARSED", run(f)["errors"])
        f = good_years(); f["e.csv.gz"] = [mh("2021-22", "III")]; self.assertIn("YEAR_OUTSIDE_PLAN", run(f)["errors"])
    def test_ai_blank_score_kept_and_reported(self):
        ai = {"x.csv.gz": [dict(year_label="2026-27", cap_round="IV", list_type="AI", sr_no="1", merit_no="1", score="", choice_code="0000111110", institute_code="00001",
                                institute_name="X", course_name="C", merit_exam="MHT-CET", merit_exam_kind="MHT-CET", ai_type="MH to AI", seat_type="AI", page="1", note="", source_sha256="a")]}
        self.assertEqual(run(good_years(), ai)["warnings"]["AI_BLANK_SCORE_KEPT_BLANK"], 1)
    def test_real_data_has_no_errors_and_expected_latest_rounds(self):
        r = V.validate()
        self.assertEqual(r["errors"], {}); self.assertEqual(r["parsed_rounds_per_year"], {"2023-24": ["III"], "2024-25": ["III"], "2025-26": ["IV"], "2026-27": ["I", "II", "III", "IV"]})
        self.assertEqual(sum(l["rows"] for l in r["lists"]), 148004)
    def test_schema_v04_columns(self):
        s = json.load(open(os.path.join(V.ROOT, "database", "schema.json")))
        self.assertIn(s["schema_version"], ("0.4", "0.5"))
        for t in ("historical_cutoffs", "current_cutoffs"):
            names = [c["name"] for c in s["tables"][t]["columns"]]
            for c in ("section", "stage", "merit_no", "merit_exam"): self.assertIn(c, names)
            self.assertIn("section", s["tables"][t]["unique"])
if __name__ == "__main__": unittest.main()
