"""Stage 14d-2: rehearsal of the admission-year rollover on PRETEND data in temporary folders (never touches the real data)."""
import csv, gzip, json, os, shutil, subprocess, sys, tempfile, unittest
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import realpkg
from test_stage14b import dec, ALL
from ingestion import plan as P, build_fees as BF, build_vacancy as BV, package_real as PR
import export_static as X
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
N = os.path.join(ROOT, "data", "normalized"); NODE = shutil.which("node")


def read_gz(path):
    with gzip.open(path, "rt", encoding="utf-8", newline="") as f: r = csv.DictReader(f); return r.fieldnames, list(r)


def write_gz(path, fields, rows):
    with gzip.open(path, "wt", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator="\n"); w.writeheader(); w.writerows(rows)


def package(plan, tables):
    folder = tempfile.mkdtemp(); out = tempfile.mkdtemp()
    try:
        PR.assemble(folder, plan=plan, tables=tables); X.publish(folder, out, now="1970-01-01T00:00:00Z")
    finally: shutil.rmtree(folder, ignore_errors=True)
    return out


def january():
    """15 January 2027: new admission year 2027-28, no 2027-28 cutoff list yet (cutoffs 2026-27, all four rounds)."""
    plan = P.make_plan(dec("2027-01-15", status="previous_cycle_latest")); T = realpkg.fresh_tables()
    BF.build(base=N, plan=plan, outdir=T); BV.build(base=N, plan=plan, outdir=T); return plan, T


def july():
    """20 July 2027: Round I of 2027-28 published. PRETEND rows: the 2026-27 Round I rows relabelled 2027-28 become the current year; the 2026-27 Round IV rows join the history."""
    d = dec("2027-07-20", cur="2027-28", rounds=["I"])
    d["previous"] = [{"label": "2026-27", "cutoff_rounds": ALL}, {"label": "2025-26", "cutoff_rounds": ALL}, {"label": "2024-25", "cutoff_rounds": ["I", "II", "III"]}]
    plan = P.make_plan(d); T = realpkg.fresh_tables()
    fc, cur = read_gz(os.path.join(T, "current_cutoffs.csv.gz")); fh, hist = read_gz(os.path.join(T, "historical_cutoffs.csv.gz"))
    new_cur = [dict(r, admission_year="2027-28", cutoff_id="X" + r["cutoff_id"]) for r in cur if r["cap_round"] == "I"]
    new_hist = [r for r in hist if r["admission_year"] != "2023-24"] + [r for r in cur if r["cap_round"] == "IV"]
    write_gz(os.path.join(T, "current_cutoffs.csv.gz"), fc, new_cur); write_gz(os.path.join(T, "historical_cutoffs.csv.gz"), fh, new_hist)
    BF.build(base=N, plan=plan, outdir=T); BV.build(base=N, plan=plan, outdir=T); return plan, T


class Rehearsal(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dirs = {}; cls.tmp = []
        for k, f in (("jan", january), ("jul", july)):
            plan, T = f(); cls.tmp.append(T); cls.dirs[k] = package(plan, T); cls.tmp.append(cls.dirs[k])
            if k == "jan": cls.jan_tables = T; cls.jan_plan = plan
            else: cls.jul_tables = T; cls.jul_plan = plan

    @classmethod
    def tearDownClass(cls):
        for d in cls.tmp: shutil.rmtree(d, ignore_errors=True)

    def test_plans(self):
        self.assertEqual((self.jan_plan["admission_year"], self.jan_plan["cutoff_year"], self.jan_plan["admission_year_has_cutoffs"]), ("2027-28", "2026-27", False))
        self.assertEqual((self.jul_plan["admission_year"], self.jul_plan["cutoff_year"], self.jul_plan["latest_round"], self.jul_plan["next_round_expected"]), ("2027-28", "2027-28", "I", "II"))
        self.assertEqual([h["label"] for h in self.jul_plan["history"]], ["2026-27", "2025-26", "2024-25"])

    def test_builders_do_not_carry_last_years_vacancy_or_fees_over_as_new(self):
        for T in (self.jan_tables, self.jul_tables):
            self.assertFalse(os.path.exists(os.path.join(T, "vacancy.csv")))                       # no 2027-28 vacancy list: removed, never reused
            rows = list(csv.DictReader(open(os.path.join(T, "fees.csv"), encoding="utf-8"))); self.assertTrue(rows)
            self.assertEqual({r["academic_year"] for r in rows}, {"2026-27"})

    def test_the_real_data_was_not_touched(self):
        plan = json.load(open(os.path.join(N, "data_plan.json"), encoding="utf-8")); self.assertEqual(plan["current_year"], "2026-27")

    @unittest.skipUnless(NODE, "node not installed")
    def test_engine_and_page_text_on_the_pretend_data(self):
        r = subprocess.run([NODE, "--test", os.path.join(ROOT, "tests", "rollover_rehearsal.test.js")], env=dict(os.environ, REHEARSAL_DIRS=json.dumps(self.dirs)), capture_output=True, text=True, cwd=ROOT)
        self.assertEqual(r.returncode, 0, r.stdout[-2500:] + r.stderr[-800:]); self.assertIn("# fail 0", r.stdout); self.assertIn("# skipped 0", r.stdout); self.assertIn("# pass 3", r.stdout)


if __name__ == "__main__":
    unittest.main()
