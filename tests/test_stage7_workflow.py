"""Stage 7: checks the GitHub Actions workflow file is valid and safe (needs PyYAML; skipped if missing)."""
import os, unittest
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
try: import yaml
except ImportError: yaml = None

@unittest.skipIf(yaml is None, "PyYAML not installed")
class T(unittest.TestCase):
    def setUp(self):
        with open(os.path.join(ROOT, ".github", "workflows", "discover-sources.yml"), encoding="utf-8") as f: self.text = f.read()
        self.w = yaml.safe_load(self.text); self.on = self.w.get("on", self.w.get(True))
    def test_runs_by_hand_and_on_a_schedule(self): self.assertIn("workflow_dispatch", self.on); self.assertTrue(self.on["schedule"][0]["cron"])
    def test_only_needed_permission_and_no_secrets(self):
        import re; self.assertEqual(self.w["permissions"], {"contents": "write"}); self.assertTrue(set(re.findall(r"secrets\.([A-Za-z_]+)", self.text)) <= {"GITHUB_TOKEN"}); self.assertNotIn("pull_request_target", self.text)      # only GitHub's own built-in token, nothing else
    def test_runs_offline_tests_before_touching_the_website(self):
        names = [s.get("name", s.get("uses", "")) for s in self.w["jobs"]["discover"]["steps"]]
        self.assertLess([i for i, n in enumerate(names) if "Self-tests" in n][0], [i for i, n in enumerate(names) if n.startswith("Discover sources")][0])
    def test_report_is_saved_even_if_discovery_fails(self):
        save = [s for s in self.w["jobs"]["discover"]["steps"] if "Save the report" in s.get("name", "")][0]; self.assertEqual(save.get("if"), "always()")
    def test_only_the_real_run_writes_the_run_page_summary(self):
        steps = {s.get("name", ""): s for s in self.w["jobs"]["discover"]["steps"]}
        real = [s for n, s in steps.items() if n.startswith("Discover sources")][0]; tests = [s for n, s in steps.items() if n.startswith("Self-tests")][0]
        self.assertIn("--github-summary", real["run"]); self.assertNotIn("--github-summary", tests["run"])
    def test_pinned_runner_and_current_action_versions(self):
        self.assertNotIn("latest", self.w["jobs"]["discover"]["runs-on"])
        uses = [s["uses"] for s in self.w["jobs"]["discover"]["steps"] if "uses" in s]
        for u in uses: self.assertNotRegex(u, r"@v[1-4]$", u)       # v1-v4 of these actions run on the retired Node 20
    def test_has_a_timeout_and_no_overlapping_runs(self): self.assertLessEqual(self.w["jobs"]["discover"]["timeout-minutes"], 60); self.assertIn("concurrency", self.w)
if __name__ == "__main__": unittest.main()
