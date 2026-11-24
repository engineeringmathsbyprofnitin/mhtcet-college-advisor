"""Stage 12c-6: the workflow "Read the NAAC list". Run: python -m unittest tests/test_stage12c6.py -v"""
import os, unittest
try:
    import yaml                      # not installed on a bare machine; the publish workflow installs it
except ImportError:
    yaml = None
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WF = os.path.join(ROOT, ".github", "workflows", "read-naac.yml")


@unittest.skipIf(yaml is None, "PyYAML not installed")
class ReadNaacWorkflow(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.y = yaml.safe_load(open(WF, encoding="utf-8")); cls.steps = cls.y["jobs"]["read"]["steps"]; cls.runs = "\n".join(s.get("run", "") for s in cls.steps)

    def test_triggers(self):
        on = self.y[True] if True in self.y else self.y["on"]
        self.assertIn("workflow_dispatch", on)
        self.assertEqual(sorted(on["push"]["paths"]), sorted(["data/manual/naac/**", "data/manual/naac_confirmations.csv", "data/manual/naac_transition_confirmations.csv"]))
        self.assertEqual(self.y["permissions"], {"contents": "write"})

    def test_does_not_start_publish_and_is_not_started_by_others(self):
        self.assertEqual(self.y["name"], "Read the NAAC list")
        pub = yaml.safe_load(open(os.path.join(ROOT, ".github", "workflows", "publish-website-data.yml"), encoding="utf-8"))
        on = pub[True] if True in pub else pub["on"]
        self.assertNotIn("workflow_run", on)          # Stage 14c: the publish workflow is no longer started by any other workflow (daily schedule + by hand)

    def test_steps_in_order(self):
        r = self.runs
        order = [r.index(x) for x in ("unittest", "ingestion.naac_import", "ingestion.naac_match", "ingestion.build_accreditation", "git commit")]
        self.assertEqual(order, sorted(order))
        for s in self.steps[2:]:
            if "naac_import" not in s.get("run", "") and "unittest" not in s.get("run", ""): self.assertEqual(s.get("if"), "success()")

    def test_saves_only_naac_and_accreditation_files(self):
        add = [l for l in self.runs.splitlines() if l.strip().startswith("git add")][0]
        for p in ("data/normalized/naac ", "data/normalized/naac_link ", "tables/accreditation.csv", "tables/accreditation_sources.csv", "tables/accreditation_build_report.json"): self.assertIn(p, add)
        self.assertNotIn("data/normalized/nba ", add)

    def test_self_test_files_exist(self):
        for n in ("test_stage12c2.py", "test_stage12c3.py", "test_stage12c4.py"): self.assertTrue(os.path.exists(os.path.join(ROOT, "tests", n)))


if __name__ == "__main__":
    unittest.main()
