"""Stage 14c: daily schedule and the publish guard (no commit on a quiet day)."""
import contextlib, io, json, os, shutil, sys, tempfile, unittest
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
try:
    import yaml
except ImportError:
    yaml = None
from ingestion import publish_guard as G
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
WFD = os.path.join(ROOT, ".github", "workflows")


def make(folder, stamp="2026-11-23T12:39:55Z", fees=617, cutoff=b"abc"):
    os.makedirs(os.path.join(folder, "cutoffs"))
    base = {"data_version": {"columns": ["data_version", "created_at", "admission_year"], "rows": [["V1", stamp, "2026-27"]]},
            "refresh_status": {"columns": ["run_id", "started_at", "finished_at", "status"], "rows": [["R1", stamp, stamp, "success"]]},
            "fees": {"columns": ["fee_id", "annual_fee_inr"], "rows": [["F1", fees]]}}
    json.dump(base, open(os.path.join(folder, "base.abc.json"), "w"))
    open(os.path.join(folder, "cutoffs", "c1.json"), "wb").write(cutoff)
    json.dump({"current_admission_year": "2026-27", "last_successful_update": stamp, "base": {"file": "base.abc.json", "sha256": stamp}, "cutoffs": {"c1.json": {"sha256": stamp}}, "format": 1}, open(os.path.join(folder, "manifest.json"), "w"))


class Guard(unittest.TestCase):
    def pair(self, **kw):
        t = tempfile.mkdtemp(); self.addCleanup(shutil.rmtree, t); a, b = os.path.join(t, "old"), os.path.join(t, "new"); make(a); make(b, **kw); return a, b

    def test_only_time_stamps_differ_means_unchanged(self):
        a, b = self.pair(stamp="2026-11-24T03:20:00Z"); self.assertFalse(G.changed(a, b))

    def test_a_table_value_changes(self):
        a, b = self.pair(fees=700); self.assertTrue(G.changed(a, b))

    def test_a_cutoff_file_changes(self):
        a, b = self.pair(cutoff=b"abd"); self.assertTrue(G.changed(a, b))

    def test_a_cutoff_file_is_added_or_removed(self):
        a, b = self.pair(); open(os.path.join(b, "cutoffs", "c2.json"), "wb").write(b"x"); self.assertTrue(G.changed(a, b))

    def test_the_admission_year_changes(self):
        a, b = self.pair(); m = json.load(open(os.path.join(b, "manifest.json"))); m["current_admission_year"] = "2027-28"; json.dump(m, open(os.path.join(b, "manifest.json"), "w")); self.assertTrue(G.changed(a, b))

    def test_nothing_published_yet_or_unreadable_means_changed(self):
        a, b = self.pair(); self.assertTrue(G.changed(os.path.join(a, "missing"), b))
        open(os.path.join(a, "base.abc.json"), "w").write("{not json"); self.assertTrue(G.changed(a, b))

    def test_the_new_folder_is_not_modified_and_main_writes_the_output(self):
        a, b = self.pair(stamp="2026-11-24T03:20:00Z"); out = os.path.join(os.path.dirname(a), "gh_out"); env = os.environ.get("GITHUB_OUTPUT"); os.environ["GITHUB_OUTPUT"] = out
        try:
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf): self.assertEqual(G.main([a, b]), 0)
        finally:
            if env is None: del os.environ["GITHUB_OUTPUT"]
            else: os.environ["GITHUB_OUTPUT"] = env
        self.assertEqual(buf.getvalue().strip(), "unchanged"); self.assertEqual(open(out).read().strip(), "changed=false")
        self.assertIn("2026-11-24T03:20:00Z", open(os.path.join(b, "base.abc.json")).read())     # the stamps are only ignored in the comparison

    def test_the_real_published_folder_is_unchanged_against_itself(self):
        d = os.path.join(ROOT, "frontend", "data-real")
        if os.path.isdir(d): self.assertFalse(G.changed(d, d))


@unittest.skipIf(yaml is None, "PyYAML not installed")
class Schedules(unittest.TestCase):
    def load(self, n):
        y = yaml.safe_load(open(os.path.join(WFD, n), encoding="utf-8")); return y, (y[True] if True in y else y["on"])

    def test_daily_workflows(self):
        for n, cron in (("discover-sources.yml", "17 3 * * *"), ("parse-documents.yml", "47 4 * * *"), ("read-vacancy.yml", "7 5 * * *"), ("publish-website-data.yml", "30 6 * * *")):
            y, on = self.load(n); self.assertEqual([c["cron"] for c in on["schedule"]], [cron], n); self.assertIn("workflow_dispatch", on)

    def test_slow_changing_readers_stay_weekly_on_mondays(self):
        for n in ("read-institutes.yml", "read-fees.yml"):
            y, on = self.load(n); crons = [c["cron"] for c in on["schedule"]]; self.assertEqual(len(crons), 1); self.assertTrue(crons[0].endswith("* * 1"), (n, crons))

    def test_publish_runs_after_every_reader_of_the_same_day(self):
        times = {}
        for n in ("discover-sources.yml", "read-institutes.yml", "parse-documents.yml", "read-vacancy.yml", "read-fees.yml", "publish-website-data.yml"):
            y, on = self.load(n); m, h = on["schedule"][0]["cron"].split()[:2]; times[n] = int(h) * 60 + int(m)
        self.assertEqual(max(times, key=times.get), "publish-website-data.yml"); self.assertGreaterEqual(times["publish-website-data.yml"] - max(v for k, v in times.items() if k != "publish-website-data.yml"), 45)

    def test_publish_guard_step_controls_the_replacement(self):
        y, on = self.load("publish-website-data.yml"); steps = y["jobs"]["publish"]["steps"]
        g = [s for s in steps if "publish_guard" in s.get("run", "")]; self.assertEqual(len(g), 1); self.assertEqual(g[0]["id"], "guard"); self.assertIn("frontend/data-real build/data-real", g[0]["run"])
        r = [s for s in steps if "rm -rf frontend/data-real" in s.get("run", "")]; self.assertEqual(len(r), 1); self.assertEqual(r[0]["if"], "steps.guard.outputs.changed == 'true'")
        names = [s.get("name", "") for s in steps]; self.assertLess(next(i for i, s in enumerate(steps) if "ingestion.package_real" in s.get("run", "")), steps.index(g[0])); self.assertLess(steps.index(g[0]), steps.index(r[0]))


if __name__ == "__main__":
    unittest.main()
