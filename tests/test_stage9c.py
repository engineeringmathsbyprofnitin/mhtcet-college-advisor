"""Stage 9c tests: master tables, seat-code parts, the 'needed files' command, the summary writer and the reading workflow.
SYNTHETIC data only. Run: python -m unittest tests/test_stage9c.py -v"""
import csv, gzip, io, json, os, sys, tempfile, unittest
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from ingestion import master as M, archive as AR, reports as RP, parse_mh, parse_ai
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
try: import yaml
except ImportError: yaml = None

def mh_row(year="2026-27", rnd="IV", inst="01002", iname="Government College of Engineering, Amravati", code="0100219110", cname="Civil Engineering", status="Government Autonomous", uni="Autonomous Institute", seat="GOPENS"):
    return {"year_label": year, "cap_round": rnd, "list_type": "MH", "institute_code": inst, "institute_name": iname, "choice_code": code, "course_name": cname, "status": status, "home_university": uni,
            "section": "State Level", "seat_pool": "State Level", "allotted_to": "", "stage": "I", "seat_code": seat, "merit_no": "1", "percentile": "99.0000000", "page": "1", "source_sha256": "x"}
def ai_row(year="2026-27", rnd="IV", inst="01002", iname="Government College of Engineering, Amravati", code="0100219110", cname="Civil Engineering", seat="AI"):
    return {"year_label": year, "cap_round": rnd, "list_type": "AI", "sr_no": "1", "merit_no": "5", "score": "90.0", "choice_code": code, "institute_code": inst, "institute_name": iname, "course_name": cname,
            "merit_exam": "JEE", "merit_exam_kind": "JEE", "ai_type": "AI to AI", "seat_type": seat, "page": "1", "note": "", "source_sha256": "x"}
def put(folder, name, rows, cols):
    os.makedirs(folder, exist_ok=True); buf = io.StringIO(); w = csv.DictWriter(buf, fieldnames=cols, lineterminator="\n"); w.writeheader(); w.writerows(rows)
    with gzip.open(os.path.join(folder, name), "wt", encoding="utf-8", newline="") as fh: fh.write(buf.getvalue())
def make(mh_rows, ai_rows=()):
    d = tempfile.mkdtemp(); mh, ai = os.path.join(d, "mh"), os.path.join(d, "ai")
    by = {}
    for r in mh_rows: by.setdefault((r["year_label"], r["cap_round"]), []).append(r)
    for (y, rd), rows in by.items(): put(mh, "%s_round-%s_MH.csv.gz" % (y, rd), rows, parse_mh.COLUMNS)
    by = {}
    for r in ai_rows: by.setdefault((r["year_label"], r["cap_round"]), []).append(r)
    for (y, rd), rows in by.items(): put(ai, "%s_round-%s_AI.csv.gz" % (y, rd), rows, parse_ai.COLUMNS)
    return d, mh, ai

class SeatCodes(unittest.TestCase):
    def test_every_form_seen_in_the_real_lists(self):
        P = M.parse_seat_code
        self.assertEqual({k: P("GOPENS")[k] for k in ("family", "gender_scope", "category", "level_letter", "level_meaning")}, {"family": "regular", "gender_scope": "General", "category": "OPEN", "level_letter": "S", "level_meaning": "State Level"})
        self.assertEqual((P("LSCH")["gender_scope"], P("LSCH")["category"], P("LSCH")["level_meaning"]), ("Ladies", "SC", "Home University"))
        self.assertEqual((P("GNT1O")["category"], P("GNT1O")["level_meaning"]), ("NT1", "Other Than Home University")); self.assertEqual(P("LSEBCO")["category"], "SEBC")
        d = P("DEFRSEBCS"); self.assertEqual((d["family"], d["variant"], d["category"], d["level_letter"]), ("defence", "R", "SEBC", "S"))
        w = P("PWDOBCH"); self.assertEqual((w["family"], w["variant"], w["category"], w["level_letter"]), ("pwd", "", "OBC", "H")); self.assertEqual(P("PWDRSEBCS")["variant"], "R")
        for code, fam in (("TFWS", "tfws"), ("EWS", "ews"), ("MI", "minority"), ("ORPHANI", "orphan"), ("ORPHANN", "orphan"), ("ORPHAN", "orphan"), ("ORPHAN2", "orphan"), ("PHCH", "phc"), ("PHCOBCH", "phc"), ("DEFO", "defence"), ("AI", "all_india_seat")): self.assertEqual(P(code)["family"], fam, code)
    def test_unknown_codes_are_kept_and_flagged_never_interpreted(self):
        p = M.parse_seat_code("XYZ12"); self.assertEqual((p["family"], p["code"], p["category"], p["level_meaning"]), ("other", "XYZ12", "", ""))
    def test_only_the_legend_defined_letters_get_a_meaning(self):
        self.assertEqual(M.parse_seat_code("ORPHANI")["level_meaning"], ""); self.assertEqual(M.parse_seat_code("TFWS")["level_meaning"], ""); self.assertEqual(M.parse_seat_code("DEFRSEBCS")["variant"], "R")

class MasterTables(unittest.TestCase):
    def test_basic_college_and_course(self):
        d, mh, ai = make([mh_row(), mh_row(seat="GSCS")]); t, s, p = M.build(mh, ai); self.assertEqual(p, [])
        c = t["colleges"][0]; self.assertEqual((c["institute_code"], c["institute_name"], c["status_latest"], c["home_university_latest"], c["first_year"], c["last_year"], c["courses"], c["lists"]), ("01002", "Government College of Engineering, Amravati", "Government Autonomous", "Autonomous Institute", "2026-27", "2026-27", 1, "MH"))
        k = t["courses"][0]; self.assertEqual((k["choice_code"], k["base_code"], k["code_suffix"], k["institute_code"], k["course_name"], k["name_source"]), ("0100219110", "0100219110", "", "01002", "Civil Engineering", "State list"))
        self.assertEqual((s["colleges"], s["courses"], s["seat_codes"]), (1, 1, 2))
    def test_facts_the_lists_do_not_contain_stay_blank(self):
        t, _, _ = M.build(*make([mh_row()])[1:]); self.assertEqual((t["colleges"][0]["district"], t["colleges"][0]["city"]), ("", ""))
    def test_the_latest_year_and_round_win(self):
        rows = [mh_row("2025-26", "IV", iname="Old Name", status="Un-Aided"), mh_row("2026-27", "III", iname="Middle Name"), mh_row("2026-27", "IV", iname="Newest Name")]
        t, _, p = M.build(*make(rows)[1:]); c = t["colleges"][0]; self.assertEqual((c["institute_name"], c["name_changes"], c["first_year"], c["last_year"]), ("Newest Name", 2, "2025-26", "2026-27"))
        hist = [(h["year_label"], h["institute_name"]) for h in t["college_name_history"]]; self.assertEqual(hist, [("2025-26", "Old Name"), ("2026-27", "Middle Name"), ("2026-27", "Newest Name")])
        self.assertTrue(any("2 different names" not in x for x in p) or p == [])
    def test_two_names_in_the_same_list_are_a_reported_problem(self):
        t, s, p = M.build(*make([mh_row(iname="Name A"), mh_row(iname="Name B", seat="GSCS")])[1:]); self.assertTrue(any("2 different names" in x for x in p)); self.assertEqual(s["problems"], len(p))
    def test_course_renames_are_kept_in_a_history(self):
        t, s, _ = M.build(*make([mh_row("2024-25", "III", cname="Computer Engg"), mh_row("2026-27", "IV", cname="Computer Engineering")])[1:])
        self.assertEqual(t["courses"][0]["course_name"], "Computer Engineering"); self.assertEqual(t["courses"][0]["name_changes"], 1); self.assertEqual(s["courses_with_name_changes"], 1); self.assertEqual(len(t["course_name_history"]), 2)
    def test_a_course_only_in_the_all_india_list_is_added_with_its_source_noted(self):
        t, s, _ = M.build(*make([mh_row()], [ai_row(), ai_row(code="0100219120", cname="Mechanical Engg")])[1:])
        k = {c["choice_code"]: c for c in t["courses"]}; self.assertEqual(k["0100219120"]["name_source"], "All India list (name may be shortened)"); self.assertEqual(k["0100219110"]["name_source"], "State list"); self.assertEqual(s["courses_only_in_all_india_list"], 1)
        self.assertEqual({c["lists"] for c in t["colleges"]}, {"AI+MH"})
    def test_state_list_names_are_never_replaced_by_shortened_all_india_names(self):
        t, _, _ = M.build(*make([mh_row(cname="Computer Science and Engineering (Artificial Intelligence)")], [ai_row(cname="Computer Science and Engineering(Artificial")])[1:]); self.assertEqual(t["courses"][0]["course_name"], "Computer Science and Engineering (Artificial Intelligence)")
    def test_blank_all_india_rows_are_ignored_for_courses(self):
        t, s, _ = M.build(*make([mh_row()], [ai_row(code="")])[1:]); self.assertEqual(len(t["courses"]), 1)
    def test_a_course_code_that_does_not_belong_to_its_institute_is_reported(self):
        _, _, p = M.build(*make([mh_row(code="0200219110")])[1:]); self.assertTrue(any("does not start with its institute code" in x for x in p))
    def test_code_suffix_letters_are_split_off(self):
        t, _, _ = M.build(*make([mh_row(inst="03033", code="0303337293LK")])[1:]); self.assertEqual((t["courses"][0]["base_code"], t["courses"][0]["code_suffix"]), ("0303337293", "LK"))
    def test_an_unrecognised_seat_code_is_a_problem_but_is_kept(self):
        t, s, p = M.build(*make([mh_row(seat="WEIRD1")])[1:]); self.assertEqual(s["seat_codes_not_recognised"], 1); self.assertTrue(any("WEIRD1" in x for x in p)); self.assertEqual(t["seat_codes"][0]["code"], "WEIRD1")
    def test_home_universities_are_listed_with_counts_and_kinds(self):
        rows = [mh_row(), mh_row(inst="03001", code="0300119110", iname="B College", status="Un-Aided", uni="Mumbai University"), mh_row(inst="03002", code="0300219110", iname="C College", status="Un-Aided", uni="Mumbai University")]
        t, s, _ = M.build(*make(rows)[1:]); u = {x["home_university"]: x for x in t["home_universities"]}
        self.assertEqual((u["Mumbai University"]["colleges"], u["Mumbai University"]["kind"]), (2, "university")); self.assertEqual(u["Autonomous Institute"]["kind"], "autonomous-institute marker"); self.assertEqual(s["home_universities"], 2)
    def test_seat_codes_record_where_and_when_they_appear(self):
        t, _, _ = M.build(*make([mh_row(seat="GOPENS")], [ai_row(seat="GNT1H"), ai_row(seat="AI")])[1:]); s = {x["code"]: x for x in t["seat_codes"]}
        self.assertEqual(s["GOPENS"]["lists"], "MH"); self.assertEqual(s["GNT1H"]["lists"], "AI"); self.assertEqual(s["AI"]["family"], "all_india_seat")

class Files(unittest.TestCase):
    def test_output_is_repeatable_and_exit_codes_are_honest(self):
        d, mh, ai = make([mh_row()]); a, b = os.path.join(d, "a"), os.path.join(d, "b")
        self.assertEqual(M.main(["--mh-dir", mh, "--ai-dir", ai, "--out", a, "--now", "t"]), 0); M.main(["--mh-dir", mh, "--ai-dir", ai, "--out", b, "--now", "t"])
        for f in sorted(os.listdir(a)): self.assertEqual(open(os.path.join(a, f), "rb").read(), open(os.path.join(b, f), "rb").read(), f)
        self.assertEqual(sorted(os.listdir(a)), ["college_name_history.csv", "colleges.csv", "course_name_history.csv", "courses.csv", "home_universities.csv", "master_report.json", "seat_codes.csv"])
        self.assertEqual(M.main(["--mh-dir", os.path.join(d, "nothing"), "--out", os.path.join(d, "c")]), 2)
        d2, mh2, ai2 = make([mh_row(seat="WEIRD1")]); self.assertEqual(M.main(["--mh-dir", mh2, "--ai-dir", ai2, "--out", os.path.join(d2, "o")]), 4)
    def test_report_lists_the_summary_and_problems(self):
        d, mh, ai = make([mh_row(seat="WEIRD1")]); M.main(["--mh-dir", mh, "--ai-dir", ai, "--out", os.path.join(d, "o")]); r = json.load(open(os.path.join(d, "o", "master_report.json"))); self.assertEqual(r["problem_count"], 1); self.assertIn("summary", r)

class NeededFiles(unittest.TestCase):
    def manifest(self):
        m = AR.empty_manifest()
        def add(i, scope, typ, up=True, rnd="IV"):
            sha = "%064d" % i; m["documents"]["d%d" % i] = {"doc_type": typ, "scope": scope, "current_sha256": sha}; m["files"][sha] = {"sha256": sha, "asset_name": "%016d__f.pdf" % i, "release_tag": "raw-2026-27", "uploaded": up}
        add(1, "MH", "cutoff"); add(2, "AI", "cutoff"); add(3, None, "vacancy_position"); add(4, None, "seat_matrix"); add(5, "MH", "cutoff", up=False); add(6, "DIPLOMA", "cutoff"); return m
    def test_only_stored_state_and_all_india_cutoff_files(self):
        got = AR.needed_downloads(self.manifest()); self.assertEqual([a for _, a, _ in got], ["%016d__f.pdf" % 1, "%016d__f.pdf" % 2])
    def test_scopes_can_be_chosen(self): self.assertEqual(len(AR.needed_downloads(self.manifest(), ("MH",))), 1)
    def test_command_prints_tag_asset_sha_lines(self):
        d = tempfile.mkdtemp(); p = os.path.join(d, "m.json"); AR.save_manifest(p, self.manifest()); buf = io.StringIO(); old = sys.stdout; sys.stdout = buf
        try: self.assertEqual(AR.main(["needed", "--manifest", p]), 0)
        finally: sys.stdout = old
        lines = buf.getvalue().splitlines(); self.assertEqual(len(lines), 2); self.assertTrue(all(l.count("|") == 2 and l.startswith("raw-2026-27|") for l in lines))
    def test_nothing_stored_means_nothing_needed(self): self.assertEqual(AR.needed_downloads(AR.empty_manifest()), [])

class Summary(unittest.TestCase):
    def folder(self, mh_ok=True, ai_ok=True, master_problems=0):
        d = tempfile.mkdtemp()
        for sub, name, ok, key in (("cutoffs_mh", "parse_report_mh.json", mh_ok, "cells"), ("cutoffs_ai", "parse_report_ai.json", ai_ok, "rows")):
            os.makedirs(os.path.join(d, sub)); json.dump({"all_ok": ok, "files": [{"year_label": "2026-27", "cap_round": "IV", key: 14764, "complete": ok, "problem_count": 0 if ok else 3}]}, open(os.path.join(d, sub, name), "w"))
        os.makedirs(os.path.join(d, "master")); json.dump({"summary": {"colleges": 403, "courses": 2511, "seat_codes": 105, "home_universities": 14}, "problem_count": master_problems, "problems": ["p"] * master_problems}, open(os.path.join(d, "master", "master_report.json"), "w")); return d
    def test_good_run(self):
        md, ok = RP.markdown_summary(self.folder()); self.assertTrue(ok); self.assertIn("14,764", md); self.assertIn("403 colleges", md); self.assertIn("everything complete, no problems", md)
    def test_any_problem_makes_the_overall_result_not_ok(self):
        for kw in ({"mh_ok": False}, {"ai_ok": False}, {"master_problems": 2}):
            md, ok = RP.markdown_summary(self.folder(**kw)); self.assertFalse(ok, kw); self.assertIn("NOT OK - the previous data was kept", md)
    def test_missing_reports_are_not_ok(self): md, ok = RP.markdown_summary(tempfile.mkdtemp()); self.assertFalse(ok); self.assertIn("report missing", md)
    def test_summary_goes_to_the_run_page_and_exit_code_follows(self):
        d = self.folder(); sm = os.path.join(d, "sum.md"); os.environ["GITHUB_STEP_SUMMARY"] = sm
        try: self.assertEqual(RP.main([d]), 0); self.assertIn("Reading the archived cutoff lists", open(sm).read()); self.assertEqual(RP.main([self.folder(mh_ok=False)]), 4)
        finally: del os.environ["GITHUB_STEP_SUMMARY"]

@unittest.skipIf(yaml is None, "PyYAML not installed")
class Workflow(unittest.TestCase):
    def setUp(self):
        with open(os.path.join(ROOT, ".github", "workflows", "parse-documents.yml"), encoding="utf-8") as f: self.text = f.read()
        self.w = yaml.safe_load(self.text); self.steps = {s.get("name", s.get("uses", "")): s for s in self.w["jobs"]["read"]["steps"]}; self.names = list(self.steps)
    def i(self, prefix): return [k for k, n in enumerate(self.names) if n.startswith(prefix)][0]
    def test_runs_by_hand_and_weekly_after_the_archive_job(self):
        on = self.w.get("on", self.w.get(True)); self.assertIn("workflow_dispatch", on); self.assertEqual(on["schedule"][0]["cron"].split()[:2], ["47", "4"])
    def test_safe_permissions_and_only_the_built_in_token(self):
        import re; self.assertEqual(self.w["permissions"], {"contents": "write"}); self.assertEqual(sorted(set(re.findall(r"secrets\.([A-Za-z_]+)", self.text))), ["GITHUB_TOKEN"]); self.assertNotIn("pull_request_target", self.text)
    def test_steps_run_in_order(self):
        order = ["Install the PDF tool", "Self-tests", "Fetch the archived PDFs", "Read the State", "Read the All India", "Build the master", "Summary", "Replace the normalized", "Save the normalized"]
        idx = [self.i(p) for p in order]; self.assertEqual(idx, sorted(idx))
    def test_new_tables_are_built_in_a_temporary_folder_and_replace_the_old_ones_only_on_success(self):
        for p in ("Read the State", "Read the All India", "Build the master"): self.assertIn("build/normalized", self.steps[self.names[self.i(p)]]["run"]); self.assertNotIn("--out data/normalized", self.steps[self.names[self.i(p)]]["run"])
        for p in ("Replace the normalized", "Save the normalized"): self.assertEqual(self.steps[self.names[self.i(p)]].get("if"), "success()")
        self.assertEqual(self.steps[self.names[self.i("Summary")]].get("if"), "always()")
    def test_pdfs_are_fetched_from_the_releases_and_never_committed(self):
        run = self.steps[self.names[self.i("Fetch the archived PDFs")]]["run"]; self.assertIn("gh release download", run); self.assertIn("ingestion.archive needed", run)
        save = self.steps[self.names[self.i("Save the normalized")]]["run"]; self.assertIn("git add data/normalized", save); self.assertNotIn("data/raw/files", save); self.assertIn("git pull --rebase", save)
    def test_selftests_include_the_stage9_tests(self):
        run = self.steps[self.names[self.i("Self-tests")]]["run"]
        for t in ("test_stage9a", "test_stage9b", "test_stage9c"): self.assertIn(t, run)
    def test_the_reading_commands_exist(self):
        for mod in ("parse_mh", "parse_ai", "master", "reports", "archive"): self.assertIn("ingestion.%s" % mod, self.text); self.assertTrue(os.path.exists(os.path.join(ROOT, "ingestion", mod + ".py")))
if __name__ == "__main__": unittest.main()
