import csv, gzip, json, os, sys, tempfile, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from ingestion import build_vacancy as B, read_vacancy as R

PLAN = dict(ok=True, current_year="2026-27")


def vrow(cc, inst="01002", name="Civil Engineering", year="2026-27", rnd="IV", si="60", vac="3", sha="a" * 64):
    d = {k: "" for k in R.COLUMNS}
    d.update(portal_year=year, cap_round=rnd, source_file="v.pdf", source_sha256=sha, institute_code=inst, choice_code=cc, course_name=name, intake_si=si,
             ms_seats=vac, minority_seats="0", all_india_seats="0", institute_seats="0", orphan_inst_seats="0", orphan_non_inst_seats="0", vacant_cap_seats=vac,
             pwd_total="0", def_total="0", ews_seats="0", tfws_seats="0", grid_json="{}")
    return d


def make(tmp, vacancy=None, courses=(("0100219110", "01002", "Civil Engineering"),), cur=("0100219110",), fname=None):
    base = os.path.join(tmp, "n"); os.makedirs(os.path.join(base, "master")); os.makedirs(os.path.join(base, "tables")); os.makedirs(os.path.join(base, "vacancy"))
    with open(os.path.join(base, "master", "courses.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(["choice_code", "institute_code", "course_name"]); w.writerows(courses)
    with open(os.path.join(base, "tables", "branches.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(["choice_code"]); [w.writerow([c[0]]) for c in courses]
    with gzip.open(os.path.join(base, "tables", "current_cutoffs.csv.gz"), "wt", encoding="utf-8", newline="") as f:
        w = csv.writer(f); w.writerow(["choice_code"]); [w.writerow([c]) for c in cur]
    for name, rows in (vacancy or {}).items():
        with gzip.open(os.path.join(base, "vacancy", name), "wt", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=R.COLUMNS); w.writeheader(); w.writerows(rows)
    mp = os.path.join(tmp, "manifest.json"); json.dump({"files": {"a" * 64: {"urls": ["https://example.org/v.pdf"]}}}, open(mp, "w"))
    return base, mp


class Build(unittest.TestCase):
    def run_b(self, **kw):
        tmp = tempfile.mkdtemp(); base, mp = make(tmp, **kw)
        return B.build(base=base, plan=PLAN, manifest_path=mp), base

    def test_matches_and_writes(self):
        rep, base = self.run_b(vacancy={"2026-27_round-IV_vacancy.csv.gz": [vrow("0100219110")]})
        self.assertTrue(rep["ok"]); self.assertEqual((rep["rows"], rep["matched"], rep["round"]), (1, 1, "IV"))
        rows = list(csv.DictReader(open(os.path.join(base, "tables", "vacancy.csv"), encoding="utf-8")))
        self.assertEqual((rows[0]["intake_si"], rows[0]["vacant_cap_seats"], rows[0]["match"]), ("60", "3", "master"))
        self.assertEqual(rows[0]["source_doc_id"], "DOC-" + "a" * 16); self.assertEqual(rows[0]["source_url"], "https://example.org/v.pdf")

    def test_other_year_never_used_as_current(self):
        rep, base = self.run_b(vacancy={"2025-26_round-IV_vacancy.csv.gz": [vrow("0100219110", year="2025-26")]})
        self.assertTrue(rep["ok"]); self.assertIn("unavailable", rep["status"]); self.assertFalse(os.path.exists(os.path.join(base, "tables", "vacancy.csv")))
        self.assertTrue(any("ignored" in n for n in rep["notes"]))

    def test_no_table_removes_old_vacancy_file(self):
        tmp = tempfile.mkdtemp(); base, mp = make(tmp)
        open(os.path.join(base, "tables", "vacancy.csv"), "w").write("old")
        B.build(base=base, plan=PLAN, manifest_path=mp)
        self.assertFalse(os.path.exists(os.path.join(base, "tables", "vacancy.csv")))

    def test_round4_beats_round3(self):
        rep, _ = self.run_b(vacancy={"2026-27_round-III_vacancy.csv.gz": [vrow("0100219110", rnd="III", vac="9")],
                                     "2026-27_round-IV_vacancy.csv.gz": [vrow("0100219110", vac="3")]})
        self.assertEqual(rep["round"], "IV"); self.assertTrue(any("Round III table not used" in n for n in rep["notes"]))

    def test_round3_when_only_round3(self):
        rep, _ = self.run_b(vacancy={"2026-27_round-III_vacancy.csv.gz": [vrow("0100219110", rnd="III")]})
        self.assertEqual(rep["round"], "III")

    def test_institute_mismatch_fails_and_writes_nothing(self):
        rep, base = self.run_b(vacancy={"2026-27_round-IV_vacancy.csv.gz": [vrow("0100219110", inst="09999")]})
        self.assertFalse(rep["ok"]); self.assertFalse(os.path.exists(os.path.join(base, "tables", "vacancy.csv")))

    def test_new_course_kept_and_marked(self):
        rep, base = self.run_b(vacancy={"2026-27_round-IV_vacancy.csv.gz": [vrow("0100219110"), vrow("0476699510", inst="04766", name="AI and DS")]})
        self.assertTrue(rep["ok"]); self.assertEqual(len(rep["new_courses"]), 1)
        rows = {r["choice_code"]: r for r in csv.DictReader(open(os.path.join(base, "tables", "vacancy.csv"), encoding="utf-8"))}
        self.assertEqual(rows["0476699510"]["match"], "new_course")

    def test_duplicate_code_fails(self):
        rep, _ = self.run_b(vacancy={"2026-27_round-IV_vacancy.csv.gz": [vrow("0100219110"), vrow("0100219110")]})
        self.assertFalse(rep["ok"])

    def test_row_with_wrong_round_fails(self):
        rep, _ = self.run_b(vacancy={"2026-27_round-IV_vacancy.csv.gz": [vrow("0100219110", rnd="III")]})
        self.assertFalse(rep["ok"])

    def test_name_difference_only_reported(self):
        rep, _ = self.run_b(vacancy={"2026-27_round-IV_vacancy.csv.gz": [vrow("0100219110", name="Civil Engineering Some University")]})
        self.assertTrue(rep["ok"]); self.assertEqual(len(rep["name_differences"]), 1)

    def test_space_in_name_is_not_a_difference(self):
        rep, _ = self.run_b(courses=(("0100219110", "01002", "Production Engineering[Sandwich]"),),
                            vacancy={"2026-27_round-IV_vacancy.csv.gz": [vrow("0100219110", name="Production Engineering [Sandwich]")]})
        self.assertEqual(rep["name_differences"], [])

    def test_missing_vacancy_is_counted_not_zero(self):
        rep, base = self.run_b(courses=(("0100219110", "01002", "Civil Engineering"), ("0100224210", "01002", "CSE")), cur=("0100219110", "0100224210"),
                               vacancy={"2026-27_round-IV_vacancy.csv.gz": [vrow("0100219110")]})
        self.assertEqual(rep["current_courses_without_vacancy"], 1)
        rows = [r["choice_code"] for r in csv.DictReader(open(os.path.join(base, "tables", "vacancy.csv"), encoding="utf-8"))]
        self.assertNotIn("0100224210", rows)


class Real(unittest.TestCase):
    def test_real_data_consistent(self):
        n = B.N
        if not os.path.exists(os.path.join(n, "vacancy")) or not os.path.exists(os.path.join(n, "master", "courses.csv")): self.skipTest("no committed data")
        tmp = tempfile.mkdtemp()
        rep = B.build(base=n, outdir=tmp) if os.path.exists(os.path.join(n, "data_plan.json")) else None
        if rep is None: self.skipTest("no plan")
        self.assertTrue(rep["ok"], rep["problems"]); self.assertEqual(rep["institute_mismatch"], [])


if __name__ == "__main__":
    unittest.main()
